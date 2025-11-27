"""
使用vLLM向量模型的RAG测试
使用远程192.168.1.232:8010的vLLM Embedding服务
"""
import sys
import asyncio
from pathlib import Path
from typing import List

# 添加backend目录到Python路径
from pathlib import Path as PathType
backend_dir = PathType(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from langchain_core.documents import Document
from open_webui.test.services.vllm_embeddings import VLLMEmbeddings


class VLLMRAGTester:
    """使用vLLM的RAG测试器"""
    
    def __init__(self):
        self.embeddings = VLLMEmbeddings(api_url="http://192.168.1.232:8010")
        self.mineru_dir = Path("/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/mineru")
        self.test_file = self.mineru_dir / "eRob_CANopen_and_EtherCAT用户手册v1.9" / "eRob_CANopen_and_EtherCAT用户手册v1.9.md"
        self.vector_store = {}  # 简单的内存向量存储
    
    def load_markdown_file(self) -> Path:
        """加载测试markdown文件"""
        if not self.test_file.exists():
            print(f"⚠️  测试文件不存在: {self.test_file}")
            return None
        
        print(f"\n📂 加载测试文件: {self.test_file.name}")
        print(f"   文件大小: {self.test_file.stat().st_size / 1024:.2f} KB")
        return self.test_file
    
    def chunk_markdown(self, content: str) -> List[Document]:
        """分段markdown文件"""
        from langchain.text_splitter import MarkdownHeaderTextSplitter
        
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        
        chunks = markdown_splitter.split_text(content)
        print(f"✅ Markdown分段完成: {len(chunks)} 个")
        return chunks
    
    def load_and_chunk_file(self, file_path: Path) -> List[Document]:
        """加载并分段文件"""
        print(f"\n📝 开始加载和分段...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = self.chunk_markdown(content)
            
            # 添加文件来源信息
            for chunk in chunks:
                if chunk.metadata is None:
                    chunk.metadata = {}
                chunk.metadata['source'] = file_path.name
            
            return chunks
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return []
    
    async def vectorize_and_store(self, chunks: List[Document]):
        """向量化并存储"""
        if len(chunks) == 0:
            print("⚠️  没有文档可以向量化")
            return
        
        print(f"\n🔢 向量化 {len(chunks)} 个文档...")
        
        # 提取文本内容
        texts = [chunk.page_content for chunk in chunks]
        
        # 向量化（使用vLLM API）
        try:
            vectors = self.embeddings.embed_documents(texts)
            print(f"✅ 向量化完成: {len(vectors)} 个向量")
            
            # 存储到内存
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                self.vector_store[i] = {
                    'doc': chunk,
                    'vector': vector
                }
            
            print(f"✅ 已存储 {len(self.vector_store)} 个向量")
        except Exception as e:
            print(f"❌ 向量化失败: {e}")
    
    async def vector_search(self, query: str, top_k: int = 5):
        """向量检索"""
        if len(self.vector_store) == 0:
            print("⚠️  向量存储为空")
            return []
        
        print(f"\n🔍 向量检索: '{query}'")
        
        try:
            # 向量化查询
            query_vector = self.embeddings.embed_query(query)
            print(f"✅ 查询向量维度: {len(query_vector)}")
            
            # 计算相似度
            import numpy as np
            query_array = np.array(query_vector)
            
            results = []
            for idx, item in self.vector_store.items():
                doc_vector = np.array(item['vector'])
                similarity = np.dot(query_array, doc_vector) / (
                    np.linalg.norm(query_array) * np.linalg.norm(doc_vector)
                )
                results.append((item['doc'], similarity))
            
            # 排序
            results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"✅ 检索完成: 找到 {len(results)} 个结果")
            return results[:top_k]
            
        except Exception as e:
            print(f"❌ 检索失败: {e}")
            return []
    
    async def test_retrieval(self):
        """测试检索"""
        print(f"\n{'='*70}")
        print("🔍 测试检索")
        print(f"{'='*70}")
        
        test_queries = [
            "CANopen报文",
            "重复定位精度",
            "关节型号查询",
        ]
        
        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"查询: {query}")
            print(f"{'='*70}")
            
            results = await self.vector_search(query, top_k=5)
            
            for i, (doc, score) in enumerate(results, 1):
                print(f"\n{i}. [相似度: {score:.4f}]")
                print(f"   📄 {doc.page_content[:150]}...")
                print(f"   📁 来源: {doc.metadata.get('source', 'N/A')}")
    
    async def run_full_pipeline(self):
        """运行完整的RAG管道"""
        print("="*70)
        print("🚀 使用vLLM的RAG测试")
        print("="*70)
        
        # 1. 加载文件
        md_file = self.load_markdown_file()
        if md_file is None:
            return
        
        # 2. 分段
        chunks = self.load_and_chunk_file(md_file)
        if len(chunks) == 0:
            return
        
        # 3. 向量化
        await self.vectorize_and_store(chunks)
        
        # 4. 测试检索
        await self.test_retrieval()
        
        print("\n" + "="*70)
        print("✅ 测试完成")
        print("="*70)


async def main():
    tester = VLLMRAGTester()
    await tester.run_full_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
