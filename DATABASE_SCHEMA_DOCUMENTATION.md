# OpenWebUI-ZeroErr 数据库表结构文档

## 数据库概览
- **数据库文件**: `./backend/data/webui.db`
- **数据库类型**: SQLite3
- **总表数**: 27个表（24个业务表 + 3个系统表）

## 核心业务表

### 1. 用户表 (user)
```sql
CREATE TABLE IF NOT EXISTS "user" (
    "id" VARCHAR(255) NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "role" VARCHAR(255) NOT NULL,
    "profile_image_url" TEXT NOT NULL,
    "api_key" VARCHAR(255),
    "created_at" INTEGER NOT NULL,
    "updated_at" INTEGER NOT NULL,
    "last_active_at" INTEGER NOT NULL,
    "settings" TEXT,
    "info" TEXT,
    "oauth_sub" TEXT,
    "username" VARCHAR(50),
    "bio" TEXT,
    "gender" TEXT,
    "date_of_birth" DATE
);
```

**字段说明**:
- `id`: 用户唯一标识符 (主键)
- `name`: 用户姓名
- `email`: 用户邮箱
- `role`: 用户角色 (admin/user等)
- `profile_image_url`: 头像URL
- `api_key`: API密钥
- `created_at`: 创建时间 (Unix时间戳)
- `updated_at`: 更新时间 (Unix时间戳)
- `last_active_at`: 最后活跃时间 (Unix时间戳)
- `settings`: 用户设置 (JSON)
- `info`: 用户信息 (JSON)
- `oauth_sub`: OAuth订阅ID
- `username`: 用户名
- `bio`: 个人简介
- `gender`: 性别
- `date_of_birth`: 出生日期

**索引**:
- `user_api_key`: API密钥唯一索引
- `user_id`: 用户ID唯一索引
- `user_oauth_sub`: OAuth订阅ID唯一索引

### 2. 聊天表 (chat)
```sql
CREATE TABLE IF NOT EXISTS "chat" (
    "id" VARCHAR(255) NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL,
    "title" TEXT NOT NULL,
    "share_id" VARCHAR(255),
    "archived" INTEGER NOT NULL,
    "created_at" DATETIME NOT NULL,
    "updated_at" DATETIME NOT NULL,
    "chat" JSON,
    "pinned" BOOLEAN,
    "meta" JSON DEFAULT '{}' NOT NULL,
    "folder_id" TEXT
);
```

**字段说明**:
- `id`: 聊天唯一标识符 (主键)
- `user_id`: 用户ID (外键)
- `title`: 聊天标题
- `share_id`: 分享ID
- `archived`: 是否归档 (0/1)
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `chat`: 聊天内容 (JSON格式)
- `pinned`: 是否置顶
- `meta`: 元数据 (JSON)
- `folder_id`: 文件夹ID

**索引**:
- `chat_id`: 聊天ID唯一索引
- `chat_share_id`: 分享ID唯一索引
- `folder_id_idx`: 文件夹ID索引
- `user_id_pinned_idx`: 用户ID和置顶状态复合索引
- `user_id_archived_idx`: 用户ID和归档状态复合索引
- `updated_at_user_id_idx`: 更新时间和用户ID复合索引
- `folder_id_user_id_idx`: 文件夹ID和用户ID复合索引

### 3. 工单表 (ticket)
```sql
CREATE TABLE ticket (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    category TEXT DEFAULT 'bug',
    attachments TEXT,
    tags TEXT,
    comments TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    user_name TEXT,
    user_email TEXT,
    assigned_to TEXT,
    assigned_to_name TEXT,
    resolved_at INTEGER,
    is_ai_generated BOOLEAN DEFAULT 0,
    source_feedback_id TEXT,
    ai_analysis TEXT,
    task_requirements TEXT,
    completion_criteria TEXT,
    task_deadline TEXT,
    task_priority TEXT,
    required_files TEXT,
    required_text TEXT,
    required_images TEXT,
    delivery_instructions TEXT,
    delivery_files TEXT,
    delivery_text TEXT,
    delivery_images TEXT,
    completion_status TEXT,
    completion_notes TEXT,
    verification_score INTEGER,
    verification_checklist TEXT
);
```

**字段说明**:
- `id`: 工单唯一标识符 (主键)
- `user_id`: 创建用户ID
- `title`: 工单标题
- `description`: 工单描述
- `status`: 工单状态 (open/in_progress/resolved/closed)
- `priority`: 优先级 (low/medium/high/urgent)
- `category`: 分类 (bug/feature/improvement等)
- `attachments`: 附件信息 (JSON)
- `tags`: 标签 (JSON)
- `comments`: 评论 (JSON)
- `created_at`: 创建时间 (Unix时间戳)
- `updated_at`: 更新时间 (Unix时间戳)
- `user_name`: 用户姓名
- `user_email`: 用户邮箱
- `assigned_to`: 分配给的用户ID
- `assigned_to_name`: 分配给的用户姓名
- `resolved_at`: 解决时间 (Unix时间戳)
- `is_ai_generated`: 是否AI生成 (0/1)
- `source_feedback_id`: 来源反馈ID
- `ai_analysis`: AI分析结果 (JSON)
- `task_requirements`: 任务需求
- `completion_criteria`: 完成标准
- `task_deadline`: 任务截止时间
- `task_priority`: 任务优先级
- `required_files`: 必需文件
- `required_text`: 必需文本
- `required_images`: 必需图片
- `delivery_instructions`: 交付说明
- `delivery_files`: 交付文件
- `delivery_text`: 交付文本
- `delivery_images`: 交付图片
- `completion_status`: 完成状态
- `completion_notes`: 完成备注
- `verification_score`: 验证分数
- `verification_checklist`: 验证清单

**索引**:
- `idx_ticket_user_id`: 用户ID索引
- `idx_ticket_status`: 状态索引
- `idx_ticket_created_at`: 创建时间索引

## 辅助表

### 4. 聊天标签关联表 (chatidtag)
```sql
CREATE TABLE IF NOT EXISTS "chatidtag" (
    "id" VARCHAR(255) NOT NULL,
    "tag_name" VARCHAR(255) NOT NULL,
    "chat_id" VARCHAR(255) NOT NULL,
    "user_id" VARCHAR(255) NOT NULL,
    "timestamp" INTEGER NOT NULL,
    PRIMARY KEY (id)
);
```

**字段说明**:
- `id`: 关联唯一标识符 (主键)
- `tag_name`: 标签名称
- `chat_id`: 聊天ID
- `user_id`: 用户ID
- `timestamp`: 创建时间戳 (Unix时间戳)

**索引**:
- `chatidtag_id`: 关联ID唯一索引

### 5. 工单配置表 (ticket_config)
```sql
CREATE TABLE ticket_config (
    id VARCHAR NOT NULL PRIMARY KEY,
    enabled BOOLEAN,
    model_id VARCHAR NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at VARCHAR,
    updated_at VARCHAR
);
```

### 6. 反馈表 (feedback)
```sql
CREATE TABLE feedback (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    version BIGINT,
    type TEXT,
    data JSON,
    meta JSON,
    snapshot JSON,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    chat_id TEXT,
    PRIMARY KEY (id)
);
```

**字段说明**:
- `id`: 反馈唯一标识符 (主键)
- `user_id`: 用户ID
- `version`: 版本号
- `type`: 反馈类型
- `data`: 反馈数据 (JSON)
- `meta`: 元数据 (JSON)
- `snapshot`: 快照数据 (JSON)
- `created_at`: 创建时间 (Unix时间戳)
- `updated_at`: 更新时间 (Unix时间戳)
- `chat_id`: 关联的聊天ID

**索引**:
- `sqlite_autoindex_feedback_1`: 主键自动索引

### 7. 认证表 (auth)
```sql
CREATE TABLE IF NOT EXISTS "auth" (
    "id" VARCHAR(255) NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL,
    "password" TEXT NOT NULL,
    "active" INTEGER NOT NULL
);
```

### 8. 模型表 (model)
```sql
CREATE TABLE IF NOT EXISTS "model" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "base_model_id" TEXT,
    "name" TEXT NOT NULL,
    "meta" TEXT NOT NULL,
    "params" TEXT NOT NULL,
    "created_at" INTEGER NOT NULL,
    "updated_at" INTEGER NOT NULL,
    "access_control" JSON,
    "is_active" BOOLEAN DEFAULT (1) NOT NULL
);
```

### 9. 工具表 (tool)
```sql
CREATE TABLE IF NOT EXISTS "tool" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "specs" TEXT NOT NULL,
    "meta" TEXT NOT NULL,
    "created_at" INTEGER NOT NULL,
    "updated_at" INTEGER NOT NULL,
    "valves" TEXT,
    "access_control" JSON,
    "is_default_for_all_users" INTEGER DEFAULT 0
);
```

**字段说明**:
- `id`: 工具唯一标识符 (主键)
- `user_id`: 用户ID
- `name`: 工具名称
- `content`: 工具代码内容
- `specs`: 工具规格 (JSON)
- `meta`: 元数据 (JSON)
- `created_at`: 创建时间 (Unix时间戳)
- `updated_at`: 更新时间 (Unix时间戳)
- `valves`: 阀门配置 (JSON)
- `access_control`: 访问控制 (JSON)
- `is_default_for_all_users`: 是否为所有用户的默认工具 (0/1)

**索引**:
- `tool_id`: 工具ID唯一索引

### 10. 知识库表 (knowledge)
```sql
CREATE TABLE knowledge (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    data JSON,
    meta JSON,
    created_at BIGINT NOT NULL,
    updated_at BIGINT,
    access_control JSON
);
```

**字段说明**:
- `id`: 知识库唯一标识符 (主键)
- `user_id`: 用户ID
- `name`: 知识库名称
- `description`: 知识库描述
- `data`: 数据 (JSON)
- `meta`: 元数据 (JSON)
- `created_at`: 创建时间 (Unix时间戳)
- `updated_at`: 更新时间 (Unix时间戳)
- `access_control`: 访问控制 (JSON)

### 11. 文件表 (file)
```sql
CREATE TABLE IF NOT EXISTS "file" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "meta" JSON,
    "created_at" INTEGER NOT NULL,
    "hash" TEXT,
    "data" JSON,
    "updated_at" BIGINT,
    "path" TEXT,
    "access_control" JSON
);
```

### 12. 标签表 (tag)
```sql
CREATE TABLE IF NOT EXISTS "tag" (
    "id" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "user_id" VARCHAR(255) NOT NULL,
    "meta" JSON,
    CONSTRAINT pk_id_user_id PRIMARY KEY (id, user_id)
);
```

### 13. 文件夹表 (folder)
```sql
CREATE TABLE IF NOT EXISTS "folder" (
    "id" TEXT NOT NULL,
    "parent_id" TEXT,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "items" JSON,
    "meta" JSON,
    "is_expanded" BOOLEAN NOT NULL,
    "created_at" BIGINT NOT NULL,
    "updated_at" BIGINT NOT NULL,
    "data" JSON,
    PRIMARY KEY (id, user_id)
);
```

### 14. 群组表 (group)
```sql
CREATE TABLE IF NOT EXISTS "group" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT,
    "name" TEXT,
    "description" TEXT,
    "data" JSON,
    "meta" JSON,
    "permissions" JSON,
    "user_ids" JSON,
    "created_at" BIGINT,
    "updated_at" BIGINT,
    UNIQUE (id)
);
```

### 15. 频道表 (channel)
```sql
CREATE TABLE channel (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    data JSON,
    meta JSON,
    access_control JSON,
    created_at BIGINT,
    updated_at BIGINT,
    type TEXT,
    UNIQUE (id)
);
```

### 16. 消息表 (message)
```sql
CREATE TABLE message (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    channel_id TEXT,
    content TEXT,
    data JSON,
    meta JSON,
    created_at BIGINT,
    updated_at BIGINT,
    parent_id TEXT,
    UNIQUE (id)
);
```

### 17. 消息反应表 (message_reaction)
```sql
CREATE TABLE message_reaction (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at BIGINT,
    PRIMARY KEY (id),
    UNIQUE (id)
);
```

### 18. 频道成员表 (channel_member)
```sql
CREATE TABLE channel_member (
    id TEXT NOT NULL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at BIGINT,
    PRIMARY KEY (id),
    UNIQUE (id)
);
```

### 19. 笔记表 (note)
```sql
CREATE TABLE note (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    data JSON,
    meta JSON,
    access_control JSON,
    created_at BIGINT,
    updated_at BIGINT,
    PRIMARY KEY (id),
    UNIQUE (id)
);
```

### 20. 提示词表 (prompt)
```sql
CREATE TABLE IF NOT EXISTS "prompt" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "command" VARCHAR(255) NOT NULL,
    "user_id" VARCHAR(255) NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "timestamp" INTEGER NOT NULL,
    "access_control" JSON
);
```

### 21. 文档表 (document)
```sql
CREATE TABLE IF NOT EXISTS "document" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "collection_name" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "title" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "content" TEXT,
    "user_id" VARCHAR(255) NOT NULL,
    "timestamp" INTEGER NOT NULL
);
```

### 22. 记忆表 (memory)
```sql
CREATE TABLE IF NOT EXISTS "memory" (
    "id" VARCHAR(255) NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    "updated_at" INTEGER NOT NULL,
    "created_at" INTEGER NOT NULL
);
```

### 23. 函数表 (function)
```sql
CREATE TABLE IF NOT EXISTS "function" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "meta" TEXT NOT NULL,
    "created_at" INTEGER NOT NULL,
    "updated_at" INTEGER NOT NULL,
    "valves" TEXT,
    "is_active" INTEGER NOT NULL,
    "is_global" INTEGER NOT NULL
);
```

### 24. OAuth会话表 (oauth_session)
```sql
CREATE TABLE oauth_session (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    token TEXT NOT NULL,
    expires_at BIGINT NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
```

## 系统表

### 25. 配置表 (config)
```sql
CREATE TABLE config (
    id INTEGER NOT NULL PRIMARY KEY,
    data JSON NOT NULL,
    version INTEGER NOT NULL,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);
```

### 26. 迁移历史表 (migratehistory)
```sql
CREATE TABLE IF NOT EXISTS "migratehistory" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "migrated_at" DATETIME NOT NULL
);
```

### 27. Alembic版本表 (alembic_version)
```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
```

## 数据关系

### 主要外键关系
1. **用户相关**:
   - `chat.user_id` → `user.id`
   - `ticket.user_id` → `user.id`
   - `feedback.user_id` → `user.id`
   - `chatidtag.user_id` → `user.id`
   - `oauth_session.user_id` → `user.id`

2. **聊天标签相关**:
   - `chatidtag.chat_id` → `chat.id`
   - `chatidtag.user_id` → `user.id`

3. **OAuth相关**:
   - `oauth_session.user_id` → `user.id` (CASCADE DELETE)

## 索引优化

### 性能关键索引
1. **时间相关索引**:
   - `chat.updated_at_user_id_idx`: 聊天更新时间
   - `ticket.created_at`: 工单创建时间
   - `oauth_session.expires_at`: OAuth会话过期时间

2. **用户相关索引**:
   - `chat.user_id_archived_idx`: 用户聊天归档状态
   - `ticket.user_id`: 用户工单
   - `oauth_session.user_id`: OAuth会话用户ID
   - `tag.user_id_idx`: 标签用户ID

3. **状态相关索引**:
   - `ticket.status`: 工单状态
   - `chat.archived`: 聊天归档状态

4. **OAuth相关索引**:
   - `oauth_session.user_id`: OAuth会话用户ID
   - `oauth_session.expires_at`: OAuth会话过期时间
   - `oauth_session.user_provider`: 用户ID和提供商复合索引

5. **函数相关索引**:
   - `function.is_global_idx`: 全局函数索引

## 数据类型说明

- **TEXT**: 可变长度字符串
- **VARCHAR(n)**: 固定长度字符串
- **INTEGER**: 整数
- **BIGINT**: 大整数
- **BOOLEAN**: 布尔值 (0/1)
- **JSON**: JSON格式数据
- **DATETIME**: 日期时间
- **DATE**: 日期

## 时间戳格式

- **Unix时间戳**: `created_at`, `updated_at`, `last_active_at` 等字段使用Unix时间戳 (秒)
- **DATETIME**: `chat.created_at`, `chat.updated_at`, `config.created_at` 等字段使用DATETIME格式

---

**文档生成时间**: 2025-01-10
**数据库版本**: SQLite3
**总表数**: 27个表（24个业务表 + 3个系统表）

## 表清单

### 业务表（24个）
1. user - 用户表
2. chat - 聊天表
3. chatidtag - 聊天标签关联表
4. ticket - 工单表
5. ticket_config - 工单配置表
6. feedback - 反馈表
7. auth - 认证表
8. model - 模型表
9. tool - 工具表
10. knowledge - 知识库表
11. file - 文件表
12. tag - 标签表
13. folder - 文件夹表
14. group - 群组表
15. channel - 频道表
16. channel_member - 频道成员表
17. message - 消息表
18. message_reaction - 消息反应表
19. note - 笔记表
20. prompt - 提示词表
21. document - 文档表
22. memory - 记忆表
23. function - 函数表
24. oauth_session - OAuth会话表

### 系统表（3个）
25. config - 配置表
26. migratehistory - 迁移历史表
27. alembic_version - Alembic版本表
