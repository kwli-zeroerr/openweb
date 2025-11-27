"""
加载maxkb导出的Excel分段文件并测试检索
格式：章节、分段内容、问题（选填，单元格内一行一个）
"""
import sys
from pathlib import Path

sys.path.insert(0, '/home/zeroerr-ai72/openwebui-zeroerr/backend')

import pandas as pd
from langchain_core.documents import Document
from open_webui.test.services.vllm_embeddings import VLLMEmbeddings


def load_excel_segments(file_path: Path):
    """加载Excel分段数据"""
    excel_file = pd.ExcelFile(file_path)
    
    all_docs = []
    
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        for idx, row in df.iterrows():
            # 提取分段内容
            content = None
            questions = None
            chapter = None
            
            # 查找内容列
            for col in df.columns:
                val = row[col]
                if pd.notna(val):
                    col_str = str(col)
                    val_str = str(val).strip()
                    
                    if '内容' in col_str and not content:
                        content = val_str
                    # 查找章节列
                    elif '章节' in col_str and not chapter:
                        chapter = val_str
                    # 查找问题列
                    elif '问题' in col_str and not questions:
                        questions = val_str
            
            # 创建Document
            if content:
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': file_path.name,
                        'sheet': sheet_name,
                        'row': idx,
                        'chapter': chapter or '',
                        'questions': questions or ''
                    }
                )
                all_docs.append(doc)
    
    return all_docs


def test_retrieval(docs, queries):
    """测试检索"""
    print(f"\n{'='*70}")
    print("🔍 测试检索")
    print(f"{'='*70}")
    
    # 向量化
    embeddings = VLLMEmbeddings()
    texts = [doc.page_content for doc in docs]
    
    print(f"\n📝 向量化 {len(texts)} 个文档...")
    vectors = embeddings.embed_documents(texts)
    
    # 存储向量
    vector_store = {i: {'doc': doc, 'vector': vec} for i, (doc, vec) in enumerate(zip(docs, vectors))}
    
    # 测试查询
    for query in queries:
        print(f"\n{'='*70}")
        print(f"查询: {query}")
        print(f"{'='*70}")
        
        # 向量化查询
        query_vec = embeddings.embed_query(query)
        
        # 计算相似度
        import numpy as np
        query_array = np.array(query_vec)
        
        results = []
        for idx, item in vector_store.items():
            doc_vec = np.array(item['vector'])
            similarity = np.dot(query_array, doc_vec) / (
                np.linalg.norm(query_array) * np.linalg.norm(doc_vec)
            )
            results.append((item['doc'], similarity))
        
        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 显示前5个结果
        print(f"\nTop 5 结果:")
        for i, (doc, score) in enumerate(results[:5], 1):
            print(f"\n{i}. [相似度: {score:.4f}]")
            print(f"   章节: {doc.metadata.get('chapter', 'N/A')}")
            print(f"   内容: {doc.page_content[:200]}...")
            if doc.metadata.get('questions'):
                print(f"   问题: {doc.metadata['questions']}")


def main():
    excel_file = Path("/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/manual/EtherCAT&CANopen通讯手册-20250919.xlsx")
    
    print("🚀 加载Excel分段文件")
    print("="*70)
    
    # 加载文档
    docs = load_excel_segments(excel_file)
    print(f"\n✅ 加载完成: {len(docs)} 个分段")
    
    # 显示前3个分段的元数据
    print("\n前3个分段:")
    for i, doc in enumerate(docs[:3], 1):
        print(f"{i}. {doc.page_content[:100]}...")
        print(f"   元数据: {doc.metadata}")
    
    # 测试查询
    test_queries = [
        "关节的重复定位精度是多少啊？"
    ]
    
    test_retrieval(docs, test_queries)
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    main()
