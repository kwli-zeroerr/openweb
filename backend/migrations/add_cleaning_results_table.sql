-- 添加清洗结果表
-- 用于记录清洗结果文件夹和源文件的对应关系

CREATE TABLE IF NOT EXISTS cleaning_results (
    id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    source_file_name TEXT NOT NULL,           -- 源文件名 (如: eCoder编码器用户手册V2.4.pdf)
    source_file_path TEXT NOT NULL,           -- 源文件路径
    source_file_size INTEGER,                -- 源文件大小
    result_folder_path TEXT NOT NULL,         -- 清洗结果文件夹路径 (如: mineru/)
    markdown_file_path TEXT,                  -- 生成的Markdown文件路径
    processing_status TEXT DEFAULT 'pending', -- 处理状态: pending/processing/completed/failed
    processing_started_at INTEGER,            -- 开始处理时间
    processing_completed_at INTEGER,          -- 完成处理时间
    error_message TEXT,                       -- 错误信息
    processing_log TEXT,                      -- 处理日志
    metadata JSON,                           -- 额外元数据
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cleaning_results_knowledge_id ON cleaning_results (knowledge_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_results_user_id ON cleaning_results (user_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_results_status ON cleaning_results (processing_status);
CREATE INDEX IF NOT EXISTS idx_cleaning_results_created_at ON cleaning_results (created_at);
CREATE INDEX IF NOT EXISTS idx_cleaning_results_source_file ON cleaning_results (source_file_name);

-- 添加注释
-- 这个表用于跟踪PDF清洗处理的结果，建立源文件和清洗结果之间的映射关系
