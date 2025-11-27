"""
Agent 路由模块

提供 Agent 相关的 API 接口
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

# 导入检索API路由
from open_webui.agent.retrieval_api import router as retrieval_router
router.include_router(retrieval_router)

# 导入RAG API路由（Excel迁移等功能）
from open_webui.agent.rag_api import router as rag_router
router.include_router(rag_router)


############################
# Agent API
############################


@router.get("/")
async def get_agent(request: Request, user=Depends(get_verified_user)):
    """
    获取 Agent 信息（占位接口）
    """
    return {
        "message": "Agent API endpoint",
        "status": "ready"
    }


