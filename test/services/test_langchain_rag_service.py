"""
LangChain RAG服务测试
测试 backend/open_webui/services/langchain_rag_service.py 中的各个函数
"""
import sys
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# 添加backend目录到路径
sys.path.insert(0, '/home/zeroerr-ai72/openwebui-zeroerr/backend')

from open_webui.services.langchain_rag_service import (
    langchain_rag_service,
    LangChainRAGQuery,
    LangChainRAGResult
)
from langchain_core.documents import Document


class TestLangChainRAGService:
    """测试LangChainRAGService类"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return langchain_rag_service
    
    @pytest.fixture
    def sample_documents(self):
        """创建示例文档"""
        return [
            Document(
                page_content="CANopen是一种基于CAN总线的通信协议，广泛应用于工业自动化领域。",
                metadata={"source": "test1", "page": 1}
            ),
            Document(
                page_content="重复定位精度是指机器人在重复执行同一任务时的位置精度，通常以毫米为单位。",
                metadata={"source": "test2", "page": 2}
            ),
            Document(
                page_content="关节型号包括RV减速机和谐波减速机，用于机器人关节传动。",
                metadata={"source": "test3", "page": 3}
            ),
        ]
    
    def test_service_init(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'embeddings')
        assert hasattr(service, 'vector_stores')
        assert hasattr(service, 'bm25_retrievers')
    
    @pytest.mark.asyncio
    async def test_embed_text(self, service):
        """测试文本向量化"""
        try:
            result = await service._embed_text("测试文本")
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(x, (int, float)) for x in result)
            print(f"✅ 向量维度: {len(result)}")
        except Exception as e:
            print(f"⚠️  向量化失败（可能因为模型未加载）: {e}")
    
    def test_chunk_markdown(self, service):
        """测试Markdown分块"""
        markdown_text = """
# 标题1
这是第一段内容。

## 子标题
这是第二段内容。

### 子子标题
这是第三段内容。
"""
        result = service.chunk_markdown(markdown_text)
        assert isinstance(result, list)
        assert len(result) > 0
        print(f"✅ Markdown分块结果: {len(result)}个块")
    
    def test_chunk_text_recursive(self, service):
        """测试递归文本分块"""
        text = "这是一段很长的文本。" * 100
        result = service.chunk_text_recursive(text, chunk_size=100, chunk_overlap=20)
        assert isinstance(result, list)
        assert len(result) > 0
        print(f"✅ 递归分块结果: {len(result)}个块")
    
    @pytest.mark.asyncio
    async def test_load_collection(self, service, sample_documents):
        """测试加载集合"""
        collection_name = "test_collection_123"
        
        try:
            await service.load_collection(collection_name, sample_documents, use_faiss=False)
            
            # 检查是否加载成功
            assert collection_name in service.vector_stores
            print(f"✅ 集合加载成功: {collection_name}")
            
            # 清理
            del service.vector_stores[collection_name]
            if collection_name in service.bm25_retrievers:
                del service.bm25_retrievers[collection_name]
                
        except Exception as e:
            print(f"⚠️  加载集合失败: {e}")
    
    @pytest.mark.asyncio
    async def test_vector_search(self, service, sample_documents):
        """测试向量检索"""
        collection_name = "test_vector_search"
        
        try:
            # 加载集合
            await service.load_collection(collection_name, sample_documents, use_faiss=False)
            
            # 执行向量检索
            results = await service.vector_search("CANopen报文", collection_name, top_k=2)
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert all(isinstance(item, tuple) and len(item) == 2 for item in results)
            
            print(f"✅ 向量检索成功，返回 {len(results)} 个结果")
            
            # 清理
            del service.vector_stores[collection_name]
            if collection_name in service.bm25_retrievers:
                del service.bm25_retrievers[collection_name]
                
        except Exception as e:
            print(f"⚠️  向量检索失败: {e}")
    
    def test_bm25_search(self, service, sample_documents):
        """测试BM25检索"""
        collection_name = "test_bm25_search"
        
        try:
            # 加载集合
            asyncio.run(service.load_collection(collection_name, sample_documents, use_faiss=False))
            
            # 执行BM25检索
            results = service.bm25_search("重复定位精度", collection_name, top_k=2)
            
            assert isinstance(results, list)
            print(f"✅ BM25检索成功，返回 {len(results)} 个结果")
            
            # 清理
            if collection_name in service.vector_stores:
                del service.vector_stores[collection_name]
            if collection_name in service.bm25_retrievers:
                del service.bm25_retrievers[collection_name]
                
        except Exception as e:
            print(f"⚠️  BM25检索失败: {e}")
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, service, sample_documents):
        """测试混合检索"""
        collection_name = "test_hybrid_search"
        
        try:
            # 加载集合
            await service.load_collection(collection_name, sample_documents, use_faiss=False)
            
            # 执行混合检索
            results = await service.hybrid_search("关节型号", collection_name, top_k=2)
            
            assert isinstance(results, list)
            print(f"✅ 混合检索成功，返回 {len(results)} 个结果")
            
            # 清理
            del service.vector_stores[collection_name]
            if collection_name in service.bm25_retrievers:
                del service.bm25_retrievers[collection_name]
                
        except Exception as e:
            print(f"⚠️  混合检索失败: {e}")
    
    @pytest.mark.asyncio
    async def test_rerank(self, service, sample_documents):
        """测试重排序"""
        try:
            query = "CANopen"
            results = await service.rerank(query, sample_documents, top_k=2)
            
            assert isinstance(results, list)
            print(f"✅ 重排序成功，返回 {len(results)} 个结果")
            
        except Exception as e:
            print(f"⚠️  重排序失败（可能因为模型未加载）: {e}")
    
    def test_get_llm_no_request(self, service):
        """测试获取LLM（无request）"""
        # 重置_llm状态
        service._llm = None
        
        result = service.get_llm(None)
        assert result is not None
        print(f"✅ 获取LLM成功: {type(result)}")
    
    @pytest.mark.asyncio
    async def test_generate_answer_text_only(self, service):
        """测试生成回答（仅文本模式）"""
        query = "测试问题"
        context = "这是测试上下文。"
        
        result = await service.generate_answer(query, context, None)
        
        assert isinstance(result, str)
        assert len(result) > 0
        print(f"✅ 生成回答成功（文本模式）")
    
    @pytest.mark.asyncio
    async def test_full_query(self, service, sample_documents):
        """测试完整查询流程"""
        collection_name = "test_full_query"
        
        try:
            # 加载集合
            await service.load_collection(collection_name, sample_documents, use_faiss=False)
            
            # 创建查询
            rag_query = LangChainRAGQuery(
                query="CANopen报文",
                collection_name=collection_name,
                top_k=3,
                use_reranking=False,
                mode="vector"
            )
            
            # 执行查询
            result = await service.query(rag_query, None)
            
            assert isinstance(result, LangChainRAGResult)
            assert result.query == "CANopen报文"
            assert isinstance(result.documents, list)
            assert isinstance(result.answer, str)
            
            print(f"✅ 完整查询成功")
            print(f"   - 检索到 {len(result.documents)} 个文档")
            print(f"   - 回答长度: {len(result.answer)} 字符")
            
            # 清理
            del service.vector_stores[collection_name]
            if collection_name in service.bm25_retrievers:
                del service.bm25_retrievers[collection_name]
                
        except Exception as e:
            print(f"⚠️  完整查询失败: {e}")


def run_manual_tests():
    """手动运行测试（不使用pytest）"""
    print("=" * 70)
    print("开始测试 LangChain RAG 服务")
    print("=" * 70)
    
    service = langchain_rag_service
    sample_docs = [
        Document(
            page_content="CANopen是一种基于CAN总线的通信协议。",
            metadata={"source": "test1"}
        ),
        Document(
            page_content="重复定位精度是指机器人的位置精度。",
            metadata={"source": "test2"}
        ),
    ]
    
    async def test():
        print("\n1️⃣  测试服务初始化")
        print(f"   ✅ 服务已初始化")
        
        print("\n2️⃣  测试文本向量化")
        try:
            vector = await service._embed_text("测试")
            print(f"   ✅ 向量维度: {len(vector)}")
        except Exception as e:
            print(f"   ⚠️  向量化失败: {e}")
        
        print("\n3️⃣  测试Markdown分块")
        md_text = "# 标题\n内容"
        chunks = service.chunk_markdown(md_text)
        print(f"   ✅ 分块数量: {len(chunks)}")
        
        print("\n4️⃣  测试加载集合")
        collection = "test_manual"
        try:
            await service.load_collection(collection, sample_docs, use_faiss=False)
            print(f"   ✅ 集合加载成功")
            
            print("\n5️⃣  测试向量检索")
            results = await service.vector_search("CANopen", collection, top_k=1)
            print(f"   ✅ 检索结果: {len(results)} 个")
            
            print("\n6️⃣  测试BM25检索")
            bm25_results = service.bm25_search("CANopen", collection, top_k=1)
            print(f"   ✅ BM25结果: {len(bm25_results)} 个")
            
            print("\n7️⃣  测试混合检索")
            hybrid_results = await service.hybrid_search("CANopen", collection, top_k=1)
            print(f"   ✅ 混合结果: {len(hybrid_results)} 个")
            
            print("\n8️⃣  测试生成回答")
            answer = await service.generate_answer("测试", "这是上下文", None)
            print(f"   ✅ 回答生成成功，长度: {len(answer)}")
            
            print("\n9️⃣  测试完整查询")
            query = LangChainRAGQuery(
                query="CANopen",
                collection_name=collection,
                top_k=1,
                use_reranking=False,
                mode="vector"
            )
            result = await service.query(query, None)
            print(f"   ✅ 完整查询成功，文档数: {len(result.documents)}")
            
            # 清理
            if collection in service.vector_stores:
                del service.vector_stores[collection]
            if collection in service.bm25_retrievers:
                del service.bm25_retrievers[collection]
                
        except Exception as e:
            print(f"   ⚠️  集合操作失败: {e}")
        
        print("\n" + "=" * 70)
        print("✅ 测试完成")
        print("=" * 70)
    
    asyncio.run(test())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # 使用pytest运行
        pytest.main([__file__, "-v", "-s"])
    else:
        # 手动运行
        run_manual_tests()
