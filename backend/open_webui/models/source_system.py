import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# SourceSystem DB Schema
####################


class SourceSystem(Base):
    __tablename__ = "source_system"
    
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)  # 外部系统名称
    api_key_hash = Column(Text, nullable=False)  # API 密钥的哈希值（用于鉴权和溯源）
    
    meta = Column(Text, nullable=True)  # 其他元数据（JSON 字符串，可选）
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class SourceSystemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    api_key_hash: str
    
    meta: Optional[str] = None
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class SourceSystemForm(BaseModel):
    name: str
    api_key_hash: str
    meta: Optional[str] = None


class SourceSystemTable:
    def create_source_system(
        self, name: str, api_key_hash: str, meta: Optional[str] = None
    ) -> Optional[SourceSystemModel]:
        """创建新的外部系统记录"""
        with get_db() as db:
            try:
                source_system = SourceSystem(
                    id=str(uuid.uuid4()),
                    name=name,
                    api_key_hash=api_key_hash,
                    meta=meta,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
                
                db.add(source_system)
                db.commit()
                db.refresh(source_system)
                
                return SourceSystemModel.model_validate(source_system)
            except Exception as e:
                log.exception(f"Error creating source system: {e}")
                db.rollback()
                return None

    def get_source_system_by_id(self, system_id: str) -> Optional[SourceSystemModel]:
        """根据 ID 获取外部系统信息"""
        with get_db() as db:
            try:
                source_system = (
                    db.query(SourceSystem).filter_by(id=system_id).first()
                )
                return (
                    SourceSystemModel.model_validate(source_system)
                    if source_system
                    else None
                )
            except Exception as e:
                log.exception(f"Error getting source system by id: {e}")
                return None

    def get_source_system_by_api_key_hash(
        self, api_key_hash: str
    ) -> Optional[SourceSystemModel]:
        """根据 API 密钥哈希获取外部系统信息（用于鉴权）"""
        with get_db() as db:
            try:
                source_system = (
                    db.query(SourceSystem).filter_by(api_key_hash=api_key_hash).first()
                )
                return (
                    SourceSystemModel.model_validate(source_system)
                    if source_system
                    else None
                )
            except Exception as e:
                log.exception(f"Error getting source system by api_key_hash: {e}")
                return None

    def get_all_source_systems(self) -> list[SourceSystemModel]:
        """获取所有外部系统"""
        with get_db() as db:
            try:
                source_systems = (
                    db.query(SourceSystem)
                    .order_by(SourceSystem.created_at.desc())
                    .all()
                )
                return [
                    SourceSystemModel.model_validate(s) for s in source_systems
                ]
            except Exception as e:
                log.exception(f"Error getting all source systems: {e}")
                return []

    def update_source_system(
        self,
        system_id: str,
        name: Optional[str] = None,
        api_key_hash: Optional[str] = None,
        meta: Optional[str] = None,
    ) -> Optional[SourceSystemModel]:
        """更新外部系统信息"""
        with get_db() as db:
            try:
                source_system = (
                    db.query(SourceSystem).filter_by(id=system_id).first()
                )
                
                if not source_system:
                    return None
                
                if name is not None:
                    source_system.name = name
                if api_key_hash is not None:
                    source_system.api_key_hash = api_key_hash
                if meta is not None:
                    source_system.meta = meta
                
                source_system.updated_at = int(time.time())
                
                db.commit()
                db.refresh(source_system)
                
                return SourceSystemModel.model_validate(source_system)
            except Exception as e:
                log.exception(f"Error updating source system: {e}")
                db.rollback()
                return None

    def delete_source_system(self, system_id: str) -> bool:
        """删除外部系统"""
        with get_db() as db:
            try:
                db.query(SourceSystem).filter_by(id=system_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting source system: {e}")
                db.rollback()
                return False


SourceSystems = SourceSystemTable()

