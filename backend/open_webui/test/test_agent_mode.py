"""
测试 Agent 模式使用 LangGraph 直接调用工具函数

固定问题：查询零差云控关节重复定位精度，并预测产品交付时间

使用方法:
    cd backend && python -m open_webui.test.test_agent_mode
"""
import asyncio
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

# 添加项目根目录到路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import Request
from open_webui.agent.graph import execute_workflow
from open_webui.agent.nodes import ToolNode
from open_webui.models.users import UserModel, UserSettings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 固定测试问题
FIXED_QUESTION = "我想知道零差云控关节重复定位精度是多少？请调用相关工具查询并给出详细答案。同时预测产品ID为 '02.88.000.00488'，数量为 100 的交付时间。"

# ==================== 工具函数定义 ====================

def delivery_prediction_get(
    product_id: str = "02.88.000.00488",
    quantity: int = 100,
) -> str:
    """
    使用 GET 方法查询产品交付预测信息
    """
    API_BASE_URL = "http://192.168.2.168:8000/api/SaleAgent/DeliveryPrediction"
    
    try:
        params = {"product_id": product_id, "quantity": quantity}
        response = requests.get(API_BASE_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return f"✅ 交付预测查询成功（GET方法）:\n产品ID: {product_id}\n数量: {quantity}\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}"
        else:
            return f"❌ GET 请求失败，状态码: {response.status_code}\n错误信息: {response.text}"
    except requests.exceptions.Timeout:
        return f"❌ 请求超时：无法连接到交付预测服务"
    except requests.exceptions.ConnectionError:
        return f"❌ 连接错误：无法连接到服务器 {API_BASE_URL}"
    except Exception as e:
        return f"❌ 发生错误：{str(e)}"


def ragflow_retrieval(
    question: str,
) -> str:
    """
    直接调用 RAGFlow API 检索相关文档片段
    """
    # RAGFlow API 配置（根据实际情况修改）
    RAGFLOW_API_BASE = "http://192.168.2.168:9222"
    RAGFLOW_API_KEY = ""  # 如果需要认证，在这里设置
    
    try:
        # 1. 获取数据集列表
        datasets_url = f"{RAGFLOW_API_BASE}/api/datasets"
        headers = {"Content-Type": "application/json"}
        if RAGFLOW_API_KEY:
            headers["Authorization"] = f"Bearer {RAGFLOW_API_KEY}"
        
        response = requests.get(datasets_url, headers=headers, params={"page": 1, "page_size": 1000}, timeout=10)
        
        if response.status_code != 200:
            return json.dumps(
                {"error": f"获取数据集失败: {response.status_code} - {response.text}", "question": question},
                ensure_ascii=False,
            )
        
        datasets = response.json().get("data", [])
        dataset_ids = []
        for ds in datasets:
            dataset_id = ds.get("id") or ds.get("dataset_id") or ds.get("_id")
            if dataset_id:
                dataset_ids.append(str(dataset_id))
        
        if not dataset_ids:
            return json.dumps(
                {"error": "没有可用的数据集", "question": question},
                ensure_ascii=False,
            )
        
        # 2. 执行检索
        retrieve_url = f"{RAGFLOW_API_BASE}/api/chunks/retrieve"
        retrieve_data = {
            "question": question,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": 10,
            "similarity_threshold": 0.2,
            "vector_similarity_weight": 0.3,
            "top_k": 1024,
            "keyword": False,
            "highlight": False,
        }
        
        response = requests.post(retrieve_url, json=retrieve_data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return json.dumps(
                {"error": f"检索失败: {response.status_code} - {response.text}", "question": question},
                ensure_ascii=False,
            )
        
        result = response.json()
        documents = result.get("data", {}).get("documents", [])
        scores = result.get("data", {}).get("scores", [])
        
        return json.dumps(
            {
                "question": question,
                "total": len(documents),
                "documents": documents[:3],  # 只返回前3个结果
                "scores": scores[:3] if scores else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    except requests.exceptions.Timeout:
        return json.dumps(
            {"error": "请求超时：无法连接到RAGFlow服务", "question": question},
            ensure_ascii=False,
        )
    except requests.exceptions.ConnectionError:
        return json.dumps(
            {"error": f"连接错误：无法连接到RAGFlow服务器 {RAGFLOW_API_BASE}", "question": question},
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error(f"RAGFlow检索失败: {e}", exc_info=True)
        return json.dumps(
            {"error": str(e), "question": question}, ensure_ascii=False
        )


# ==================== Mock 对象 ====================

def create_mock_request() -> Request:
    """创建模拟的 FastAPI Request 对象（简化版，不需要真实 app）"""
    mock_request = MagicMock(spec=Request)
    mock_request.app = MagicMock()
    mock_request.app.state = MagicMock()
    mock_request.app.state.config = MagicMock()
    mock_request.app.state.config.TOOL_SERVER_CONNECTIONS = []
    mock_request.app.state.MODELS = {}
    mock_request.app.state.config.OPENAI_API_BASE_URLS = []
    mock_request.app.state.config.OPENAI_API_KEYS = []
    return mock_request


def create_mock_user(user_id: str = "test_user_1", name: str = "Test User", email: str = "test@example.com") -> UserModel:
    """创建模拟的 UserModel 对象"""
    import time
    current_time = int(time.time())
    
    return UserModel(
        id=user_id,
        name=name,
        email=email,
        role="user",
        profile_image_url="/user.png",
        last_active_at=current_time,
        updated_at=current_time,
        created_at=current_time,
        settings=UserSettings()
    )


async def simple_event_emitter(event: dict):
    """简单的事件发射器，用于测试"""
    event_type = event.get("type")
    data = event.get("data", {})
    
    if event_type == "status":
        action = data.get("action")
        node_id = data.get("node_id")
        node_label = data.get("node_label", node_id)
        
        if action == "agent_node_start":
            logger.info(f"🚀 节点开始: {node_label} ({node_id})")
        elif action == "agent_node_end":
            elapsed_ms = data.get("elapsed_ms", 0)
            logger.info(f"✅ 节点完成: {node_label} ({node_id}) - 耗时: {elapsed_ms:.2f}ms")


# ==================== 自定义工具节点 ====================

class CustomToolNode:
    """自定义工具节点，直接调用工具函数"""
    
    def __init__(self, node_id: str, config: Dict[str, Any], tool_function: callable):
        self.node_id = node_id
        self.config = config
        self._tool_function = tool_function
    
    def _get_input_value(self, state, port_key: str, default: Any) -> Any:
        """获取输入值"""
        bindings = self.config.get("input_bindings", {})
        binding = bindings.get(port_key)
        
        if binding and "." in binding:
            source_node_id, source_port = binding.split(".", 1)
            source_msg = state.messages.get(source_node_id, {}).get(source_port)
            if source_msg:
                return source_msg.payload
        
        return default
    
    async def execute(self, state):
        """执行工具函数"""
        from open_webui.agent.state import Message
        
        try:
            # 获取参数
            tool_params = self.config.get("tool_params", {}).copy()
            question_input = self._get_input_value(state, "question", None)
            if question_input and isinstance(question_input, str):
                if "question" not in tool_params:
                    tool_params["question"] = question_input
            
            # 获取 request 和 user
            request = getattr(state, "_request", None)
            user = getattr(state, "_user", None)
            
            # 过滤参数，只传递函数接受的参数
            import inspect
            if self._tool_function is None:
                raise ValueError(f"工具函数未定义: {self.node_id}")
            
            sig = inspect.signature(self._tool_function)
            accepted_params = list(sig.parameters.keys())
            
            # 过滤参数，只传递函数接受的参数
            filtered_params = {}
            for param_name, param_value in tool_params.items():
                if param_name in accepted_params:
                    filtered_params[param_name] = param_value
            
            # 调用工具函数（同步函数，不需要 await）
            if asyncio.iscoroutinefunction(self._tool_function):
                result = await self._tool_function(**filtered_params)
            else:
                result = self._tool_function(**filtered_params)
            
            # 保存结果
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["result"] = Message(
                type="text",
                payload=result
            )
            
            state.execution_path.append(self.node_id)
            return state
            
        except Exception as e:
            logger.error(f"工具节点 {self.node_id} 执行失败: {e}", exc_info=True)
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["error"] = Message(
                type="error",
                payload=str(e)
            )
            state.execution_path.append(self.node_id)
            return state


# ==================== 测试主函数 ====================

async def test_agent_mode():
    """测试 Agent 模式"""
    logger.info("=" * 80)
    logger.info("开始测试 Agent 模式（直接调用工具函数）")
    logger.info("=" * 80)
    logger.info(f"固定问题: {FIXED_QUESTION}")
    logger.info("\n工具列表:")
    logger.info("  1. ragflow_retrieval - 检索知识库中的相关信息")
    logger.info("  2. delivery_prediction_get - 查询产品交付预测")
    
    # 创建 mock 对象
    user = create_mock_user()
    request = create_mock_request()
    
    logger.info(f"\n使用用户: {user.name} ({user.id})")
    logger.info("\n" + "=" * 80)
    logger.info("开始执行 Agent 工作流...")
    logger.info("=" * 80 + "\n")
    
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
                "user_input": FIXED_QUESTION
            }
        })
        
        # 2. 工具节点1: ragflow_retrieval
        tool1_node_id = "tool_1"
        nodes.append({
            "id": tool1_node_id,
            "type": "custom_tool",
            "config": {
                "tool_name": "ragflow_retrieval",
                "tool_params": {
                    "question": "零差云控关节重复定位精度"
                },
                "input_bindings": {
                    "question": f"{input_node_id}.user"
                }
            },
            "tool_function": ragflow_retrieval  # 直接传递函数
        })
        connections.append({
            "from": input_node_id,
            "to": tool1_node_id,
            "type": "unidirectional"
        })
        
        # 3. 工具节点2: delivery_prediction_get
        tool2_node_id = "tool_2"
        nodes.append({
            "id": tool2_node_id,
            "type": "custom_tool",
            "config": {
                "tool_name": "delivery_prediction_get",
                "tool_params": {
                    "product_id": "02.88.000.00488",
                    "quantity": 100
                }
            },
            "tool_function": delivery_prediction_get  # 直接传递函数
        })
        connections.append({
            "from": tool1_node_id,
            "to": tool2_node_id,
            "type": "unidirectional"
        })
        
        # 4. LLM节点
        llm_node_id = "llm_1"
        nodes.append({
            "id": llm_node_id,
            "type": "llm",
            "config": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 20000,
                "prompt_template": """你是Agent的审核和执行官，负责将工具执行的结果进行审核，审核通过可以直接推送消息。

用户问题: {question}

工具执行结果:
{tool_results}

请基于工具结果，给出完整、准确的回答。确保内容有效且易于理解。
"""
            }
        })
        connections.append({
            "from": tool2_node_id,
            "to": llm_node_id,
            "type": "unidirectional"
        })
        
        # 5. 输出节点
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
        connections.append({
            "from": llm_node_id,
            "to": output_node_id,
            "type": "unidirectional"
        })
        
        # 修改 execute_workflow 以支持自定义工具节点
        # 这里我们需要手动创建图，因为需要替换自定义工具节点
        from langgraph.graph import StateGraph, END, START
        from langgraph.checkpoint.memory import MemorySaver
        from open_webui.agent.state import WorkflowState, Message
        from open_webui.agent.nodes import InputNode, LLMNode, OutputNode
        from open_webui.agent.graph import WorkflowGraphState, _convert_to_langgraph_state, _convert_from_langgraph_state
        import time
        
        # 创建图
        workflow = StateGraph(WorkflowGraphState)
        
        # 创建节点实例
        node_instances = {}
        for node_data in nodes:
            node_id = node_data["id"]
            node_type = node_data["type"]
            node_config = node_data.get("config", {})
            
            if node_type == "input":
                node_instance = InputNode(node_id, node_config)
            elif node_type == "custom_tool":
                # 使用自定义工具节点
                tool_function = node_data.get("tool_function")
                node_instance = CustomToolNode(node_id, node_config, tool_function)
            elif node_type == "llm":
                node_instance = LLMNode(node_id, node_config)
            elif node_type == "output":
                node_instance = OutputNode(node_id, node_config)
            else:
                logger.warning(f"未知节点类型: {node_type}, 跳过节点 {node_id}")
                continue
            
            node_instances[node_id] = node_instance
            
            # 创建节点函数（使用闭包捕获变量）
            def make_node_func(nid, ntype, nconfig, ninst):
                async def node_func(state: WorkflowGraphState) -> WorkflowGraphState:
                    t0 = time.time()
                    workflow_state = _convert_from_langgraph_state(state)
                    workflow_state._request = request
                    workflow_state._user = user
                    
                    # 发送开始事件
                    try:
                        await simple_event_emitter({
                            "type": "status",
                            "data": {
                                "action": "agent_node_start",
                                "node_id": nid,
                                "node_type": ntype,
                                "node_label": nconfig.get("tool_name", nid),
                                "done": False,
                            },
                        })
                    except:
                        pass
                    
                    # 执行节点
                    workflow_state = await ninst.execute(workflow_state)
                    workflow_state.timings[f"node_{nid}"] = (time.time() - t0) * 1000
                    
                    # 发送结束事件
                    try:
                        await simple_event_emitter({
                            "type": "status",
                            "data": {
                                "action": "agent_node_end",
                                "node_id": nid,
                                "node_type": ntype,
                                "node_label": nconfig.get("tool_name", nid),
                                "elapsed_ms": workflow_state.timings.get(f"node_{nid}"),
                                "done": False,
                            },
                        })
                    except:
                        pass
                    
                    return _convert_to_langgraph_state(workflow_state)
                return node_func
            
            workflow.add_node(node_id, make_node_func(node_id, node_type, node_config, node_instance))
        
        # 添加边
        workflow.add_edge(START, input_node_id)
        for conn in connections:
            if conn.get("type") == "unidirectional":
                workflow.add_edge(conn["from"], conn["to"])
        workflow.add_edge(output_node_id, END)
        
        # 编译并执行
        checkpoint = MemorySaver()
        app = workflow.compile(checkpointer=checkpoint)
        
        initial_state = WorkflowGraphState(
            messages={},
            execution_path=[],
            question=FIXED_QUESTION,
            start_time=time.time(),
            timings={},
            retrieved_context=None,
            llm_output=None,
            total=0,
            documents=[],
            scores=[],
        )
        
        config = {"configurable": {"thread_id": "1"}}
        final_state = None
        
        async for state in app.astream(initial_state, config):
            if isinstance(state, dict) and state:
                final_state = list(state.values())[-1]
        
        # 转换为 WorkflowState
        if final_state:
            workflow_state = _convert_from_langgraph_state(final_state)
            if workflow_state.start_time:
                workflow_state.timings["total"] = (time.time() - workflow_state.start_time) * 1000
        
        logger.info("\n" + "=" * 80)
        logger.info("Agent 执行完成")
        logger.info("=" * 80)
        
        # 显示结果
        logger.info("\n📝 Agent 回答:")
        logger.info("-" * 80)
        logger.info(workflow_state.llm_output or "无回答")
        logger.info("-" * 80)
        
        # 显示工具调用结果
        tool_calls = []
        for node_id in workflow_state.execution_path:
            if node_id.startswith("tool_"):
                tool_messages = workflow_state.messages.get(node_id, {})
                tool_result_msg = tool_messages.get("result")
                tool_error_msg = tool_messages.get("error")
                if tool_result_msg:
                    tool_calls.append({
                        "tool_id": node_id,
                        "result": tool_result_msg.payload,
                        "success": True
                    })
                elif tool_error_msg:
                    tool_calls.append({
                        "tool_id": node_id,
                        "result": tool_error_msg.payload,
                        "success": False
                    })
        
        if tool_calls:
            logger.info(f"\n🔧 工具调用结果 ({len(tool_calls)} 个):")
            for idx, tool_call in enumerate(tool_calls, 1):
                tool_id = tool_call.get("tool_id", "未知")
                success = tool_call.get("success", False)
                result_data = tool_call.get("result", {})
                
                status = "✅ 成功" if success else "❌ 失败"
                logger.info(f"\n  {idx}. {tool_id} - {status}")
                logger.info(f"     结果: {str(result_data)[:500]}...")
        
        # 显示执行步骤
        steps = []
        for nid in workflow_state.execution_path:
            for node_data in nodes:
                if node_data["id"] == nid:
                    ntype = node_data.get("type")
                    label = node_data.get("config", {}).get("tool_name", nid)
                    if ntype == "input":
                        label = "Input"
                    elif ntype == "llm":
                        label = "LLM"
                    elif ntype == "output":
                        label = "Output"
                    steps.append({"id": nid, "label": label})
                    break
        
        if steps:
            logger.info(f"\n📊 执行步骤 ({len(steps)} 个):")
            for idx, step in enumerate(steps, 1):
                step_id = step.get("id", "未知")
                step_label = step.get("label", step_id)
                logger.info(f"  {idx}. {step_label} ({step_id})")
        
        # 显示执行时间
        if workflow_state.timings:
            logger.info(f"\n⏱️  执行时间:")
            for key, value in workflow_state.timings.items():
                logger.info(f"  {key}: {value:.2f}ms")
        
        logger.info("\n" + "=" * 80)
        logger.info("测试完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\n❌ Agent 执行失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    await test_agent_mode()


if __name__ == "__main__":
    asyncio.run(main())
