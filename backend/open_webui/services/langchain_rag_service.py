"""
基于LangChain的RAG服务
涵盖：分段、向量化、检索、LLM调用
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from fastapi import Request

from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

@dataclass
class LangChainRAGQuery:
    """LangChain RAG查询"""
    query: str
    collection_name: str
    top_k: int = 5
    use_reranking: bool = True
    mode: str = "hybrid"  # vector, bm25, hybrid
    bm25_weight: Optional[float] = None  # 混合检索时BM25权重（0-1），为空则用默认

@dataclass
class LangChainRAGResult:
    """LangChain RAG结果"""
    query: str
    answer: str
    documents: List[Document]
    retrieval_scores: List[float]
    rerank_scores: Optional[List[float]] = None
    method: str = "hybrid"
    retrieval_time: Optional[float] = None  # 检索耗时（秒）

class LangChainRAGService:
    """基于LangChain的完整RAG服务"""
    
    def __init__(self, embedding_model: str = None, embedding_function=None):
        """
        初始化RAG服务
        
        Args:
            embedding_model: embedding模型名称（已忽略，强制使用vLLM服务）
            embedding_function: 预配置的embedding函数（已忽略，强制使用vLLM服务）
        """
        # vLLM Embedding 服务地址由配置提供，保留默认
        self._vllm_api_url = None  # 由 get_embeddings_client 动态解析
        self._vllm_base_url = None
        
        # 标记：强制使用vLLM服务，忽略其他配置
        self._use_external_embedding = True
        self._embedding_function = None  # 不使用外部函数
        self.embeddings = None  # 不使用LangChain的HuggingFaceEmbeddings
        self._embedding_model = "vllm_embedding_service"  # 保留属性以避免AttributeError，值表示使用vLLM服务
        
        # 仅在首次使用时从 request 配置解析 URL（见 _get_client）
        
        # 向量存储（内存）
        self.vector_stores: Dict[str, Any] = {}
        
        # LLM（延迟初始化）
        self._llm = None
    
    
    def _get_client(self, request=None):
        try:
            from .embeddings_client import get_embeddings_client, _get_vllm_url_from_request
            client = get_embeddings_client(request)
            # 缓存展示用 base_url
            base = _get_vllm_url_from_request(request)
            self._vllm_api_url = base
            self._vllm_base_url = f"{base}/v1/embeddings"
            return client
        except Exception as e:
            raise ValueError(f"Cannot init embeddings client: {e}")

    async def _embed_text(self, text: str, request=None) -> List[float]:
        """嵌入文本（统一接口）- 强制使用vLLM服务"""
        try:
            client = self._get_client(request)
            return await client.embed_one(text)
        except Exception as e:
            logger.error(f"⚠️ vLLM Embedding API failed (url={self._vllm_base_url}): {e}", exc_info=True)
            raise ValueError(f"vLLM Embedding API failed: {e}")
    
    async def _embed_texts_batch(self, texts: List[str], request=None) -> List[List[float]]:
        """批量嵌入文本（统一接口）- 强制使用vLLM服务"""
        try:
            client = self._get_client(None)
            return await client.embed_batch(texts)
        except Exception as e:
            logger.error(f"⚠️ vLLM Embedding API batch failed (url={self._vllm_base_url}): {e}", exc_info=True)
            raise ValueError(f"vLLM Embedding API batch failed: {e}")
    
    def get_llm(self, request=None):
        """LLM 功能已移除，返回 text_only。"""
        return "text_only"
    
    def chunk_markdown(
        self, 
        text: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        use_header_splitter: bool = True
    ) -> List[Document]:
        """
        Markdown文档分段
        
        Args:
            text: Markdown文本
            chunk_size: 分段大小
            chunk_overlap: 重叠大小
            use_header_splitter: 是否使用标题分割器
        
        Returns:
            分段后的Document列表
        """
        if use_header_splitter:
            # 按标题层级分割
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on,
                strip_headers=False
            )
            
            # 分割
            splits = splitter.split_text(text)
            
            # 如果段落太长，再递归分割
            if any(len(split.page_content) > chunk_size for split in splits):
                recursive_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", "。", " ", ""]
                )
                final_splits = []
                for split in splits:
                    if len(split.page_content) > chunk_size:
                        sub_splits = recursive_splitter.split_documents([split])
                        for sub in sub_splits:
                            final_splits.append(Document(
                                page_content=sub.page_content,
                                metadata={**split.metadata, **sub.metadata}
                            ))
                    else:
                        final_splits.append(split)
                return final_splits
            
            return splits
        else:
            # 纯文本分段
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", "。", " ", ""]
            )
            return text_splitter.create_documents([text])
    
    async def load_collection(
        self, 
        collection_name: str, 
        documents: List[Document],
        use_faiss: bool = False
    ):
        """
        加载文档到检索索引
        
        Args:
            collection_name: 集合名称
            documents: 文档列表
            use_faiss: 是否使用FAISS（需要安装）
        """
        # ⚠️ 记录加载信息（强制使用vLLM服务）
        logger.info(f"Loading collection '{collection_name}' with {len(documents)} documents")
        
        # 创建向量存储（仅内存存储，使用 vLLM 批量向量化）
        # 批量向量化
        texts = [doc.page_content for doc in documents]
        
        try:
            vectors = await self._embed_texts_batch(texts)
            
            # 验证向量数量
            if len(vectors) != len(documents):
                logger.warning(f"⚠️ 向量数量不匹配: {len(vectors)} vectors for {len(documents)} documents")
                # 只保留成功向量化的文档
                documents = documents[:len(vectors)]
                vectors = vectors[:len(documents)]
            
            # 记录向量维度（可选）
        except Exception as e:
            logger.error(f"❌ vLLM批量向量化失败: {e}")
            vectors = []
        
        if len(vectors) != len(documents):
            logger.warning(f"Vector count mismatch: {len(vectors)} vectors for {len(documents)} documents")
            # 只保留成功向量化的文档
            documents = [doc for i, doc in enumerate(documents) if i < len(vectors)]
        
        if len(vectors) == 0:
            logger.error(f"No valid vectors generated for collection {collection_name}")
            self.vector_stores[collection_name] = {
                "docs": [],
                "vectors": []
            }
        else:
            self.vector_stores[collection_name] = {
                "docs": documents[:len(vectors)],
                "vectors": vectors
            }
        
        logger.info(f"Collection '{collection_name}' loaded: {len(documents)} docs")
    
    async def vector_search(
        self, 
        query: str, 
        collection_name: str, 
        top_k: int = 5,
        use_weighted_multi_channel: bool = True
    ) -> List[Tuple[Document, float]]:
        """纯向量检索
        
        如果use_weighted_multi_channel=True，支持多通道加权检索（标题0.15、内容0.7、问题0.15）
        
        优化：如果内存中没有缓存，直接从向量数据库检索，避免重新向量化
        """
        # 向量检索（内存或直连向量库）
        
        # ⚠️ 如果内存中没有缓存，直接从向量数据库检索（优化：避免重新向量化）
        if collection_name not in self.vector_stores:
            # 未缓存时，直接从向量数据库检索
            return await self._vector_search_direct(collection_name, query, top_k, use_weighted_multi_channel)
        
        vector_store = self.vector_stores[collection_name]
        
        query_vector = await self._embed_text(query)
        
        # 调试信息：检查查询向量
        if not query_vector or len(query_vector) == 0:
            logger.error(f"Query vector is empty or None for query: {query[:50]}...")
            return []
        
        # 简单内存搜索（本服务仅写入 dict 存储）
            docs = vector_store["docs"]
            vectors = vector_store["vectors"]
            
        if not vectors or len(vectors) == 0:
            logger.warning(f"No vectors found in collection {collection_name}")
            return []
        
        # 检查向量维度
        query_dim = len(query_vector)
        doc_dim = len(vectors[0]) if vectors else 0
        if query_dim != doc_dim:
            logger.error(f"Vector dimension mismatch: query={query_dim}, document={doc_dim}")
            return []
            
            import numpy as np
        query_array = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query_array)
        if query_norm == 0:
            logger.warning("Query vector is zero vector, cannot compute similarities")
            return []
        
        similarities = []
        for vec in vectors:
            vec_array = np.array(vec, dtype=np.float32)
            vec_norm = np.linalg.norm(vec_array)
            if vec_norm == 0:
                similarities.append(0.0)
            else:
                sim = float(np.dot(query_array, vec_array) / (query_norm * vec_norm))
                similarities.append(0.0 if (np.isnan(sim) or np.isinf(sim)) else sim)
            
            if use_weighted_multi_channel:
                search_limit = min(len(docs), top_k * 5)
                preliminary_ranked = sorted(zip(docs, similarities), key=lambda x: x[1], reverse=True)[:search_limit]
                preliminary_docs = [d for d, _ in preliminary_ranked]
                preliminary_scores = [s for _, s in preliminary_ranked]
                return await self._weighted_multi_channel_search(preliminary_docs, preliminary_scores, top_k)
            else:
                ranked = sorted(zip(docs, similarities), key=lambda x: x[1], reverse=True)
            results = ranked[:top_k]
        
        return results
    
    async def _vector_search_direct(
        self,
        collection_name: str,
        query: str,
        top_k: int,
        use_weighted_multi_channel: bool
    ) -> List[Tuple[Document, float]]:
        """直接从向量数据库检索，不加载到内存（优化性能）"""
        import time
        start_time = time.time()
        
        try:
            from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
            from langchain_core.documents import Document
            
            # 0. 查找实际集合名称（尝试多种格式）
            actual_collection_name = None
            possible_collection_names = [
                collection_name,  # 直接使用知识库ID
                f"knowledge_{collection_name}",
                f"kb_{collection_name}",
            ]
            
            for candidate_name in possible_collection_names:
                if VECTOR_DB_CLIENT.has_collection(candidate_name):
                    actual_collection_name = candidate_name
                    logger.info(f"✅ Found collection: {actual_collection_name}")
                    break
            
            # 如果还没找到，尝试列出所有集合
            if not actual_collection_name and hasattr(VECTOR_DB_CLIENT, 'list_collections'):
                try:
                    all_collections = VECTOR_DB_CLIENT.list_collections()
                    logger.debug(f"Available collections: {all_collections}")
                    
                    # 查找包含知识库ID的集合
                    for coll_name in all_collections:
                        if collection_name in coll_name or coll_name == collection_name:
                            actual_collection_name = coll_name
                            logger.info(f"✅ Found matching collection: {actual_collection_name}")
                            break
                    
                    # 如果仍然没找到，使用第一个可用集合（作为后备）
                    if not actual_collection_name and all_collections:
                        actual_collection_name = all_collections[0]
                        logger.warning(f"⚠️ Using first available collection as fallback: {actual_collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to list collections: {e}")
            
            if not actual_collection_name:
                logger.error(f"❌ No collection found for '{collection_name}'. Tried: {possible_collection_names}")
                return []
            
            # 1. 向量化查询（使用vLLM服务）
            query_vector = await self._embed_text(query)
            logger.debug(f"✅ Query vectorized via vLLM: dimension={len(query_vector) if query_vector else 0}")
            
            if not query_vector or len(query_vector) == 0:
                logger.error(f"Query vector is empty or None for query: {query[:50]}...")
                return []
            
            # 2. 直接从向量数据库搜索（使用实际找到的集合名称）
            logger.debug(f"🔍 Searching in collection: {actual_collection_name}, query vector dimension: {len(query_vector)}")
            
            # 检查向量维度是否匹配（如果集合已有向量）
            try:
                # 获取集合中的第一个向量来检查维度
                check_result = VECTOR_DB_CLIENT.get(actual_collection_name, limit=1)
                if check_result and check_result.ids and check_result.ids[0]:
                    # 如果能获取到向量，检查维度
                    # 注意：某些向量DB的get方法可能不返回向量，只返回metadata
                    logger.debug(f"Collection '{actual_collection_name}' has documents, proceeding with search")
            except Exception as e:
                logger.debug(f"Could not pre-check collection: {e}")
            
            # 先验证集合确实存在且可访问
            try:
                if not VECTOR_DB_CLIENT.has_collection(actual_collection_name):
                    logger.error(f"❌ Collection '{actual_collection_name}' does not exist (has_collection returned False)")
                    return []
            except Exception as e:
                logger.warning(f"Could not verify collection existence: {e}")
            
            # 执行搜索
            try:
                search_result = await asyncio.to_thread(
                    VECTOR_DB_CLIENT.search,
                    collection_name=actual_collection_name,
                    vectors=[query_vector],
                    limit=top_k * 5 if use_weighted_multi_channel else top_k
                )
            except Exception as e:
                logger.error(f"Vector DB search failed for collection '{actual_collection_name}': {e}", exc_info=True)
                # 检查是否是维度不匹配的问题
                if "dimension" in str(e).lower() or "size" in str(e).lower():
                    logger.error(f"⚠️ Possible dimension mismatch! Query vector: {len(query_vector)} dimensions")
                # 尝试获取集合信息来诊断问题
                try:
                    check_result = VECTOR_DB_CLIENT.get(actual_collection_name)
                    if check_result:
                        logger.error(f"Collection exists but search failed. Collection info: {len(check_result.ids[0]) if check_result.ids and check_result.ids[0] else 0} items")
                except:
                    pass
                return []
            
            # 检查搜索结果
            if not search_result:
                logger.warning(f"Search returned None for collection '{actual_collection_name}'")
                # 可能是集合存在但没有数据，或get_collection失败
                try:
                    check_result = VECTOR_DB_CLIENT.get(actual_collection_name)
                    if check_result and check_result.documents and check_result.documents[0]:
                        doc_count = len(check_result.documents[0])
                        logger.warning(f"Collection '{actual_collection_name}' has {doc_count} documents but search returned None")
                        logger.warning(f"⚠️ This might indicate the collection exists but search method failed")
                    else:
                        logger.warning(f"Collection '{actual_collection_name}' appears to be empty or inaccessible")
                except Exception as e:
                    logger.warning(f"Could not check collection contents: {e}")
                return []
            
            if not search_result.documents or not search_result.documents[0]:
                logger.warning(f"No documents in search result for collection '{actual_collection_name}'")
                return []
            
            # 3. 转换为Document格式
            docs = []
            scores = []
            
            for i, doc_text in enumerate(search_result.documents[0]):
                # 获取metadata
                metadata = search_result.metadatas[0][i] if search_result.metadatas and search_result.metadatas[0] else {}
                
                # 获取距离并转换为相似度分数
                distance = search_result.distances[0][i] if search_result.distances and search_result.distances[0] else 1.0
                # Chroma距离: 0(最好) -> 2(最差)，转换为相似度: 1(最好) -> 0(最差)
                similarity = 1.0 - (distance / 2.0) if distance <= 2.0 else 0.0
                
                doc = Document(
                    page_content=doc_text,
                    metadata={**metadata, "distance": distance}
                )
                docs.append(doc)
                scores.append(similarity)
            
            # 4. 如果需要多通道加权检索
            if use_weighted_multi_channel:
                results = await self._weighted_multi_channel_search(docs, scores, top_k)
            else:
                # 按分数排序
                results = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:top_k]
            
            # 记录检索时间
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Direct vector DB search completed in {elapsed_time:.3f}s, found {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"Direct vector DB search failed: {e}", exc_info=True)
            return []
    
    async def _weighted_multi_channel_search(
        self,
        docs: List[Document],
        similarities: List[float],
        top_k: int
    ) -> List[Tuple[Document, float]]:
        """多通道加权检索：标题0.15、内容0.7、问题0.15"""
        import numpy as np
        
        # 按segment_id和type分组
        segment_scores: Dict[str, Dict[str, Tuple[Document, float, float]]] = {}  # (doc, original_score, weighted_score)
        old_data_results: List[Tuple[Document, float]] = []  # 旧数据（无segment_id）
        
        for doc, score in zip(docs, similarities):
            meta = doc.metadata or {}
            segment_id = meta.get("segment_id", "")
            doc_type = meta.get("type", "content")
            weight = meta.get("weight", 0.7)  # 默认权重：标题0.15、内容0.7、问题0.15
            
            # 加权分数
            weighted_score = score * weight
            
            if not segment_id:
                # 没有segment_id的旧数据，直接使用加权分数（向后兼容）
                old_data_results.append((doc, weighted_score))
                continue
            
            if segment_id not in segment_scores:
                segment_scores[segment_id] = {}
            
            # 同一分段的同一类型只保留最高分（按加权分数比较，但保存原始分数）
            current_best = segment_scores[segment_id].get(doc_type)
            if not current_best or weighted_score > current_best[2]:  # 比较加权分数
                segment_scores[segment_id][doc_type] = (doc, score, weighted_score)  # 保存原始分数和加权分数
        
        # 合并同一分段的不同类型，累加分数
        merged_results: Dict[str, Tuple[Document, float]] = {}
        for segment_id, type_scores in segment_scores.items():
            total_score = sum(weighted_score for _, _, weighted_score in type_scores.values())  # 累加加权分数
            # 构建完整的代表Document，包含标题+内容+问题
            title_data = type_scores.get("title")  # (doc, original_score, weighted_score)
            content_data = type_scores.get("content")
            questions_data = type_scores.get("questions")
            
            # 优先使用content作为基础
            base_doc_data = content_data if content_data else (title_data if title_data else questions_data if questions_data else None)
            if not base_doc_data or not isinstance(base_doc_data, tuple) or len(base_doc_data) < 3:
                continue
            base_doc = base_doc_data[0]
            
            # 提取各通道的原始分数和加权分数（安全访问）
            title_original = title_data[1] if (title_data and isinstance(title_data, tuple) and len(title_data) >= 3) else None
            title_weighted = title_data[2] if (title_data and isinstance(title_data, tuple) and len(title_data) >= 3) else None
            content_original = content_data[1] if (content_data and isinstance(content_data, tuple) and len(content_data) >= 3) else None
            content_weighted = content_data[2] if (content_data and isinstance(content_data, tuple) and len(content_data) >= 3) else None
            questions_original = questions_data[1] if (questions_data and isinstance(questions_data, tuple) and len(questions_data) >= 3) else None
            questions_weighted = questions_data[2] if (questions_data and isinstance(questions_data, tuple) and len(questions_data) >= 3) else None
            
            # 获取Document对象用于构建内容（安全访问）
            title_doc = title_data[0] if (title_data and isinstance(title_data, tuple) and len(title_data) >= 1) else None
            content_doc = content_data[0] if (content_data and isinstance(content_data, tuple) and len(content_data) >= 1) else None
            questions_doc = questions_data[0] if (questions_data and isinstance(questions_data, tuple) and len(questions_data) >= 1) else None
            
            # 构建完整的文本内容（标题 + 内容 + 问题）
            full_content_parts = []
            if title_doc:
                # 从面包屑格式中提取标题部分
                title_text = title_doc.page_content  # title_doc 已经是 Document 对象，不需要 [0]
                if ":" in title_text:
                    full_content_parts.append(title_text.split(":", 1)[1].strip())
            if content_doc:
                content_text = content_doc.page_content  # content_doc 已经是 Document 对象，不需要 [0]
                if ":" in content_text:
                    full_content_parts.append(content_text.split(":", 1)[1].strip())
            if questions_doc:
                questions_text = questions_doc.page_content  # questions_doc 已经是 Document 对象，不需要 [0]
                if ":" in questions_text:
                    full_content_parts.append(f"问题（选填，单元格内一行一个）: {questions_text.split(':', 1)[1].strip()}")
            
            # 更新metadata，添加各通道分数信息
            updated_metadata = base_doc.metadata.copy() if base_doc.metadata else {}
            updated_metadata["channel_scores"] = {
                "title_original": title_original,
                "content_original": content_original,
                "questions_original": questions_original,
                "title_weighted": title_weighted,
                "content_weighted": content_weighted,
                "questions_weighted": questions_weighted,
            }
            
            # 创建新的Document，使用完整内容
            merged_doc = Document(
                page_content="\n\n".join(full_content_parts) if full_content_parts else base_doc.page_content,
                metadata=updated_metadata
            )
            merged_results[segment_id] = (merged_doc, total_score)
        
        # 合并新旧数据并排序
        all_results = list(merged_results.values()) + old_data_results
        ranked = sorted(all_results, key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    
    # 已移除：从外部向量库结果做多通道加权的分支
    
    # 已移除：BM25 检索相关实现

    def _clean_text(self, text: str) -> str:
        """轻量清洗：去 HTML 标签、多余空白"""
        try:
            import re
            # 去标签
            t = re.sub(r"<[^>]+>", " ", text)
            # 合并空白
            t = re.sub(r"\s+", " ", t).strip()
            return t
        except Exception:
            return text
    
    # 已移除：Hybrid 检索相关实现
    
    
    
    async def generate_answer(self, query: str, context: str, request=None) -> str:
        """LLM 已移除：直接返回上下文。"""
        return context
    
    async def query(self, rag_query: LangChainRAGQuery, request=None) -> LangChainRAGResult:
        """
        执行RAG查询（完整流程）
        
        Args:
            rag_query: RAG查询对象
        
        Returns:
            RAG查询结果
        """
        import time
        retrieval_start_time = time.time()
        
        # 1. 仅向量检索
        results = await self.vector_search(
                rag_query.query, 
                rag_query.collection_name, 
                rag_query.top_k
            )
        documents = [doc for doc, score in results]
        scores = [score for doc, score in results]
        method = "vector"
        
        # 计算检索时间
        retrieval_time = time.time() - retrieval_start_time
        
        if not documents:
            return LangChainRAGResult(
                query=rag_query.query,
                answer="未找到相关文档",
                documents=[],
                retrieval_scores=[],
                method=method,
                retrieval_time=retrieval_time
            )
        
        # 2. 重排序已移除
        rerank_scores = None
        
        # 3. 构建上下文
        context = "\n\n".join([
            f"文档 {i+1}:\n{doc.page_content[:500]}"
            for i, doc in enumerate(documents[:3])
        ])
        
        # 4. 生成回答
        answer = await self.generate_answer(rag_query.query, context, request)
        
        return LangChainRAGResult(
            query=rag_query.query,
            answer=answer,
            documents=documents,
            retrieval_scores=scores[:len(documents)],
            rerank_scores=rerank_scores,
            method=method,
            retrieval_time=retrieval_time
        )

# 全局实例缓存：基于embedding配置的键来缓存实例
# 这样可以确保相同的embedding配置使用同一个实例（共享vector_stores）
_langchain_rag_service_instances: Dict[str, LangChainRAGService] = {}

def _get_instance_key(request: Request = None) -> str:
    """生成实例缓存键，基于embedding配置"""
    if request is None:
        return "default"
    
    # 基于embedding engine和model生成键
    embedding_engine = getattr(request.app.state.config, 'RAG_EMBEDDING_ENGINE', '')
    embedding_model = getattr(request.app.state.config, 'RAG_EMBEDDING_MODEL', '')
    
    # 检查是否有EMBEDDING_FUNCTION
    has_ef = hasattr(request.app.state, 'EMBEDDING_FUNCTION') and request.app.state.EMBEDDING_FUNCTION is not None
    has_local_ef = hasattr(request.app.state, 'ef') and request.app.state.ef is not None
    
    if has_ef:
        return f"external_ef_{embedding_engine}_{embedding_model}"
    elif has_local_ef:
        return f"local_ef_{embedding_model}"
    else:
        return f"default_{embedding_model}"

def get_langchain_rag_service(request: Request = None) -> LangChainRAGService:
    """获取LangChainRAGService实例
    ⚠️ 强制使用 vLLM Embedding 服务 (192.168.1.232:8010)，忽略所有外部配置
    """
    global _langchain_rag_service_instances
    
    # ⚠️ 强制使用固定的实例键，确保所有实例都使用vLLM服务
    instance_key = "vllm_forced_service"
    
    # 如果已缓存，直接返回
    if instance_key in _langchain_rag_service_instances:
        logger.debug(f"✅ LangChainRAGService 复用已缓存实例 (强制使用vLLM服务)")
        return _langchain_rag_service_instances[instance_key]
    
    # ⚠️ 强制创建使用vLLM服务的新实例，忽略所有外部配置
    logger.info(f"⚠️ 强制创建 LangChainRAGService 实例，使用 vLLM Embedding 服务")
    logger.info(f"   vLLM API: http://192.168.1.232:8010/v1/embeddings")
    logger.info(f"   所有向量化和向量检索都将通过此服务进行！")
    
    # 忽略 request 中的所有 embedding 配置，强制使用vLLM
    service = LangChainRAGService()
    _langchain_rag_service_instances[instance_key] = service
    logger.info(f"✅ LangChainRAGService 创建完成 (强制使用vLLM服务)")
    return service

# 默认实例（向后兼容）
langchain_rag_service = LangChainRAGService()

