"""
基于 LangGraph 的工作流图构建和执行

使用 LangGraph StateGraph 实现工作流的节点执行、条件路由和状态管理
"""
from typing import Dict, Any, List, Optional, TypedDict
import time
import logging

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from .state import WorkflowState, Message
from .nodes import InputNode, DataSourceNode, RetrievalNode, LLMNode, ToolNode, OutputNode

logger = logging.getLogger(__name__)


class WorkflowGraphState(TypedDict):
    """LangGraph 状态定义（兼容 LangGraph 的 TypedDict 格式）"""
    messages: Dict[str, Dict[str, Any]]
    execution_path: List[str]
    question: str
    start_time: Optional[float]
    timings: Dict[str, float]
    retrieved_context: Optional[str]
    llm_output: Optional[str]
    total: int
    documents: List[Dict[str, Any]]
    scores: List[float]


def _convert_to_langgraph_state(state: WorkflowState) -> WorkflowGraphState:
    """将 WorkflowState 转换为 LangGraph 状态格式"""
    return {
        "messages": {
            node_id: {
                port: {
                    "type": msg.type,
                    "payload": msg.payload
                } for port, msg in ports.items()
            } for node_id, ports in state.messages.items()
        },
        "execution_path": state.execution_path,
        "question": state.question,
        "start_time": state.start_time,
        "timings": state.timings,
        "retrieved_context": state.retrieved_context,
        "llm_output": state.llm_output,
        "total": state.total,
        "documents": state.documents,
        "scores": state.scores,
    }


def _convert_from_langgraph_state(graph_state: WorkflowGraphState) -> WorkflowState:
    """从 LangGraph 状态格式转换回 WorkflowState"""
    state = WorkflowState(
        messages={
            node_id: {
                port: Message(type=msg["type"], payload=msg["payload"])
                for port, msg in ports.items()
            } for node_id, ports in graph_state["messages"].items()
        },
        execution_path=graph_state["execution_path"],
        question=graph_state["question"],
        start_time=graph_state.get("start_time"),
        timings=graph_state.get("timings", {}),
        retrieved_context=graph_state.get("retrieved_context"),
        llm_output=graph_state.get("llm_output"),
        total=graph_state.get("total", 0),
        documents=graph_state.get("documents", []),
        scores=graph_state.get("scores", []),
    )
    return state


def create_node_function(node_instance: Any, node_id: str, request: Optional[Any] = None, user: Optional[Any] = None, event_emitter: Optional[Any] = None) -> callable:
    """创建 LangGraph 节点函数"""
    async def node_func(state: WorkflowGraphState) -> WorkflowGraphState:
        """节点执行函数"""
        t0 = time.time()
        
        # 转换为 WorkflowState
        workflow_state = _convert_from_langgraph_state(state)
        
        # 传递 request 和 user（用于工具节点）
        workflow_state._request = request
        workflow_state._user = user

        # 计算节点类型与可读标签
        try:
            node_type = None
            node_label = None
            cfg = getattr(node_instance, "config", {}) or {}
            cls_name = getattr(getattr(node_instance, "__class__", None), "__name__", "")
            # 映射类名到类型
            cls_map = {
                "InputNode": "input",
                "DataSourceNode": "dataSource",
                "RetrievalNode": "retrieval",
                "LLMNode": "llm",
                "ToolNode": "tool",
                "OutputNode": "output",
            }
            node_type = cls_map.get(cls_name, cls_name or "node")
            if node_type == "tool":
                node_label = cfg.get("tool_name") or cfg.get("tool_id") or "Tool"
            elif node_type == "llm":
                node_label = "LLM"
            elif node_type == "retrieval":
                node_label = "Retrieval"
            elif node_type == "dataSource":
                node_label = "DataSource"
            elif node_type == "input":
                node_label = "Input"
            elif node_type == "output":
                node_label = "Output"
            else:
                node_label = node_type
        except Exception:
            node_type = "node"
            node_label = node_id
        
        # 发送开始事件
        try:
            if event_emitter:
                await event_emitter({
                    "type": "status",
                    "data": {
                        "action": "agent_node_start",
                        "node_id": node_id,
                        "node_type": node_type,
                        "node_label": node_label,
                        "done": False,
                    },
                })
        except Exception:
            pass

        # 执行节点
        workflow_state = await node_instance.execute(workflow_state)
        
        # 记录执行时间
        workflow_state.timings[f"node_{node_id}"] = (time.time() - t0) * 1000  # 毫秒
        
        # 发送结束事件
        try:
            if event_emitter:
                await event_emitter({
                    "type": "status",
                    "data": {
                        "action": "agent_node_end",
                        "node_id": node_id,
                        "node_type": node_type,
                        "node_label": node_label,
                        "elapsed_ms": workflow_state.timings.get(f"node_{node_id}"),
                        "done": False,
                    },
                })
        except Exception:
            pass

        # 转换回 LangGraph 状态
        return _convert_to_langgraph_state(workflow_state)
    
    return node_func


def create_workflow_graph(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    request: Optional[Any] = None,
    user: Optional[Any] = None,
    event_emitter: Optional[Any] = None
) -> StateGraph:
    """
    创建工作流图
    
    Args:
        nodes: 节点列表，每个节点包含 id, type, config
        connections: 连接列表，每个连接包含 from, to, type
    
    Returns:
        LangGraph StateGraph 实例
    """
    # 创建图
    workflow = StateGraph(WorkflowGraphState)
    
    # 节点类型映射
    node_classes = {
        "input": InputNode,
        "dataSource": DataSourceNode,
        "retrieval": RetrievalNode,
        "llm": LLMNode,
        "tool": ToolNode,
        "output": OutputNode,
    }
    
    # 创建节点实例并添加到图
    node_instances = {}
    for node_data in nodes:
        node_id = node_data["id"]
        node_type = node_data["type"]
        node_config = node_data.get("config", {})
        
        if node_type not in node_classes:
            logger.warning(f"未知节点类型: {node_type}, 跳过节点 {node_id}")
            continue
        
        # 创建节点实例
        node_class = node_classes[node_type]
        node_instance = node_class(node_id, node_config)
        node_instances[node_id] = node_instance
        
        # 创建节点函数并添加到图
        node_func = create_node_function(node_instance, node_id, request, user, event_emitter)
        workflow.add_node(node_id, node_func)
    
    # 构建连接关系（拓扑排序）
    graph_edges = {}
    in_degree = {node["id"]: 0 for node in nodes}
    
    for conn in connections:
        if conn.get("type") == "unidirectional" and conn.get("from") and conn.get("to"):
            from_id = conn["from"]
            to_id = conn["to"]
            if from_id not in graph_edges:
                graph_edges[from_id] = []
            graph_edges[from_id].append(to_id)
            if to_id in in_degree:
                in_degree[to_id] += 1
    
    # 找到起始节点（入度为 0 的节点）
    start_nodes = [node_id for node_id, degree in in_degree.items() if degree == 0]
    
    # 如果没有起始节点，选择 input 和 dataSource 节点
    if not start_nodes:
        start_nodes = [
            node["id"] for node in nodes
            if node.get("type") in ["input", "dataSource"]
        ]
    
    # 设置入口点
    if start_nodes:
        # 从 START 连接到所有起始节点
        for start_node in start_nodes:
            if start_node in node_instances:
                workflow.add_edge(START, start_node)
    else:
        # 如果没有起始节点，直接设置第一个节点为入口
        if nodes and nodes[0]["id"] in node_instances:
            first_node_id = nodes[0]["id"]
            workflow.add_edge(START, first_node_id)
    
    # 添加连接边
    for from_id, to_ids in graph_edges.items():
        for to_id in to_ids:
            if from_id in node_instances and to_id in node_instances:
                workflow.add_edge(from_id, to_id)
    
    # 设置结束节点
    output_nodes = [node["id"] for node in nodes if node.get("type") == "output"]
    if output_nodes:
        # 从输出节点连接到 END
        for output_node in output_nodes:
            if output_node in node_instances:
                workflow.add_edge(output_node, END)
    else:
        # 如果没有输出节点，所有叶子节点都连接到 END
        leaf_nodes = [
            node_id for node_id in node_instances.keys()
            if node_id not in graph_edges or not graph_edges.get(node_id)
        ]
        for leaf_node in leaf_nodes:
            if leaf_node in node_instances:
                workflow.add_edge(leaf_node, END)
    
    return workflow


async def execute_workflow(
    question: str,
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    checkpoint: Optional[Any] = None,
    request: Optional[Any] = None,
    user: Optional[Any] = None,
    event_emitter: Optional[Any] = None
) -> WorkflowState:
    """
    执行工作流
    
    Args:
        question: 用户问题
        nodes: 节点列表
        connections: 连接列表
        checkpoint: 可选检查点（用于恢复执行）
        request: FastAPI Request 对象（用于工具调用）
        user: 用户对象（用于工具调用）
    
    Returns:
        执行完成后的 WorkflowState
    """
    # 创建图
    workflow = create_workflow_graph(nodes, connections, request, user, event_emitter)
    
    # 创建检查点存储（如果提供）
    if checkpoint is None:
        checkpoint = MemorySaver()
    
    # 编译图
    app = workflow.compile(checkpointer=checkpoint)
    
    # 初始化状态
    initial_state = WorkflowGraphState(
        messages={},
        execution_path=[],
        question=question,
        start_time=time.time(),
        timings={},
        retrieved_context=None,
        llm_output=None,
        total=0,
        documents=[],
        scores=[],
    )
    
    # request 和 user 已通过 create_node_function 传递到节点
    
    # 执行图
    config = {"configurable": {"thread_id": "1"}}
    final_state = None
    
    # 流式执行，收集最后一个状态
    async for state in app.astream(initial_state, config):
        # LangGraph 返回的是 {node_id: state} 格式
        if isinstance(state, dict) and state:
            final_state = list(state.values())[-1]
        else:
            final_state = state
    
    # 转换为 WorkflowState
    if final_state:
        workflow_state = _convert_from_langgraph_state(final_state)
        # 计算总时间
        if workflow_state.start_time:
            workflow_state.timings["total"] = (time.time() - workflow_state.start_time) * 1000
        return workflow_state
    
    # 如果执行失败，返回初始状态
    return _convert_from_langgraph_state(initial_state)

