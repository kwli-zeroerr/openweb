"""
LangGraph 工作流状态定义
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class Message(BaseModel):
    """节点间传递的消息"""
    type: str  # "user", "context", "text", "json"
    payload: Any


class WorkflowState(BaseModel):
    """工作流全局状态"""
    # 节点ID -> 端口 -> 消息
    messages: Dict[str, Dict[str, Message]] = {}
    
    # 当前执行路径（用于调试）
    execution_path: List[str] = []
    
    # 元数据
    question: str = ""
    start_time: Optional[float] = None
    timings: Dict[str, float] = {}
    
    # 最终结果
    retrieved_context: Optional[str] = None
    llm_output: Optional[str] = None
    total: int = 0
    documents: List[Dict[str, Any]] = []
    scores: List[float] = []
    
    class Config:
        arbitrary_types_allowed = True

