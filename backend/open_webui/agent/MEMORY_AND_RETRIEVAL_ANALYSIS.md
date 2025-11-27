# OpenWebUI 记忆与检索系统分析

## 📋 目录
1. [记忆系统架构](#记忆系统架构)
2. [聊天对话中的记忆处理](#聊天对话中的记忆处理)
3. [检索系统中的记忆使用](#检索系统中的记忆使用)
4. [数据库使用方式](#数据库使用方式)
5. [工作流程](#工作流程)
6. [总结](#总结)

---

## 记忆系统架构

### 双存储架构

OpenWebUI 采用 **双存储架构** 实现记忆系统：

```
┌─────────────────────────────────────────┐
│  1. SQL 数据库 (关系型数据库)            │
│     - 存储原始记忆内容                   │
│     - 表结构: memory                    │
│       • id (String, PK)                 │
│       • user_id (String)                │
│       • content (Text)                  │
│       • created_at (BigInteger)        │
│       • updated_at (BigInteger)         │
└──────────────┬──────────────────────────┘
               │
               │ 同步写入
               │
┌──────────────▼──────────────────────────┐
│  2. 向量数据库 (Vector DB)               │
│     - 存储嵌入向量（用于语义检索）        │
│     - Collection: user-memory-{user_id} │
│     - 存储结构:                          │
│       • id: 记忆ID                      │
│       • text: 记忆内容                   │
│       • vector: 嵌入向量                 │
│       • metadata: {created_at, ...}      │
└─────────────────────────────────────────┘
```

### 数据库类型支持

**向量数据库**支持多种后端：
- ✅ **Chroma** (默认)
- ✅ **Qdrant** (支持多租户模式)
- ✅ **Milvus**
- ✅ **Pinecone**
- ✅ **S3Vector**
- ✅ **OpenSearch**
- ✅ **PgVector** (PostgreSQL 扩展)
- ✅ **Elasticsearch**
- ✅ **Oracle23AI**

通过 `VECTOR_DB` 环境变量配置，统一接口：`VECTOR_DB_CLIENT`

---

## 聊天对话中的记忆处理

### 记忆检索流程

**位置**: `backend/open_webui/utils/middleware.py` → `chat_memory_handler()`

**触发条件**:
- 用户请求中 `features.memory = true`
- 在 `process_chat_payload()` 中自动调用

**处理流程**:
```python
async def chat_memory_handler(request, form_data, extra_params, user):
    # 1. 获取用户最后一条消息
    user_message = get_last_user_message(form_data["messages"])
    
    # 2. 调用记忆检索 API
    results = await query_memory(
        request,
        QueryMemoryForm(content=user_message, k=3),
        user
    )
    
    # 3. 格式化记忆上下文
    user_context = ""
    for doc_idx, doc in enumerate(results.documents[0]):
        date = format_date(results.metadatas[0][doc_idx]["created_at"])
        user_context += f"{doc_idx + 1}. [{date}] {doc}\n"
    
    # 4. 注入到系统消息
    form_data["messages"] = add_or_update_system_message(
        f"User Context:\n{user_context}\n",
        form_data["messages"],
        append=True
    )
    
    return form_data
```

### 记忆保存流程

**位置**: `backend/open_webui/routers/memories.py` → `add_memory()`

**保存流程**:
```python
async def add_memory(request, form_data, user):
    # 1. 保存到 SQL 数据库
    memory = Memories.insert_new_memory(
        user_id=user.id,
        content=form_data.content
    )
    
    # 2. 生成嵌入向量
    embedding = request.app.state.EMBEDDING_FUNCTION(
        memory.content, 
        user=user
    )
    
    # 3. 保存到向量数据库
    VECTOR_DB_CLIENT.upsert(
        collection_name=f"user-memory-{user.id}",
        items=[{
            "id": memory.id,
            "text": memory.content,
            "vector": embedding,
            "metadata": {"created_at": memory.created_at}
        }]
    )
    
    return memory
```

### 聊天流程中的记忆位置

**处理顺序** (在 `process_chat_payload()` 中):
```
1. Pipeline Inlet (管道入口)
2. Filter Inlet (过滤器入口)
3. Chat Memory ← 记忆检索和注入
4. Chat Web Search
5. Chat Image Generation
6. Chat Code Interpreter
7. Chat Tools Function Calling
8. Chat Files
```

**记忆注入时机**:
- ✅ **检索阶段**: 在 LLM 调用前，自动检索并注入相关记忆
- ✅ **注入位置**: 系统消息 (`system` role)
- ✅ **格式**: `User Context:\n1. [日期] 记忆内容\n...`

---

## 检索系统中的记忆使用

### 知识库检索

**位置**: `backend/open_webui/routers/retrieval.py`

**检索流程**:
```python
# 1. 向量检索（从向量数据库）
results = VECTOR_DB_CLIENT.search(
    collection_name=knowledge_base_id,
    vectors=[query_embedding],
    limit=top_k
)

# 2. 格式化检索结果
context_string = ""
for doc in results.documents:
    context_string += f'<source id="...">{doc}</source>\n'

# 3. 注入到用户消息（使用 RAG 模板）
form_data["messages"] = add_or_update_user_message(
    rag_template(
        RAG_TEMPLATE,
        context_string,
        user_prompt
    ),
    form_data["messages"]
)
```

### 记忆检索 vs 知识库检索

| 特性 | 记忆检索 | 知识库检索 |
|------|---------|-----------|
| **数据来源** | 用户记忆 (`user-memory-{id}`) | 知识库 (`knowledge-{id}`) |
| **注入位置** | 系统消息 (`system`) | 用户消息 (`user`) |
| **格式** | `User Context:\n1. [日期] 内容\n...` | `<source id="...">内容</source>\n...` |
| **用途** | 提供用户历史上下文 | 提供知识库文档 |
| **检索时机** | 聊天前（如果启用） | 工具调用或 RAG 流程 |

### 检索上下文组装

**RAG 模板格式** (`RAG_TEMPLATE`):
```python
# 默认模板
"{context}\n\n{question}"

# 实际使用
rag_template(
    template="{context}\n\n{question}",
    context_string=context_string,  # 检索到的文档
    prompt=user_prompt               # 用户问题
)
```

**结果格式**:
```xml
<source id="1" name="文档名">文档内容...</source>
<source id="2" name="文档名">文档内容...</source>

用户问题
```

---

## 数据库使用方式

### SQL 数据库 (关系型)

**表结构**: `memory`

```sql
CREATE TABLE memory (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    content TEXT,
    created_at BIGINT,
    updated_at BIGINT
);
```

**操作**:
- ✅ `insert_new_memory()` - 插入新记忆
- ✅ `get_memories_by_user_id()` - 获取用户所有记忆
- ✅ `update_memory_by_id_and_user_id()` - 更新记忆
- ✅ `delete_memory_by_id_and_user_id()` - 删除记忆

**使用场景**:
- 存储原始记忆内容
- 管理记忆生命周期
- 提供结构化查询

### 向量数据库 (Vector DB)

**Collection 命名规则**:
- 用户记忆: `user-memory-{user_id}`
- 知识库: `{knowledge_base_id}`
- 文件: `file-{file_id}`

**操作接口** (统一通过 `VECTOR_DB_CLIENT`):
```python
# 插入/更新
VECTOR_DB_CLIENT.upsert(
    collection_name="user-memory-{user_id}",
    items=[{
        "id": "memory_id",
        "text": "记忆内容",
        "vector": [0.1, 0.2, ...],  # 嵌入向量
        "metadata": {"created_at": 1234567890}
    }]
)

# 检索
results = VECTOR_DB_CLIENT.search(
    collection_name="user-memory-{user_id}",
    vectors=[query_embedding],  # 查询向量
    limit=3  # top-k
)

# 删除
VECTOR_DB_CLIENT.delete(
    collection_name="user-memory-{user_id}",
    ids=["memory_id"]
)
```

**使用场景**:
- 语义检索（相似度搜索）
- 快速查找相关记忆
- 支持大规模向量存储

### 嵌入函数 (Embedding Function)

**位置**: `request.app.state.EMBEDDING_FUNCTION`

**功能**:
- 将文本转换为向量
- 支持用户上下文（`user` 参数）
- 统一接口，支持多种嵌入模型

**使用示例**:
```python
# 生成嵌入向量
embedding = request.app.state.EMBEDDING_FUNCTION(
    text="记忆内容",
    user=user  # 可选，用于多租户
)

# 向量维度取决于嵌入模型（通常 1536 或 384）
```

---

## 工作流程

### 完整聊天流程（带记忆）

```
用户发送消息
    ↓
process_chat_payload()
    ↓
┌─────────────────────────────────────┐
│ chat_memory_handler()               │
│ 1. 提取用户消息                     │
│ 2. 向量化查询                       │
│ 3. 从向量DB检索记忆                 │
│ 4. 格式化记忆上下文                 │
│ 5. 注入到系统消息                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ chat_completion_tools_handler()     │
│ 1. 工具调用（如果需要）             │
│ 2. 知识库检索（如果需要）           │
│ 3. 组装检索上下文                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ LLM 调用                            │
│ 输入:                               │
│ - System: User Context (记忆)       │
│ - User: RAG Context + Question      │
└─────────────────────────────────────┘
    ↓
返回响应
    ↓
(可选) 保存新记忆到 SQL + Vector DB
```

### 记忆检索流程

```
用户查询 → 向量化
    ↓
VECTOR_DB_CLIENT.search(
    collection="user-memory-{user_id}",
    vectors=[query_vector],
    limit=3
)
    ↓
返回结果 (documents, metadatas, ids)
    ↓
格式化:
1. [2025-11-05] 记忆内容1
2. [2025-11-04] 记忆内容2
3. [2025-11-03] 记忆内容3
    ↓
注入到系统消息
```

### 记忆保存流程

```
用户操作 / LLM 输出
    ↓
Memories.insert_new_memory(user_id, content)
    ↓
SQL 数据库: 保存原始内容
    ↓
生成嵌入向量: EMBEDDING_FUNCTION(content)
    ↓
VECTOR_DB_CLIENT.upsert(
    collection="user-memory-{user_id}",
    items=[{id, text, vector, metadata}]
)
    ↓
向量数据库: 保存向量和元数据
```

---

## 总结

### 记忆系统特点

1. **双存储架构**:
   - SQL 数据库：存储原始内容，支持结构化查询
   - 向量数据库：存储嵌入向量，支持语义检索

2. **自动检索和注入**:
   - 聊天前自动检索相关记忆
   - 注入到系统消息，提供上下文

3. **统一接口**:
   - `VECTOR_DB_CLIENT` 统一向量数据库操作
   - 支持多种向量数据库后端

### 检索系统特点

1. **分离的检索流程**:
   - 记忆检索：用户历史上下文
   - 知识库检索：外部文档知识

2. **不同的注入方式**:
   - 记忆：系统消息 (`system`)
   - 知识库：用户消息 (`user`) + RAG 模板

3. **灵活的检索方式**:
   - 向量检索（语义相似度）
   - 元数据过滤（结构化查询）

### 数据库使用方式总结

| 数据库类型 | 用途 | 存储内容 | 查询方式 |
|-----------|------|---------|---------|
| **SQL DB** | 记忆原始内容 | id, user_id, content, timestamps | SQL 查询 |
| **Vector DB** | 语义检索 | id, text, vector, metadata | 向量相似度搜索 |

### Agent 模块的缺失

❌ **Agent 模块目前没有集成记忆系统**:
- 没有 `MemoryRetrievalNode` 节点
- 没有 `MemorySaveNode` 节点
- 无法在工作流中使用用户记忆

**建议**:
1. 实现 `MemoryRetrievalNode` 和 `MemorySaveNode`
2. 在工作流中支持记忆检索和保存
3. 实现完整的"记忆 → 检索 → LLM → 保存记忆"闭环

---

**创建时间**: 2025-11-05

