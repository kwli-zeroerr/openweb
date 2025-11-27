#!/usr/bin/env python3
"""
使用LangChain远程调用vLLM Embedding API
"""
try:
    from langchain.embeddings.base import Embeddings
except ImportError:
    # LangChain v0.2+ 使用新的导入路径
    from langchain_core.embeddings import Embeddings
from typing import List
import requests
import numpy as np


class VLLMEmbeddings(Embeddings):
    """自定义LangChain Embeddings包装器"""
    
    def __init__(self, api_url: str = "http://192.168.1.232:8010"):
        self.api_url = api_url
        self.base_url = f"{api_url}/v1/embeddings"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """为文档列表生成embeddings"""
        print(f"📝 正在为 {len(texts)} 个文档生成embeddings...")
        
        # 批量发送请求（可以分批处理大量文档）
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            try:
                response = requests.post(
                    self.base_url,
                    json={"input": batch},
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings = [item['embedding'] for item in result['data']]
                all_embeddings.extend(embeddings)
                
                print(f"   ✅ 已处理 {min(i+batch_size, len(texts))}/{len(texts)} 个文档")
            except Exception as e:
                print(f"   ❌ 批次 {i}-{i+batch_size} 失败: {e}")
                raise
        
        return all_embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """为单个查询生成embedding"""
        embeddings = self.embed_documents([text])
        return embeddings[0]
