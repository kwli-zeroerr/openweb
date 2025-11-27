"""
知识库检索API
迁移自 rag_api.py 中的检索功能
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import time

from open_webui.services.ragflow.chunk_management import get_client as get_ragflow_chunk_client
from open_webui.services.ragflow.dataset_management import get_client as get_ragflow_dataset_client
from open_webui.utils.auth import get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== RAGFlow 检索功能 ==========

class RagFlowRetrievalRequest(BaseModel):
    """RAGFlow检索请求"""
    question: str  # 查询问题
    dataset_id: Optional[str] = None  # Dataset ID（单数，向后兼容）
    dataset_ids: Optional[List[str]] = None  # Dataset ID列表（支持多知识库检索）
    document_ids: Optional[List[str]] = None  # 可选的文档ID列表，如果指定则只在这些文档中检索
    page: Optional[int] = 1  # 页码
    page_size: Optional[int] = 10  # 每页结果数
    similarity_threshold: Optional[float] = None  # 相似度阈值（0-1）
    vector_similarity_weight: Optional[float] = None  # 向量相似度权重（0-1）
    top_k: Optional[int] = None  # 向量检索的top_k
    keyword: Optional[bool] = True  # 是否启用关键词匹配
    highlight: Optional[bool] = True  # 是否启用高亮


class RagFlowRetrievalResponse(BaseModel):
    """RAGFlow检索响应"""
    question: str
    total: int  # 总结果数
    documents: List[Dict[str, Any]]  # 检索到的文档列表
    scores: List[float]  # 相似度分数列表
    retrieval_time: Optional[float] = None  # 检索耗时（秒）


@router.get("/retrieval/datasets")
async def ragflow_list_datasets(request: Request, user=Depends(get_verified_user)):
    """获取所有RAGFlow datasets列表，返回id和name用于前端选择"""
    try:
        dataset_client = get_ragflow_dataset_client(request)
        datasets = await dataset_client.list(page=1, page_size=1000)  # 获取所有datasets
        
        # 提取id和name
        dataset_list = []
        for ds in datasets:
            dataset_id = ds.get("id") or ds.get("dataset_id") or ds.get("_id")
            dataset_name = ds.get("name", "")
            if dataset_id and dataset_name:
                dataset_list.append({
                    "id": str(dataset_id),
                    "name": dataset_name,
                    "description": ds.get("description", ""),
                    "document_count": ds.get("document_count", 0),
                    "chunk_count": ds.get("chunk_count", 0),
                })
        
        # 按名称排序
        dataset_list.sort(key=lambda x: x["name"])
        
        return {
            "datasets": dataset_list,
            "total": len(dataset_list)
        }
    except Exception as e:
        logger.error(f"ragflow_list_datasets failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取datasets列表失败: {e}")


@router.post("/retrieval", response_model=RagFlowRetrievalResponse)
async def ragflow_retrieval(req: RagFlowRetrievalRequest, request: Request, user=Depends(get_verified_user)):
    """RAGFlow知识库检索（支持多知识库）"""
    try:
        # 处理dataset_ids：优先使用dataset_ids列表，如果没有则使用dataset_id（向后兼容）
        final_dataset_ids: List[str] = []
        if req.dataset_ids:
            final_dataset_ids = req.dataset_ids
        elif req.dataset_id:
            final_dataset_ids = [req.dataset_id]
        else:
            raise HTTPException(status_code=400, detail="必须指定dataset_id或dataset_ids")
        
        if not final_dataset_ids:
            raise HTTPException(status_code=400, detail="至少需要指定一个知识库")
        
        start_time = time.time()
        chunk_client = get_ragflow_chunk_client(request)
        
        documents, scores = await chunk_client.retrieve(
            question=req.question,
            dataset_ids=final_dataset_ids,
            document_ids=req.document_ids,
            page=req.page,
            page_size=req.page_size,
            similarity_threshold=req.similarity_threshold,
            vector_similarity_weight=req.vector_similarity_weight,
            top_k=req.top_k,
            keyword=req.keyword,
            highlight=req.highlight,
        )
        
        retrieval_time = time.time() - start_time
        
        return RagFlowRetrievalResponse(
            question=req.question,
            total=len(documents),
            documents=documents,
            scores=scores,
            retrieval_time=retrieval_time,
        )
    except Exception as e:
        logger.error(f"ragflow_retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")

