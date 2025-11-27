# 知识库组件和框架清单

## 📚 概述

OpenWebUI 的知识库系统采用 **RAG（检索增强生成）** 架构，支持多种向量数据库、嵌入模型和文档加载器。

---

## 🏗️ 架构组件

### 1. 后端组件（Backend）

#### 1.1 核心路由（Routers）

| 组件 | 路径 | 功能 |
|------|------|------|
| **Knowledge Router** | `backend/open_webui/routers/knowledge.py` | 知识库管理 API（CRUD、文件上传、日志） |
| **Retrieval Router** | `backend/open_webui/routers/retrieval.py` | 检索 API（文档处理、向量化、查询） |
| **RAG API Router** | `backend/open_webui/routers/rag_api.py` | RAG 相关 API |
| **Agent Retrieval API** | `backend/open_webui/agent/retrieval_api.py` | Agent 模式下的检索 API |

#### 1.2 数据模型（Models）

| 模型 | 路径 | 说明 |
|------|------|------|
| **Knowledge** | `backend/open_webui/models/knowledge.py` | 知识库数据模型 |
| **KnowledgeLogs** | `backend/open_webui/models/knowledge_logs.py` | 知识库操作日志模型 |
| **File** | `backend/open_webui/models/files.py` | 文件元数据模型 |

#### 1.3 向量数据库（Vector Databases）

**支持的向量数据库：**

| 数据库 | 实现类 | 路径 | 特点 |
|--------|--------|------|------|
| **Chroma** | `ChromaClient` | `backend/open_webui/retrieval/vector/dbs/chroma.py` | 默认，轻量级 |
| **Qdrant** | `QdrantClient` | `backend/open_webui/retrieval/vector/dbs/qdrant.py` | 支持多租户模式 |
| **Milvus** | `MilvusClient` | `backend/open_webui/retrieval/vector/dbs/milvus.py` | 高性能 |
| **Pinecone** | `PineconeClient` | `backend/open_webui/retrieval/vector/dbs/pinecone.py` | 云服务 |
| **OpenSearch** | `OpenSearchClient` | `backend/open_webui/retrieval/vector/dbs/opensearch.py` | 企业级 |
| **Elasticsearch** | `ElasticsearchClient` | `backend/open_webui/retrieval/vector/dbs/elasticsearch.py` | 企业级 |
| **Pgvector** | `PgvectorClient` | `backend/open_webui/retrieval/vector/dbs/pgvector.py` | PostgreSQL 扩展 |
| **Oracle 23ai** | `Oracle23aiClient` | `backend/open_webui/retrieval/vector/dbs/oracle23ai.py` | Oracle 数据库 |
| **S3Vector** | `S3VectorClient` | `backend/open_webui/retrieval/vector/dbs/s3vector.py` | S3 存储 |

**工厂模式：**
- `backend/open_webui/retrieval/vector/factory.py` - 向量数据库工厂，根据配置选择数据库

#### 1.4 嵌入模型（Embedding Models）

**默认模型：**
- `sentence-transformers/all-MiniLM-L6-v2`（默认）

**支持的嵌入引擎：**

| 引擎 | 说明 | 配置 |
|------|------|------|
| **sentence-transformers** | 本地模型（默认） | `RAG_EMBEDDING_MODEL` |
| **vLLM/OpenAI 兼容** | 外部 API | `RAG_VLLM_EMBEDDING_URL` |
| **OpenAI** | OpenAI API | `OPENAI_API_KEY` |
| **自定义模型** | HuggingFace 模型 | 通过 `RAG_EMBEDDING_MODEL` 配置 |

**相关文件：**
- `backend/open_webui/services/embeddings_client.py` - vLLM/OpenAI 兼容的嵌入客户端
- `backend/open_webui/retrieval/utils.py` - 嵌入函数获取

#### 1.5 文档加载器（Document Loaders）

| 加载器 | 路径 | 支持格式 |
|--------|------|---------|
| **Main Loader** | `backend/open_webui/retrieval/loaders/main.py` | 统一入口 |
| **YouTube Loader** | `backend/open_webui/retrieval/loaders/youtube.py` | YouTube 视频 |
| **External Document** | `backend/open_webui/retrieval/loaders/external_document.py` | 外部文档 |
| **External Web** | `backend/open_webui/retrieval/loaders/external_web.py` | 网页内容 |
| **Tavily** | `backend/open_webui/retrieval/loaders/tavily.py` | Tavily 搜索 |
| **Mistral** | `backend/open_webui/retrieval/loaders/mistral.py` | Mistral 格式 |

**支持的文档格式：**
- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Excel (`.xlsx`, `.xls`)
- PowerPoint (`.pptx`)
- Markdown (`.md`)
- Text (`.txt`)
- HTML (`.html`)
- 图片 (`.jpg`, `.png`, 等，支持 OCR)

#### 1.6 文本分割器（Text Splitters）

**使用 LangChain：**
- `RecursiveCharacterTextSplitter` - 递归字符分割
- `TokenTextSplitter` - Token 分割
- `MarkdownHeaderTextSplitter` - Markdown 标题分割

#### 1.7 重排序模型（Reranking Models）

**支持的模型：**
- `cross-encoder/ms-marco-MiniLM-L-6-v2`（默认）
- 自定义模型（通过 `RAG_RERANKING_MODEL` 配置）

#### 1.8 Web 搜索引擎（Web Search Engines）

**支持的搜索引擎：**

| 引擎 | 实现 | 说明 |
|------|------|------|
| **DuckDuckGo** | `search_duckduckgo` | 免费，无需 API |
| **Brave** | `search_brave` | 需要 API Key |
| **Google PSE** | `search_google_pse` | Google 自定义搜索 |
| **Serper** | `search_serper` | Google 搜索 API |
| **SerpAPI** | `search_serpapi` | Google 搜索 API |
| **Tavily** | `search_tavily` | AI 搜索 |
| **Perplexity** | `search_perplexity` | AI 搜索 |
| **Bing** | `search_bing` | 微软搜索 |
| **Firecrawl** | `search_firecrawl` | 网页爬取 |
| **Exa** | `search_exa` | AI 搜索 |
| **Jina** | `search_jina` | 搜索 API |
| **Kagi** | `search_kagi` | 搜索 API |
| **SearXNG** | `search_searxng` | 开源搜索 |
| **Yacy** | `search_yacy` | 分布式搜索 |
| **Mojeek** | `search_mojeek` | 搜索 API |
| **Bocha** | `search_bocha` | 搜索 API |
| **Serply** | `search_serply` | Google 搜索 API |
| **Serpstack** | `search_serpstack` | Google 搜索 API |
| **Sougou** | `search_sougou` | 搜狗搜索 |
| **External** | `search_external` | 外部搜索 API |

**路径：** `backend/open_webui/retrieval/web/`

---

### 2. 前端组件（Frontend）

#### 2.1 知识库管理组件

| 组件 | 路径 | 功能 |
|------|------|------|
| **Knowledge** | `src/lib/components/workspace/Knowledge.svelte` | 知识库列表页面 |
| **KnowledgeBase** | `src/lib/components/workspace/Knowledge/KnowledgeBase.svelte` | 知识库详情页面 |
| **CreateKnowledgeBase** | `src/lib/components/workspace/Knowledge/CreateKnowledgeBase.svelte` | 创建知识库 |
| **KnowledgeHeader** | `src/lib/components/workspace/Knowledge/KnowledgeBase/KnowledgeHeader.svelte` | 知识库头部 |
| **KnowledgeLogs** | `src/lib/components/workspace/Knowledge/KnowledgeBase/KnowledgeLogs.svelte` | 操作日志 |
| **ItemMenu** | `src/lib/components/workspace/Knowledge/ItemMenu.svelte` | 知识库菜单 |

#### 2.2 聊天集成组件

| 组件 | 路径 | 功能 |
|------|------|------|
| **Knowledge (Command)** | `src/lib/components/chat/MessageInput/Commands/Knowledge.svelte` | 命令模式选择知识库 |
| **Knowledge (InputMenu)** | `src/lib/components/chat/MessageInput/InputMenu/Knowledge.svelte` | 输入菜单选择知识库 |
| **Knowledge (Models)** | `src/lib/components/workspace/Models/Knowledge.svelte` | 模型选择中的知识库 |

#### 2.3 RAG 工作流组件

| 组件 | 路径 | 功能 |
|------|------|------|
| **RAGWorkflowCanvas** | `src/lib/components/workspace/RAG/WorkflowCanvas/RAGWorkflowCanvas.svelte` | RAG 工作流画布（已删除） |

---

## 🔧 核心框架和库

### 后端框架

| 框架/库 | 版本 | 用途 |
|---------|------|------|
| **FastAPI** | 0.115.7 | Web 框架 |
| **LangChain** | 0.3.27 | RAG 框架 |
| **LangChain Community** | 0.3.29 | LangChain 扩展 |
| **sentence-transformers** | 5.1.1 | 嵌入模型 |
| **transformers** | latest | 模型加载 |
| **ChromaDB** | 1.0.20 | 向量数据库（默认） |
| **Qdrant Client** | 1.14.3 | Qdrant 客户端 |
| **Milvus** | 2.5.0 | Milvus 客户端 |
| **Pinecone** | 6.0.2 | Pinecone 客户端 |
| **OpenSearch** | 2.8.0 | OpenSearch 客户端 |
| **Elasticsearch** | 9.1.0 | Elasticsearch 客户端 |
| **Pgvector** | 0.4.1 | PostgreSQL 向量扩展 |
| **Oracle DB** | 3.2.0+ | Oracle 数据库 |
| **Unstructured** | 0.16.17 | 文档解析 |
| **pypdf** | 6.0.0 | PDF 处理 |
| **python-pptx** | 1.0.2 | PowerPoint 处理 |
| **openpyxl** | 3.1.5 | Excel 处理 |
| **docx2txt** | 0.8 | Word 处理 |
| **rank-bm25** | 0.2.2 | BM25 检索 |
| **colbert-ai** | 0.2.21 | ColBERT 检索 |

### 前端框架

| 框架/库 | 版本 | 用途 |
|---------|------|------|
| **Svelte** | latest | 前端框架 |
| **SvelteKit** | latest | 全栈框架 |
| **TypeScript** | latest | 类型系统 |
| **Tailwind CSS** | latest | 样式框架 |

---

## 📊 数据流程

```
用户上传文档
    ↓
文档加载器（Loader）
    ↓
文本分割（Text Splitter）
    ↓
嵌入模型（Embedding Model）
    ↓
向量化（Vectorization）
    ↓
存储到向量数据库（Vector DB）
    ↓
用户查询
    ↓
查询向量化
    ↓
向量相似度搜索
    ↓
重排序（Reranking）
    ↓
返回相关文档片段
    ↓
LLM 生成回答
```

---

## ⚙️ 配置项

### 向量数据库配置

```bash
VECTOR_DB=chroma  # 可选: chroma, qdrant, milvus, pinecone, opensearch, elasticsearch, pgvector, oracle23ai, s3vector
```

### 嵌入模型配置

```bash
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_EMBEDDING_ENGINE=  # 可选: vllm, openai
RAG_VLLM_EMBEDDING_URL=http://localhost:8010
```

### 重排序模型配置

```bash
RAG_RERANKING_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

---

## 🔗 相关工具集成

### RAGFlow 集成

- `backend/open_webui/services/ragflow_server.py` - RAGFlow 服务客户端
- `backend/open_webui/agent/rag_api.py` - RAGFlow API 路由
- `ragflow_retrieval_tool.py` - RAGFlow 检索工具

---

## 📝 总结

### 核心特点

1. **多向量数据库支持**：9 种向量数据库可选
2. **多嵌入模型支持**：本地模型、vLLM、OpenAI 兼容
3. **多文档格式支持**：PDF、Word、Excel、PPT、Markdown 等
4. **多搜索引擎支持**：20+ 种 Web 搜索引擎
5. **完整的 RAG 流程**：文档加载 → 分割 → 向量化 → 检索 → 重排序 → 生成

### 技术栈

- **后端**：FastAPI + LangChain + sentence-transformers
- **前端**：Svelte + TypeScript + Tailwind CSS
- **向量数据库**：Chroma（默认）+ 8 种可选
- **嵌入模型**：sentence-transformers（默认）+ 外部 API

---

## 📚 相关文档

- `backend/open_webui/agent/MEMORY_AND_RETRIEVAL_ANALYSIS.md` - 记忆与检索系统分析
- `backend/open_webui/agent/ARCHITECTURE.md` - Agent 架构文档

