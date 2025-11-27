# LangChain RAG 服务测试

这个目录包含对 `langchain_rag_service.py` 的测试代码。

## 测试文件

- `test_langchain_rag_service.py` - 主要测试文件

## 运行测试

### 方式1: 手动运行（推荐）

```bash
python test/services/test_langchain_rag_service.py
```

### 方式2: 使用pytest

```bash
# 安装pytest（如果还没安装）
pip install pytest pytest-asyncio

# 运行测试
pytest test/services/test_langchain_rag_service.py -v -s
```

## 测试内容

测试覆盖以下功能：

### 1. 基础功能测试
- ✅ 服务初始化
- ✅ 文本向量化 (`_embed_text`)
- ✅ Markdown分块 (`chunk_markdown`)
- ✅ 递归文本分块 (`chunk_text_recursive`)

### 2. 集合管理
- ✅ 加载集合 (`load_collection`)

### 3. 检索功能
- ✅ 向量检索 (`vector_search`)
- ✅ BM25检索 (`bm25_search`)
- ✅ 混合检索 (`hybrid_search`)

### 4. 重排序
- ✅ 文档重排序 (`rerank`)

### 5. LLM功能
- ✅ 获取LLM配置 (`get_llm`)
- ✅ 生成回答 (`generate_answer`)

### 6. 完整流程
- ✅ 完整RAG查询流程 (`query`)

## 测试输出示例

```
======================================================================
开始测试 LangChain RAG 服务
======================================================================

1️⃣  测试服务初始化
   ✅ 服务已初始化

2️⃣  测试文本向量化
   ✅ 向量维度: 384

3️⃣  测试Markdown分块
   ✅ 分块数量: 1

4️⃣  测试加载集合
   ✅ 集合加载成功

5️⃣  测试向量检索
   ✅ 检索结果: 1 个

6️⃣  测试BM25检索
   ✅ BM25结果: 1 个

7️⃣  测试混合检索
   ✅ 混合结果: 1 个

8️⃣  测试生成回答
   ✅ 回答生成成功，长度: 62

9️⃣  测试完整查询
   ✅ 完整查询成功，文档数: 1

======================================================================
✅ 测试完成
======================================================================
```

## 注意事项

1. 某些功能（如向量化、重排序）可能需要加载模型，如果模型未加载会跳过相关测试
2. 测试会自动清理临时创建的集合
3. 测试使用虚拟的文档数据，不会影响实际数据库

## 添加新测试

在 `test_langchain_rag_service.py` 中添加新的测试方法：

```python
@pytest.mark.asyncio
async def test_your_function(self, service):
    """测试你的功能"""
    # 测试代码
    result = await service.your_function()
    assert result is not None
```

## 故障排查

如果测试失败，检查：

1. **依赖包**: 确保安装了所有必需的Python包
2. **模型文件**: 某些功能需要下载的模型文件
3. **权限问题**: 确保有读取/写入权限
4. **路径问题**: 确保 `sys.path` 正确配置
