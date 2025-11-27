# 数据库表概览（按重要性排序）

## 🔴 核心业务表（最高优先级）

### 1. **user** - 用户表
**用途**: 存储所有用户信息，系统核心表
- **模型**: `backend/open_webui/models/users.py`
- **路由**: `backend/open_webui/routers/users.py`
- **主要字段**: id, name, email, username, role, api_key, oauth_sub, settings
- **关键功能**:
  - 用户认证和授权
  - 用户资料管理
  - API密钥管理
  - OAuth集成
- **关联**: 几乎所有表都通过 `user_id` 关联

### 2. **chat** - 聊天会话表
**用途**: 存储所有聊天会话，核心业务数据
- **模型**: `backend/open_webui/models/chats.py`
- **路由**: `backend/open_webui/routers/chats.py`
- **主要字段**: id, user_id, title, chat(JSON), meta(JSON), archived, pinned, folder_id
- **关键功能**:
  - 聊天会话管理（创建、删除、归档、置顶）
  - 聊天内容存储（JSON格式，包含消息历史）
  - 标签和文件夹关联
  - 分享功能（share_id）
- **关联**: tag, folder, user

### 3. **auth** - 认证表
**用途**: 存储用户认证信息（密码、OAuth等）
- **模型**: `backend/open_webui/models/auths.py`
- **路由**: `backend/open_webui/routers/auths.py`
- **主要字段**: id, user_id, provider, token, refresh_token
- **关键功能**:
  - 用户登录认证
  - OAuth认证管理
  - Token管理
- **关联**: user

---

## 🟠 重要功能表

### 4. **knowledge** - 知识库表
**用途**: 存储知识库配置和元数据
- **模型**: `backend/open_webui/models/knowledge.py`
- **路由**: `backend/open_webui/routers/knowledge.py`, `rag_api.py`
- **主要字段**: id, user_id, name, description, data(JSON), meta(JSON), access_control
- **关键功能**:
  - 知识库创建和管理
  - RAG检索配置
  - 访问控制
- **关联**: file, knowledge_log, user

### 5. **file** - 文件表
**用途**: 存储上传文件的元数据
- **模型**: `backend/open_webui/models/files.py`
- **路由**: `backend/open_webui/routers/files.py`
- **主要字段**: id, user_id, name, path, size, type, meta(JSON), access_control
- **关键功能**:
  - 文件上传和管理
  - 文件元数据存储
  - 文件访问控制
- **关联**: knowledge, user, folder

### 6. **message** - 消息表
**用途**: 存储独立的消息记录（可选功能）
- **模型**: `backend/open_webui/models/messages.py`
- **路由**: `backend/open_webui/routers/channels.py`
- **主要字段**: id, channel_id, user_id, content, role, data(JSON)
- **关键功能**:
  - 频道消息存储
  - 消息反应（reactions）
- **关联**: channel, user, message_reaction

### 7. **tag** - 标签表
**用途**: 存储聊天标签定义
- **模型**: `backend/open_webui/models/tags.py`
- **路由**: `backend/open_webui/routers/chats.py`
- **主要字段**: id, name, user_id, meta(JSON)
- **关键功能**:
  - 标签创建和管理
  - 聊天标签关联（存储在chat.meta.tags中）
  - 标签搜索和过滤
- **关联**: chat (通过JSON字段)

### 8. **folder** - 文件夹表
**用途**: 存储文件夹结构（用于组织聊天、文件等）
- **模型**: `backend/open_webui/models/folders.py`
- **路由**: `backend/open_webui/routers/folders.py`
- **主要字段**: id, user_id, name, folder_type, items(JSON), meta(JSON)
- **关键功能**:
  - 文件夹创建和管理
  - 聊天和文件组织
  - 文件夹层级结构
- **关联**: chat, file, knowledge

---

## 🟡 配置和工具表

### 9. **model** - 模型表
**用途**: 存储AI模型配置
- **模型**: `backend/open_webui/models/models.py`
- **路由**: `backend/open_webui/routers/models.py`, `ollama.py`, `openai.py`
- **主要字段**: id, user_id, name, model_id, base_model_id, access_control
- **关键功能**:
  - AI模型配置管理
  - 模型访问控制
  - 模型参数设置
- **关联**: user

### 10. **tool** - 工具表
**用途**: 存储自定义工具/函数定义
- **模型**: `backend/open_webui/models/tools.py`
- **路由**: `backend/open_webui/routers/tools.py`
- **主要字段**: id, user_id, name, description, parameters(JSON), access_control
- **关键功能**:
  - 工具定义和管理
  - 函数调用配置
  - 工具访问控制
- **关联**: user, group

### 11. **function** - 函数表
**用途**: 存储系统函数定义
- **模型**: `backend/open_webui/models/functions.py`
- **路由**: `backend/open_webui/routers/functions.py`
- **主要字段**: id, name, description, parameters(JSON), code
- **关键功能**:
  - 系统函数定义
  - 可执行代码存储
- **关联**: 独立表

### 12. **prompt** - 提示词表
**用途**: 存储提示词模板
- **模型**: `backend/open_webui/models/prompts.py`
- **路由**: `backend/open_webui/routers/prompts.py`
- **主要字段**: id, user_id, name, content, access_control
- **关键功能**:
  - 提示词模板管理
  - 提示词共享
- **关联**: user

### 13. **config** - 配置表
**用途**: 存储系统配置
- **模型**: 在多个文件中引用
- **路由**: `backend/open_webui/routers/configs.py`
- **主要字段**: id, key, value, data(JSON)
- **关键功能**:
  - 系统全局配置
  - 功能开关
- **关联**: 独立表

---

## 🟢 辅助功能表

### 14. **feedback** - 反馈表
**用途**: 存储用户反馈和评分
- **模型**: `backend/open_webui/models/feedbacks.py`
- **路由**: `backend/open_webui/routers/evaluations.py`, `model_scoring.py`
- **主要字段**: id, user_id, chat_id, rating, data(JSON), meta(JSON)
- **关键功能**:
  - 消息评分
  - 用户反馈收集
  - 模型评估
- **关联**: user, chat

### 15. **group** - 用户组表
**用途**: 存储用户组和权限配置
- **模型**: `backend/open_webui/models/groups.py`
- **路由**: `backend/open_webui/routers/groups.py`, `scim.py`
- **主要字段**: id, name, data(JSON), permissions(JSON), user_ids(JSON)
- **关键功能**:
  - 用户组管理
  - 权限配置
  - 访问控制
- **关联**: user

### 16. **channel** - 频道表
**用途**: 存储聊天频道（团队协作功能）
- **模型**: `backend/open_webui/models/channels.py`
- **路由**: `backend/open_webui/routers/channels.py`
- **主要字段**: id, name, description, data(JSON), access_control
- **关键功能**:
  - 频道创建和管理
  - 团队协作
  - 消息组织
- **关联**: message, channel_member, user

### 17. **note** - 笔记表
**用途**: 存储用户笔记
- **模型**: `backend/open_webui/models/notes.py`
- **路由**: `backend/open_webui/routers/notes.py`
- **主要字段**: id, user_id, title, content, data(JSON), access_control
- **关键功能**:
  - 笔记创建和管理
  - 笔记共享
- **关联**: user

### 18. **memory** - 记忆表
**用途**: 存储长期记忆（Agent功能）
- **模型**: `backend/open_webui/models/memories.py`
- **路由**: `backend/open_webui/routers/memories.py`
- **主要字段**: id, user_id, content, importance, embedding
- **关键功能**:
  - 长期记忆存储
  - Agent上下文记忆
- **关联**: user

### 19. **ticket** - 工单表
**用途**: 存储支持工单
- **模型**: `backend/open_webui/models/tickets.py`
- **路由**: `backend/open_webui/routers/tickets.py`
- **主要字段**: id, user_id, title, status, data(JSON), meta(JSON) (35个字段)
- **关键功能**:
  - 工单创建和管理
  - 工单状态跟踪
  - 支持系统
- **关联**: user, ticket_config

### 20. **ticket_config** - 工单配置表
**用途**: 存储工单系统配置
- **模型**: `backend/open_webui/models/ticket_config.py`
- **路由**: `backend/open_webui/routers/tickets.py`
- **主要字段**: id, config(JSON)
- **关键功能**:
  - 工单流程配置
  - 工单规则设置
- **关联**: ticket

---

## 🔵 关联和日志表

### 21. **knowledge_log** - 知识库日志表
**用途**: 记录知识库操作日志
- **模型**: `backend/open_webui/models/knowledge_logs.py`
- **路由**: `backend/open_webui/routers/knowledge.py`
- **主要字段**: id, knowledge_id, user_id, action, data(JSON), timestamp
- **关键功能**:
  - 知识库操作审计
  - 检索历史记录
- **关联**: knowledge, user

### 22. **message_reaction** - 消息反应表
**用途**: 存储消息的点赞/反应
- **模型**: `backend/open_webui/models/messages.py`
- **路由**: `backend/open_webui/routers/channels.py`
- **主要字段**: id, message_id, user_id, reaction_type
- **关键功能**:
  - 消息互动
  - 反应统计
- **关联**: message, user

### 23. **channel_member** - 频道成员表
**用途**: 存储频道成员关系
- **模型**: `backend/open_webui/models/channels.py`
- **路由**: `backend/open_webui/routers/channels.py`
- **主要字段**: id, channel_id, user_id, role
- **关键功能**:
  - 频道成员管理
  - 权限控制
- **关联**: channel, user

### 24. **chatidtag** - 聊天标签关联表（已废弃）
**用途**: 旧版标签关联表，已被chat.meta.tags替代
- **状态**: 已废弃，不再使用
- **替代**: chat表的meta JSON字段中的tags数组

### 25. **oauth_session** - OAuth会话表
**用途**: 存储OAuth会话信息
- **模型**: `backend/open_webui/models/oauth_sessions.py`
- **路由**: `backend/open_webui/routers/auths.py`, `tools.py`
- **主要字段**: id, user_id, provider, token, expires_at
- **关键功能**:
  - OAuth会话管理
  - Token刷新
- **关联**: user

### 26. **document** - 文档表（未使用）
**用途**: 预留表，当前未使用
- **状态**: 表存在但未在代码中使用

---

## ⚪ 系统表

### 27. **migratehistory** - 迁移历史表
**用途**: 记录数据库迁移历史（Peewee ORM）
- **状态**: 旧版ORM迁移记录，已切换到SQLAlchemy

### 28. **alembic_version** - Alembic版本表
**用途**: 记录Alembic数据库迁移版本
- **状态**: SQLAlchemy迁移系统使用
- **关键功能**: 数据库版本控制

---

## 📊 表关系总结

### 核心关系链：
1. **user** → **chat** → (tag, folder)
2. **user** → **knowledge** → **file** → **knowledge_log**
3. **user** → **group** → (权限控制)
4. **channel** → **message** → **message_reaction**
5. **user** → **auth** / **oauth_session**

### JSON字段存储关系：
- `chat.meta.tags` → tag表的id数组
- `chat.chat` → 完整的聊天消息历史（JSON）
- `folder.items` → 文件夹内容列表（JSON）
- `knowledge.data` → 知识库配置（JSON）

### 访问控制模式：
多个表使用 `access_control` JSON字段存储权限信息：
- knowledge, file, prompt, note, channel, tool

