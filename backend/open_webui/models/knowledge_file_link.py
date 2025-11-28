import logging
import time
from typing import Optional
from sqlalchemy import PrimaryKeyConstraint

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Boolean, String

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# KnowledgeFileLink DB Schema (N:M 关联表)
####################


class KnowledgeFileLink(Base):
    __tablename__ = "knowledge_file_link"
    
    knowledge_id = Column(String, nullable=False)
    file_id = Column(String, nullable=False)
    
    is_indexed = Column(Boolean, default=False, nullable=False)  # 标记文件是否已成功索引到该知识库
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    
    # 复合主键：knowledge_id + file_id
    __table_args__ = (
        PrimaryKeyConstraint("knowledge_id", "file_id", name="pk_knowledge_file"),
    )


class KnowledgeFileLinkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    knowledge_id: str
    file_id: str
    is_indexed: bool
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class KnowledgeFileLinkForm(BaseModel):
    knowledge_id: str
    file_id: str
    is_indexed: Optional[bool] = False


class KnowledgeFileLinkTable:
    def create_link(
        self, knowledge_id: str, file_id: str, is_indexed: bool = False
    ) -> Optional[KnowledgeFileLinkModel]:
        """创建知识库与文件的关联"""
        with get_db() as db:
            try:
                # 检查是否已存在
                existing = (
                    db.query(KnowledgeFileLink)
                    .filter_by(knowledge_id=knowledge_id, file_id=file_id)
                    .first()
                )
                
                if existing:
                    # 如果已存在，更新 is_indexed 状态
                    existing.is_indexed = is_indexed
                    existing.updated_at = int(time.time())
                    db.commit()
                    db.refresh(existing)
                    return KnowledgeFileLinkModel.model_validate(existing)
                
                # 创建新关联
                link = KnowledgeFileLink(
                    knowledge_id=knowledge_id,
                    file_id=file_id,
                    is_indexed=is_indexed,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
                
                db.add(link)
                db.commit()
                db.refresh(link)
                
                return KnowledgeFileLinkModel.model_validate(link)
            except Exception as e:
                log.exception(f"Error creating knowledge-file link: {e}")
                db.rollback()
                return None

    def get_link(
        self, knowledge_id: str, file_id: str
    ) -> Optional[KnowledgeFileLinkModel]:
        """获取知识库与文件的关联"""
        with get_db() as db:
            try:
                link = (
                    db.query(KnowledgeFileLink)
                    .filter_by(knowledge_id=knowledge_id, file_id=file_id)
                    .first()
                )
                return KnowledgeFileLinkModel.model_validate(link) if link else None
            except Exception as e:
                log.exception(f"Error getting knowledge-file link: {e}")
                return None

    def get_files_by_knowledge_id(
        self, knowledge_id: str, only_indexed: bool = False
    ) -> list[KnowledgeFileLinkModel]:
        """获取知识库关联的所有文件"""
        with get_db() as db:
            try:
                query = db.query(KnowledgeFileLink).filter_by(knowledge_id=knowledge_id)
                
                if only_indexed:
                    query = query.filter_by(is_indexed=True)
                
                links = query.order_by(KnowledgeFileLink.created_at.desc()).all()
                return [KnowledgeFileLinkModel.model_validate(link) for link in links]
            except Exception as e:
                log.exception(f"Error getting files by knowledge_id: {e}")
                return []

    def get_knowledges_by_file_id(self, file_id: str) -> list[KnowledgeFileLinkModel]:
        """获取文件关联的所有知识库"""
        with get_db() as db:
            try:
                links = (
                    db.query(KnowledgeFileLink)
                    .filter_by(file_id=file_id)
                    .order_by(KnowledgeFileLink.created_at.desc())
                    .all()
                )
                return [KnowledgeFileLinkModel.model_validate(link) for link in links]
            except Exception as e:
                log.exception(f"Error getting knowledges by file_id: {e}")
                return []

    def update_indexed_status(
        self, knowledge_id: str, file_id: str, is_indexed: bool
    ) -> Optional[KnowledgeFileLinkModel]:
        """更新文件的索引状态"""
        with get_db() as db:
            try:
                link = (
                    db.query(KnowledgeFileLink)
                    .filter_by(knowledge_id=knowledge_id, file_id=file_id)
                    .first()
                )
                
                if not link:
                    return None
                
                link.is_indexed = is_indexed
                link.updated_at = int(time.time())
                
                db.commit()
                db.refresh(link)
                
                return KnowledgeFileLinkModel.model_validate(link)
            except Exception as e:
                log.exception(f"Error updating indexed status: {e}")
                db.rollback()
                return None

    def delete_link(self, knowledge_id: str, file_id: str) -> bool:
        """删除知识库与文件的关联"""
        with get_db() as db:
            try:
                db.query(KnowledgeFileLink).filter_by(
                    knowledge_id=knowledge_id, file_id=file_id
                ).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting knowledge-file link: {e}")
                db.rollback()
                return False

    def delete_links_by_knowledge_id(self, knowledge_id: str) -> bool:
        """删除知识库的所有文件关联"""
        with get_db() as db:
            try:
                db.query(KnowledgeFileLink).filter_by(knowledge_id=knowledge_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting links by knowledge_id: {e}")
                db.rollback()
                return False

    def delete_links_by_file_id(self, file_id: str) -> bool:
        """删除文件的所有知识库关联"""
        with get_db() as db:
            try:
                db.query(KnowledgeFileLink).filter_by(file_id=file_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting links by file_id: {e}")
                db.rollback()
                return False

    def count_files_by_knowledge_id(
        self, knowledge_id: str, only_indexed: bool = False
    ) -> int:
        """统计知识库关联的文件数量"""
        with get_db() as db:
            try:
                query = db.query(KnowledgeFileLink).filter_by(knowledge_id=knowledge_id)
                
                if only_indexed:
                    query = query.filter_by(is_indexed=True)
                
                return query.count()
            except Exception as e:
                log.exception(f"Error counting files by knowledge_id: {e}")
                return 0


KnowledgeFileLinks = KnowledgeFileLinkTable()

