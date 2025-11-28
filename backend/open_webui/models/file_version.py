import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# FileVersion DB Schema
####################


class FileVersion(Base):
    __tablename__ = "file_version"
    
    id = Column(String, primary_key=True)
    file_id = Column(String, nullable=False)  # 关联 file.id (1:N)
    version_number = Column(Integer, nullable=False)  # 版本号，从 1 开始递增
    
    status = Column(Text, nullable=True)  # 版本状态：'indexed', 'indexing', 'failed', 等
    meta = Column(Text, nullable=True)  # 版本元数据（JSON 字符串，可选）
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class FileVersionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    file_id: str
    version_number: int
    
    status: Optional[str] = None
    meta: Optional[str] = None
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class FileVersionForm(BaseModel):
    file_id: str
    version_number: Optional[int] = None  # 如果不提供，自动递增
    status: Optional[str] = None
    meta: Optional[str] = None


class FileVersionTable:
    def create_version(
        self, file_id: str, status: Optional[str] = None, meta: Optional[str] = None
    ) -> Optional[FileVersionModel]:
        """创建文件新版本，自动递增版本号"""
        with get_db() as db:
            try:
                # 获取当前最大版本号
                existing_versions = (
                    db.query(FileVersion)
                    .filter_by(file_id=file_id)
                    .order_by(FileVersion.version_number.desc())
                    .all()
                )
                
                next_version = 1
                if existing_versions:
                    next_version = existing_versions[0].version_number + 1
                
                version = FileVersion(
                    id=str(uuid.uuid4()),
                    file_id=file_id,
                    version_number=next_version,
                    status=status,
                    meta=meta,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
                
                db.add(version)
                db.commit()
                db.refresh(version)
                
                return FileVersionModel.model_validate(version)
            except Exception as e:
                log.exception(f"Error creating file version: {e}")
                db.rollback()
                return None

    def get_versions_by_file_id(self, file_id: str) -> list[FileVersionModel]:
        """获取文件的所有版本，按版本号降序排列"""
        with get_db() as db:
            try:
                versions = (
                    db.query(FileVersion)
                    .filter_by(file_id=file_id)
                    .order_by(FileVersion.version_number.desc())
                    .all()
                )
                return [FileVersionModel.model_validate(v) for v in versions]
            except Exception as e:
                log.exception(f"Error getting file versions: {e}")
                return []

    def get_version_by_id(self, version_id: str) -> Optional[FileVersionModel]:
        """根据版本 ID 获取版本信息"""
        with get_db() as db:
            try:
                version = db.query(FileVersion).filter_by(id=version_id).first()
                return FileVersionModel.model_validate(version) if version else None
            except Exception as e:
                log.exception(f"Error getting file version by id: {e}")
                return None

    def get_latest_version(self, file_id: str) -> Optional[FileVersionModel]:
        """获取文件的最新版本"""
        with get_db() as db:
            try:
                version = (
                    db.query(FileVersion)
                    .filter_by(file_id=file_id)
                    .order_by(FileVersion.version_number.desc())
                    .first()
                )
                return FileVersionModel.model_validate(version) if version else None
            except Exception as e:
                log.exception(f"Error getting latest file version: {e}")
                return None

    def update_version_status(
        self, version_id: str, status: str, meta: Optional[str] = None
    ) -> Optional[FileVersionModel]:
        """更新版本状态（例如：索引完成、索引失败等）"""
        with get_db() as db:
            try:
                version = db.query(FileVersion).filter_by(id=version_id).first()
                if not version:
                    return None
                
                version.status = status
                if meta is not None:
                    version.meta = meta
                version.updated_at = int(time.time())
                
                db.commit()
                db.refresh(version)
                
                return FileVersionModel.model_validate(version)
            except Exception as e:
                log.exception(f"Error updating file version status: {e}")
                db.rollback()
                return None

    def delete_version_by_id(self, version_id: str) -> bool:
        """删除指定版本"""
        with get_db() as db:
            try:
                db.query(FileVersion).filter_by(id=version_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting file version: {e}")
                db.rollback()
                return False

    def delete_versions_by_file_id(self, file_id: str) -> bool:
        """删除文件的所有版本"""
        with get_db() as db:
            try:
                db.query(FileVersion).filter_by(file_id=file_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting file versions: {e}")
                db.rollback()
                return False


FileVersions = FileVersionTable()

