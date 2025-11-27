# 分段Markdown文件向量化处理功能

## 功能概述

本功能允许用户对已经分段好的markdown文件进行批量向量化处理，将文本内容转换为向量并存储到向量数据库中，用于RAG检索。

## 主要特性

### 1. 文件管理
- **自动扫描**: 自动扫描知识库中的分段文件
- **批量选择**: 支持全选/取消全选分段文件
- **文件预览**: 显示文件内容预览和大小信息
- **文件夹组织**: 按分段文件夹组织显示

### 2. 向量化配置
- **集合名称**: 自定义向量集合名称
- **文本分割器**: 支持多种分割策略
  - Markdown标题分割（推荐）
  - 字符分割
  - Token分割
- **块大小**: 可配置文本块大小（100-4000字符）
- **块重叠**: 可配置文本块重叠（0-1000字符）
- **覆盖选项**: 可选择是否覆盖已存在的集合

### 3. 实时进度跟踪
- **进度条**: 实时显示处理进度
- **状态更新**: 显示当前处理状态和消息
- **文件计数**: 显示已处理/总文件数
- **日志记录**: 详细的处理日志

### 4. 错误处理
- **文件验证**: 检查文件是否存在和可读
- **错误收集**: 收集并显示处理过程中的错误
- **异常处理**: 优雅处理各种异常情况

## 使用方法

### 1. 访问功能
1. 进入知识库管理界面
2. 选择RAG配置面板
3. 点击"分段向量化"标签页

### 2. 选择文件
1. 系统会自动扫描并显示所有分段文件
2. 使用复选框选择需要向量化的文件
3. 可以点击"全选"快速选择所有文件

### 3. 配置参数
1. **集合名称**: 输入向量集合的唯一名称
2. **文本分割器**: 选择适合的分割策略
3. **块大小**: 设置文本块大小（默认1000字符）
4. **块重叠**: 设置块重叠大小（默认200字符）
5. **覆盖选项**: 选择是否覆盖已存在的集合

### 4. 开始处理
1. 点击"开始向量化"按钮
2. 系统会显示实时进度和日志
3. 处理完成后显示结果统计

## API接口

### 1. 获取分段文件列表
```http
GET /api/v1/rag/segment-files?knowledge_id={knowledge_id}
```

### 2. 向量化分段文件
```http
POST /api/v1/rag/vectorize-segments
Content-Type: application/json

{
  "knowledge_id": "string",
  "segment_files": ["string"],
  "collection_name": "string",
  "overwrite": false,
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "text_splitter": "markdown_header"
}
```

### 3. 获取处理进度
```http
POST /api/v1/rag/vectorization-progress
Content-Type: application/json

{
  "knowledge_id": "string",
  "collection_name": "string"
}
```

## 技术实现

### 后端实现
- **文件处理**: 使用Python的os和pathlib模块处理文件路径
- **文本分割**: 集成LangChain的MarkdownHeaderTextSplitter
- **向量化**: 使用统一的EmbeddingService进行批量向量化
- **进度跟踪**: 使用全局字典跟踪处理进度
- **错误处理**: 完善的异常捕获和错误信息收集

### 前端实现
- **响应式设计**: 使用Svelte的响应式特性
- **实时更新**: 使用setInterval进行进度轮询
- **用户体验**: 提供直观的进度条和状态显示
- **错误提示**: 使用toast通知显示操作结果

### 数据结构
```typescript
interface SegmentFile {
  file_name: string;
  relative_path: string;
  full_path: string;
  content_preview: string;
  size: number;
  segment_folder: string;
}

interface VectorizationConfig {
  collection_name: string;
  overwrite: boolean;
  chunk_size: number;
  chunk_overlap: number;
  text_splitter: string;
}

interface ProcessingProgress {
  status: string;
  progress: number;
  current_file?: string;
  processed_files: number;
  total_files: number;
  message: string;
}
```

## 注意事项

1. **文件路径**: 确保分段文件存在于正确的路径结构中
2. **集合名称**: 集合名称必须唯一，避免冲突
3. **内存使用**: 大量文件处理时注意内存使用情况
4. **网络超时**: 处理大量文件时可能需要较长时间
5. **错误恢复**: 处理失败时检查文件格式和权限

## 故障排除

### 常见问题
1. **文件不存在**: 检查分段文件是否正确生成
2. **权限错误**: 确保有读取文件的权限
3. **集合冲突**: 使用不同的集合名称或启用覆盖选项
4. **内存不足**: 减少批量处理的文件数量

### 调试方法
1. 查看浏览器控制台的错误信息
2. 检查后端日志中的详细错误
3. 使用API接口直接测试功能
4. 检查文件路径和权限设置
