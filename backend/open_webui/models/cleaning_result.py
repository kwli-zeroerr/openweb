from sqlalchemy import Column, String, Integer, Text, ForeignKey
from open_webui.internal.db import Base
import uuid
import time

class CleaningResult(Base):
    """清洗结果表 - 记录清洗结果文件夹和源文件的对应关系"""
    __tablename__ = "cleaning_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_id = Column(String, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    
    # 源文件信息
    source_file_name = Column(String, nullable=False)  # 源文件名
    source_file_path = Column(String, nullable=False)  # 源文件路径
    source_file_size = Column(Integer)  # 源文件大小
    
    # 清洗结果信息
    result_folder_path = Column(String, nullable=False)  # 清洗结果文件夹路径
    markdown_file_path = Column(String)  # 生成的Markdown文件路径
    
    # 处理状态
    processing_status = Column(String, default="pending")  # pending/processing/completed/failed
    processing_started_at = Column(Integer)  # 开始处理时间
    processing_completed_at = Column(Integer)  # 完成处理时间
    error_message = Column(Text)  # 错误信息
    processing_log = Column(Text)  # 处理日志
    
    # 元数据
    extra_metadata = Column(Text)  # JSON格式的额外元数据
    
    # 时间戳
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    
    def __repr__(self):
        return f"<CleaningResult(id={self.id}, source_file={self.source_file_name}, status={self.processing_status})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "knowledge_id": self.knowledge_id,
            "user_id": self.user_id,
            "source_file_name": self.source_file_name,
            "source_file_path": self.source_file_path,
            "source_file_size": self.source_file_size,
            "result_folder_path": self.result_folder_path,
            "markdown_file_path": self.markdown_file_path,
            "processing_status": self.processing_status,
            "processing_started_at": self.processing_started_at,
            "processing_completed_at": self.processing_completed_at,
            "error_message": self.error_message,
            "processing_log": self.processing_log,
            "extra_metadata": self.extra_metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def create_from_processing(cls, knowledge_id: str, user_id: str, 
                              source_file_name: str, source_file_path: str,
                              source_file_size: int = None, 
                              result_folder_path: str = "mineru/"):
        """创建新的清洗结果记录"""
        return cls(
            knowledge_id=knowledge_id,
            user_id=user_id,
            source_file_name=source_file_name,
            source_file_path=source_file_path,
            source_file_size=source_file_size,
            result_folder_path=result_folder_path,
            processing_status="pending"
        )
    
    def mark_processing_started(self):
        """标记处理开始"""
        self.processing_status = "processing"
        self.processing_started_at = int(time.time())
        self.updated_at = int(time.time())
    
    def mark_completed(self, markdown_file_path: str = None, processing_log: str = None):
        """标记处理完成"""
        self.processing_status = "completed"
        self.processing_completed_at = int(time.time())
        self.updated_at = int(time.time())
        if markdown_file_path:
            self.markdown_file_path = markdown_file_path
        if processing_log:
            self.processing_log = processing_log
    
    def mark_failed(self, error_message: str, processing_log: str = None):
        """标记处理失败"""
        self.processing_status = "failed"
        self.processing_completed_at = int(time.time())
        self.updated_at = int(time.time())
        self.error_message = error_message
        if processing_log:
            self.processing_log = processing_log
