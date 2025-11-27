"""
LangGraph Agent 模块

用于实现基于 LangGraph 的工作流执行引擎，支持：
- 多节点工作流（输入、检索、LLM、输出）
- 条件路由和循环执行
- 状态管理和消息传递
"""

from .graph import create_workflow_graph, execute_workflow
from .nodes import (
    InputNode,
    DataSourceNode,
    RetrievalNode,
    LLMNode,
    ToolNode,
    OutputNode
)
from .state import WorkflowState
from .chat_handler import process_agent_chat

__all__ = [
    "create_workflow_graph",
    "execute_workflow",
    "InputNode",
    "DataSourceNode",
    "RetrievalNode",
    "LLMNode",
    "ToolNode",
    "OutputNode",
    "WorkflowState",
    "process_agent_chat",
]

