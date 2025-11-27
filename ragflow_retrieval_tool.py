"""
RAGFlow检索工具 - OpenWebUI工具模块
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserValves(BaseModel):
    """用户可配置的工具参数"""
    default_similarity_threshold: float = Field(
        0.2, 
        description="默认相似度阈值（0-1之间）",
        ge=0.0,
        le=1.0
    )
    default_page_size: int = Field(
        10,
        description="默认每页返回的chunk数量",
        ge=1,
        le=100
    )
    default_vector_similarity_weight: float = Field(
        0.3,
        description="默认向量相似度权重（0-1之间）",
        ge=0.0,
        le=1.0
    )
    default_top_k: int = Field(
        1024,
        description="默认参与向量计算的chunk数量",
        ge=1,
        le=10000
    )
    default_keyword: bool = Field(
        False,
        description="默认是否启用关键词匹配"
    )
    default_highlight: bool = Field(
        False,
        description="默认是否高亮匹配术语"
    )


class Tools:
    """RAGFlow检索工具类"""

    def __init__(self):
        pass

    def ragflow_retrieval(
        self,
        question: str,
        dataset_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        vector_similarity_weight: Optional[float] = None,
        top_k: Optional[int] = None,
        rerank_id: Optional[str] = None,
        keyword: Optional[bool] = None,
        highlight: Optional[bool] = None,
        cross_languages: Optional[List[str]] = None,
        metadata_condition: Optional[Dict[str, Any]] = None,
        __request__: Optional[Any] = None,
        __user__: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        使用RAGFlow从指定的知识库中检索相关文档片段。
        如果未指定dataset_ids，默认搜索所有数据库。

        :param question: 用户查询问题或关键词（必需）
        :param dataset_ids: 要搜索的数据集ID列表，为空时搜索所有数据库
        :param document_ids: 要搜索的文档ID列表
        :param page: 页码，默认为1
        :param page_size: 每页最大chunk数量，为空时使用用户配置的默认值
        :param similarity_threshold: 最小相似度分数，为空时使用用户配置的默认值
        :param vector_similarity_weight: 向量余弦相似度权重，为空时使用用户配置的默认值
        :param top_k: 参与向量余弦计算的chunk数量，为空时使用用户配置的默认值
        :param rerank_id: 重排序模型ID
        :param keyword: 是否启用基于关键词的匹配，为空时使用用户配置的默认值
        :param highlight: 是否在结果中高亮匹配的术语，为空时使用用户配置的默认值
        :param cross_languages: 应该翻译成的语言列表，用于跨语言检索
        :param metadata_condition: 元数据过滤条件（字典格式）

        :return: 检索结果的JSON字符串，包含question、total、documents和scores
        """
        # 清理参数：移除 FieldInfo 对象，使用实际值或 None
        try:
            from pydantic import FieldInfo
        except ImportError:
            FieldInfo = type(None)  # Fallback if FieldInfo not available
        
        def clean_param(value, default=None):
            """清理参数，如果是 FieldInfo 对象则返回默认值"""
            if value is None:
                return default
            # 检查是否是 FieldInfo 对象
            if hasattr(value, '__class__') and 'FieldInfo' in str(type(value)):
                return default
            # 检查是否是 FieldInfo 实例
            try:
                if isinstance(value, FieldInfo):
                    return default
            except:
                pass
            return value
        
        # 清理所有可能包含 FieldInfo 的参数
        question = clean_param(question) or ""
        dataset_ids = clean_param(dataset_ids)
        document_ids = clean_param(document_ids)
        page = clean_param(page, 1)
        if not isinstance(page, int):
            page = 1
        page_size = clean_param(page_size)
        similarity_threshold = clean_param(similarity_threshold)
        vector_similarity_weight = clean_param(vector_similarity_weight)
        top_k = clean_param(top_k)
        rerank_id = clean_param(rerank_id)
        keyword = clean_param(keyword)
        highlight = clean_param(highlight)
        cross_languages = clean_param(cross_languages)
        metadata_condition = clean_param(metadata_condition)
        
        # 确保 dataset_ids 和 document_ids 是列表或 None
        if dataset_ids is not None and not isinstance(dataset_ids, list):
            dataset_ids = None
        if document_ids is not None and not isinstance(document_ids, list):
            document_ids = None
        
        if not question:
            return json.dumps(
                {"error": "question 参数是必需的", "question": ""},
                ensure_ascii=False
            )
        
        try:
            # 直接导入，工具模块会在正确的路径下执行
            from open_webui.services.ragflow.chunk_management import (
                get_client as get_ragflow_chunk_client,
            )
            from open_webui.services.ragflow.dataset_management import (
                get_client as get_ragflow_dataset_client,
            )
        except ImportError as e:
            logger.error(f"无法导入RAGFlow模块: {e}")
            return json.dumps(
                {"error": f"无法导入RAGFlow模块: {e}", "question": question},
                ensure_ascii=False,
            )

        async def _async_retrieval():
            try:
                # 获取用户配置的默认值（从 UserValves）
                # __user__["valves"] 可能是 UserValves 对象（Pydantic 模型）或字典
                user_valves_raw = __user__.get("valves", {}) if __user__ else {}
                
                # 转换为字典（如果是 Pydantic 模型）
                if hasattr(user_valves_raw, 'model_dump'):
                    # Pydantic v2
                    user_valves = user_valves_raw.model_dump()
                elif hasattr(user_valves_raw, 'dict'):
                    # Pydantic v1
                    user_valves = user_valves_raw.dict()
                elif isinstance(user_valves_raw, dict):
                    user_valves = user_valves_raw
                else:
                    user_valves = {}
                
                # 使用用户配置的默认值，如果参数为 None
                final_page_size = page_size if page_size is not None else user_valves.get("default_page_size", 10)
                final_similarity_threshold = similarity_threshold if similarity_threshold is not None else user_valves.get("default_similarity_threshold", 0.2)
                final_vector_similarity_weight = vector_similarity_weight if vector_similarity_weight is not None else user_valves.get("default_vector_similarity_weight", 0.3)
                final_top_k = top_k if top_k is not None else user_valves.get("default_top_k", 1024)
                final_keyword = keyword if keyword is not None else user_valves.get("default_keyword", False)
                final_highlight = highlight if highlight is not None else user_valves.get("default_highlight", False)
                
                # 如果没有指定dataset_ids和document_ids，获取所有datasets
                final_dataset_ids = dataset_ids
                if not dataset_ids and not document_ids:
                    dataset_client = get_ragflow_dataset_client(__request__)
                    all_datasets = await dataset_client.list(page=1, page_size=1000)
                    final_dataset_ids = []
                    for ds in all_datasets:
                        dataset_id = (
                            ds.get("id") or ds.get("dataset_id") or ds.get("_id")
                        )
                        if dataset_id:
                            final_dataset_ids.append(str(dataset_id))

                    if not final_dataset_ids:
                        return json.dumps(
                            {"error": "没有可用的数据集", "question": question},
                            ensure_ascii=False
                        )

                # 处理metadata_condition
                final_metadata_condition = None
                if metadata_condition:
                    if isinstance(metadata_condition, dict):
                        final_metadata_condition = {"conditions": [metadata_condition]}
                    elif isinstance(metadata_condition, list):
                        final_metadata_condition = {"conditions": metadata_condition}

                # 获取RAGFlow客户端并执行检索
                chunk_client = get_ragflow_chunk_client(__request__)
                documents, scores = await chunk_client.retrieve(
                    question=question,
                    dataset_ids=final_dataset_ids or [],
                    document_ids=document_ids,
                    page=page,
                    page_size=final_page_size,
                    similarity_threshold=final_similarity_threshold,
                    vector_similarity_weight=final_vector_similarity_weight,
                    top_k=final_top_k,
                    rerank_id=rerank_id,
                    keyword=final_keyword,
                    highlight=final_highlight,
                    cross_languages=cross_languages,
                    metadata_condition=final_metadata_condition,
                )

                return json.dumps(
                    {
                        "question": question,
                        "total": len(documents),
                        "documents": documents,
                        "scores": scores,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            except Exception as e:
                logger.error(f"RAGFlow检索失败: {e}", exc_info=True)
                return json.dumps(
                    {"error": str(e), "question": question}, ensure_ascii=False
                )

        # 处理异步执行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，使用线程池
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _async_retrieval())
                    return future.result()
            else:
                return loop.run_until_complete(_async_retrieval())
        except RuntimeError:
            # 没有事件循环，创建一个新的
            return asyncio.run(_async_retrieval())

