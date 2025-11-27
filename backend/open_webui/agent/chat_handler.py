"""
Agent 模式聊天处理器

当 agentMode 开启时，使用 LangGraph Agent 框架调用工具
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import Request

from .graph import execute_workflow
from .state import WorkflowState

logger = logging.getLogger(__name__)


async def process_agent_chat(
    question: str,
    selected_tool_ids: List[str],
    request: Request,
    user: Any,
    model_id: str = None,
    temperature: float = 0.7,
    max_tokens: int = 20000,
    event_emitter: Any = None
) -> Dict[str, Any]:
    """
    使用 Agent 框架处理聊天请求并调用工具
    
    Args:
        question: 用户问题
        selected_tool_ids: 选中的工具ID列表
        request: FastAPI Request 对象
        user: 用户对象
        model_id: 模型ID（用于LLM节点）
        temperature: 温度参数
        max_tokens: 最大token数
    
    Returns:
        包含结果和工具调用信息的字典
    """
    logger.info(f"process_agent_chat 调用: question={question[:50] if question else None}, selected_tool_ids={selected_tool_ids}, model_id={model_id}")
    
    if not selected_tool_ids:
        logger.warning("Agent模式开启但没有选择工具")
        return {
            "answer": "请至少选择一个工具",
            "tool_calls": [],
            "sources": []
        }
    
    try:
        # 构建工作流节点
        nodes = []
        connections = []
        
        # 1. 输入节点
        input_node_id = "input_1"
        nodes.append({
            "id": input_node_id,
            "type": "input",
            "config": {
                "user_input": question
            }
        })
        
        # 2. 为每个工具创建工具节点（串行执行，避免并发写入 state）
        tool_nodes = []
        last_node_id = input_node_id
        
        for idx, tool_id in enumerate(selected_tool_ids):
            tool_node_id = f"tool_{idx + 1}"
            tool_nodes.append(tool_node_id)
            
            # 创建工具节点
            nodes.append({
                "id": tool_node_id,
                "type": "tool",
                "config": {
                    "tool_id": tool_id,
                    # 提前设置可读名称，至少用 tool_id 兜底，避免前端显示 undefined
                    "tool_name": tool_id,
                    "tool_params": {
                        # 将问题作为参数传递给工具
                        "question": question
                    },
                    "input_bindings": {
                        # 从输入节点获取问题作为参数（如果需要）
                        "params": f"{input_node_id}.user"
                    }
                }
            })
            
            # 串行连接：上一节点 -> 当前工具
            connections.append({
                "from": last_node_id,
                "to": tool_node_id,
                "type": "unidirectional"
            })
            last_node_id = tool_node_id
        
        # 3. LLM节点：基于工具结果生成回答（仅依赖最后一个工具节点）
        llm_node_id = "llm_1"
        nodes.append({
            "id": llm_node_id,
            "type": "llm",
            "config": {
                "model": model_id or "gpt-4",
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt_template": """你是Agent的审核和执行官，负责将工具执行的结果进行审核，审核通过可以直接推送消息。

用户问题: {question}

工具执行结果:
{tool_results}

确保内容有效

"""
            }
        })
        
        # 工具结果将通过 LLMNode 自动收集
        
        # 仅连接最后一个节点到 LLM（避免并发更新 state）
        connections.append({
            "from": last_node_id,
            "to": llm_node_id,
            "type": "unidirectional"
        })
        
        # 4. 输出节点
        output_node_id = "output_1"
        nodes.append({
            "id": output_node_id,
            "type": "output",
            "config": {
                "input_bindings": {
                    "answer": f"{llm_node_id}.answer"
                }
            }
        })
        
        # 连接LLM节点到输出节点
        connections.append({
            "from": llm_node_id,
            "to": output_node_id,
            "type": "unidirectional"
        })
        
        logger.info(f"开始执行工作流: 节点数={len(nodes)}, 连接数={len(connections)}")
        
        # 执行工作流
        workflow_state = await execute_workflow(
            question=question,
            nodes=nodes,
            connections=connections,
            request=request,
            user=user,  # 传递用户对象，便于下游按属性访问（user.id 等）
            event_emitter=event_emitter
        )
        
        logger.info(f"工作流执行完成: execution_path={workflow_state.execution_path}")
        
        # 提取结果
        answer = workflow_state.llm_output or ""
        
        logger.info(f"Agent回答: {answer[:100] if answer else 'None'}...")
        
        # 收集工具调用结果
        tool_calls = []
        sources = []
        
        for idx, tool_id in enumerate(selected_tool_ids):
            tool_node_id = f"tool_{idx + 1}"
            tool_messages = workflow_state.messages.get(tool_node_id, {})
            
            # 获取工具结果
            tool_result_msg = tool_messages.get("result")
            tool_error_msg = tool_messages.get("error")
            
            if tool_result_msg:
                tool_result = tool_result_msg.payload
                tool_calls.append({
                    "tool_id": tool_id,
                    "result": tool_result,
                    "success": True
                })
                sources.append({
                    "tool_result": True,
                    "content": tool_result,
                    "source": {
                        "id": tool_id,
                        "name": f"Tool {tool_id}"
                    }
                })
            elif tool_error_msg:
                tool_error = tool_error_msg.payload
                tool_calls.append({
                    "tool_id": tool_id,
                    "result": tool_error,
                    "success": False
                })
        
        # 生成可读的步骤标签
        try:
            node_meta = { n["id"]: n for n in nodes }
            readable_steps = []
            for nid in (workflow_state.execution_path or []):
                meta = node_meta.get(nid, {})
                ntype = meta.get("type")
                label = None
                if ntype == "tool":
                    cfg = meta.get("config", {})
                    label = cfg.get("tool_name") or cfg.get("tool_id") or "Tool"
                elif ntype == "llm":
                    label = "LLM"
                elif ntype == "retrieval":
                    label = "Retrieval"
                elif ntype == "dataSource":
                    label = "DataSource"
                elif ntype == "input":
                    label = "Input"
                elif ntype == "output":
                    label = "Output"
                else:
                    label = ntype or nid
                readable_steps.append({"id": nid, "label": label})
        except Exception:
            readable_steps = [{"id": nid, "label": nid} for nid in (workflow_state.execution_path or [])]

        return {
            "answer": answer,
            "tool_calls": tool_calls,
            "sources": sources,
            "workflow_state": {
                "execution_path": workflow_state.execution_path,
                "timings": workflow_state.timings,
                "total": workflow_state.total,
            },
            "agent_meta": {
                "execution_path": workflow_state.execution_path,
                "timings": workflow_state.timings,
                "steps": readable_steps,
            }
        }
        
    except Exception as e:
        logger.error(f"Agent模式处理失败: {e}", exc_info=True)
        return {
            "answer": f"Agent模式处理失败: {str(e)}",
            "tool_calls": [],
            "sources": []
        }

