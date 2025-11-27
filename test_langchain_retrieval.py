#!/usr/bin/env python3
"""
使用LangChain进行简单的文档检索测试
直接从Chroma加载数据，然后用LangChain检索
"""
import asyncio
import sys
sys.path.insert(0, '/home/zeroerr-ai72/openwebui-zeroerr/backend')

from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.services.langchain_rag_service import langchain_rag_service
from langchain_core.documents import Document
import numpy as np
import asyncio

def cosine_similarity(a, b):
    """计算余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_documents_from_chroma(collection_name: str = "test3"):
    """从Chroma加载文档"""
    print(f"\n📂 从Chroma加载集合: {collection_name}")
    
    result = VECTOR_DB_CLIENT.get(collection_name)
    
    if not result or not result.documents or not result.documents[0]:
        print(f"⚠️  集合为空")
        return []
    
    documents = []
    for text, metadata in zip(result.documents[0], result.metadatas[0]):
        doc = Document(page_content=text, metadata=metadata)
        documents.append(doc)
    
    print(f"✅ 加载了 {len(documents)} 个文档")
    return documents

async def vector_search(query, documents, top_k=5):
    """向量检索"""
    print(f"\n🔵 向量检索:")
    
    # 向量化查询
    query_vector = await langchain_rag_service._embed_text(query)
    
    # 计算相似度
    scores = []
    for doc in documents:
        doc_vector = await langchain_rag_service._embed_text(doc.page_content)
        score = cosine_similarity(query_vector, doc_vector)
        scores.append(score)
    
    # 排序取top_k
    ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    
    for i, (doc, score) in enumerate(ranked[:top_k], 1):
        print(f"   {i}. [相似度: {score:.3f}] {doc.page_content[:80]}...")
    
    return [doc for doc, score in ranked[:top_k]]

def bm25_search(query, documents, top_k=5):
    """BM25全文检索"""
    print(f"\n🟢 BM25全文检索:")
    
    try:
        # 创建BM25检索器
        bm25 = BM25Retriever.from_documents(documents)
        bm25.k = top_k
        
        # 检索
        results = bm25.get_relevant_documents(query)
        
        for i, doc in enumerate(results, 1):
            print(f"   {i}. {doc.page_content[:80]}...")
        
        return results
    except Exception as e:
        print(f"   ⚠️  BM25检索失败: {e}")
        return []

async def test():
    print("=" * 70)
    print("LangChain检索测试")
    print("=" * 70)
    
    # 1. 加载文档到LangChain服务
    documents = load_documents_from_chroma("test3")
    
    if len(documents) < 5:
        print("❌ 文档太少，无法测试")
        return
    
    # 取前100个文档加快测试速度
    test_docs = documents[:100]
    print(f"📝 使用前 {len(test_docs)} 个文档进行测试")
    
    # 初始化LangChain服务
    await langchain_rag_service.load_collection("test3", test_docs, use_faiss=False)
    
    # 2. 测试查询
    from open_webui.services.langchain_rag_service import LangChainRAGQuery
    
    test_queries = [
        "重复定位精度",
        "CANopen报文",
        "关节型号"
    ]
    
    for query in test_queries:
        print("\n" + "=" * 70)
        print(f"📝 查询: {query}")
        print("=" * 70)
        
        # 使用LangChain完整查询
        rag_query = LangChainRAGQuery(
            query=query,
            collection_name="test3",
            top_k=3,
            mode="hybrid"
        )
        
        result = await langchain_rag_service.query(rag_query)
        
        print(f"\n✅ 方法: {result.method}")
        print(f"📄 找到 {len(result.documents)} 个文档")
        print(f"📝 回答: {result.answer[:100]}...")
        
        for i, doc in enumerate(result.documents, 1):
            print(f"\n  文档 {i}: {doc.page_content[:80]}...")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test())
