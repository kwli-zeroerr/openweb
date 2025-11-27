import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Knowledge Logs DB Schema
####################

class KnowledgeLog(Base):
    __tablename__ = "knowledge_log"
    id = Column(String, primary_key=True)
    knowledge_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    
    action_type = Column(String, nullable=False)  # file_add, file_update, file_delete, knowledge_create, etc.
    action = Column(String, nullable=False)  # 操作描述
    description = Column(Text, nullable=True)  # 详细描述
    
    file_id = Column(String, nullable=True)  # 相关文件ID
    file_name = Column(String, nullable=True)  # 文件名
    file_size = Column(BigInteger, nullable=True)  # 文件大小
    
    extra_data = Column(JSON, nullable=True)  # 额外元数据
    status = Column(String, default="success")  # success, error, warning
    
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp


class KnowledgeLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    action_type: str
    action: str
    description: Optional[str] = None
    
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    
    extra_data: Optional[dict] = None
    status: str = "success"
    
    timestamp: int


####################
# Forms
####################

class KnowledgeLogForm(BaseModel):
    knowledge_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    action_type: str
    action: str
    description: Optional[str] = None
    
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    
    extra_data: Optional[dict] = None
    status: str = "success"


class KnowledgeLogsTable:
    def _ensure_table_exists(self, db):
        """确保 knowledge_log 表存在，如果不存在则创建"""
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if "knowledge_log" not in tables:
                log.info("knowledge_log table does not exist, creating it...")
                dialect = db.bind.dialect.name
                
                if dialect == "sqlite":
                    # SQLite 创建表语句（JSON 在 SQLite 中实际是 TEXT）
                    create_table_sql = """
                    CREATE TABLE knowledge_log (
                        id TEXT PRIMARY KEY,
                        knowledge_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        user_name TEXT,
                        user_email TEXT,
                        action_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        description TEXT,
                        file_id TEXT,
                        file_name TEXT,
                        file_size INTEGER,
                        extra_data TEXT,
                        status TEXT DEFAULT 'success',
                        timestamp INTEGER NOT NULL
                    )
                    """
                else:
                    # PostgreSQL 等其他数据库
                    create_table_sql = """
                    CREATE TABLE knowledge_log (
                        id VARCHAR PRIMARY KEY,
                        knowledge_id VARCHAR NOT NULL,
                        user_id VARCHAR NOT NULL,
                        user_name VARCHAR,
                        user_email VARCHAR,
                        action_type VARCHAR NOT NULL,
                        action VARCHAR NOT NULL,
                        description TEXT,
                        file_id VARCHAR,
                        file_name VARCHAR,
                        file_size BIGINT,
                        extra_data JSON,
                        status VARCHAR,
                        timestamp BIGINT NOT NULL
                    )
                    """
                
                db.execute(text(create_table_sql))
                db.commit()
                log.info("Successfully created knowledge_log table")
        except Exception as e:
            log.warning(f"Failed to ensure knowledge_log table exists: {e}")
            # 不抛出异常，让调用者处理

    def insert_log(self, form_data: KnowledgeLogForm) -> Optional[KnowledgeLogModel]:
        with get_db() as db:
            # 确保表存在
            self._ensure_table_exists(db)
            
            log_entry = KnowledgeLogModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "timestamp": int(time.time()),
                }
            )

            try:
                # 处理 extra_data 序列化（SQLite 需要）
                log_data = log_entry.model_dump()
                if log_data.get('extra_data') and db.bind.dialect.name == "sqlite":
                    import json
                    if isinstance(log_data['extra_data'], dict):
                        log_data['extra_data'] = json.dumps(log_data['extra_data'])
                
                result = KnowledgeLog(**log_data)
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    # 解析 extra_data（如果是字符串）
                    result_dict = {
                        'id': result.id,
                        'knowledge_id': result.knowledge_id,
                        'user_id': result.user_id,
                        'user_name': result.user_name,
                        'user_email': result.user_email,
                        'action_type': result.action_type,
                        'action': result.action,
                        'description': result.description,
                        'file_id': result.file_id,
                        'file_name': result.file_name,
                        'file_size': result.file_size,
                        'status': result.status or 'success',
                        'timestamp': result.timestamp,
                    }
                    # 处理 extra_data
                    extra_data = getattr(result, 'extra_data', None)
                    if isinstance(extra_data, str):
                        import json
                        try:
                            result_dict['extra_data'] = json.loads(extra_data)
                        except:
                            result_dict['extra_data'] = None
                    else:
                        result_dict['extra_data'] = extra_data
                    
                    return KnowledgeLogModel(**result_dict)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting knowledge log: {e}")
                # 如果插入失败，尝试再次确保表存在并重试一次
                try:
                    self._ensure_table_exists(db)
                    log_data = log_entry.model_dump()
                    if log_data.get('extra_data') and db.bind.dialect.name == "sqlite":
                        import json
                        if isinstance(log_data['extra_data'], dict):
                            log_data['extra_data'] = json.dumps(log_data['extra_data'])
                    
                    result = KnowledgeLog(**log_data)
                    db.add(result)
                    db.commit()
                    db.refresh(result)
                    if result:
                        # 解析 extra_data
                        result_dict = {
                            'id': result.id,
                            'knowledge_id': result.knowledge_id,
                            'user_id': result.user_id,
                            'user_name': result.user_name,
                            'user_email': result.user_email,
                            'action_type': result.action_type,
                            'action': result.action,
                            'description': result.description,
                            'file_id': result.file_id,
                            'file_name': result.file_name,
                            'file_size': result.file_size,
                            'status': result.status or 'success',
                            'timestamp': result.timestamp,
                        }
                        extra_data = getattr(result, 'extra_data', None)
                        if isinstance(extra_data, str):
                            import json
                            try:
                                result_dict['extra_data'] = json.loads(extra_data)
                            except:
                                result_dict['extra_data'] = None
                        else:
                            result_dict['extra_data'] = extra_data
                        return KnowledgeLogModel(**result_dict)
                except Exception as e2:
                    log.exception(f"Retry insert failed: {e2}")
                return None

    def get_logs_by_knowledge_id(self, knowledge_id: str, limit: int = 100) -> list[KnowledgeLogModel]:
        with get_db() as db:
            try:
                # 确保表存在
                self._ensure_table_exists(db)
                logs = db.query(KnowledgeLog).filter_by(knowledge_id=knowledge_id).order_by(KnowledgeLog.timestamp.desc()).limit(limit).all()
                
                # 处理 extra_data 字段（SQLite 中可能是字符串）
                result = []
                import json
                for log_entry in logs:
                    log_dict = {
                        'id': log_entry.id,
                        'knowledge_id': log_entry.knowledge_id,
                        'user_id': log_entry.user_id,
                        'user_name': log_entry.user_name,
                        'user_email': log_entry.user_email,
                        'action_type': log_entry.action_type,
                        'action': log_entry.action,
                        'description': log_entry.description,
                        'file_id': log_entry.file_id,
                        'file_name': log_entry.file_name,
                        'file_size': log_entry.file_size,
                        'status': log_entry.status or 'success',
                        'timestamp': log_entry.timestamp,
                    }
                    extra_data = getattr(log_entry, 'extra_data', None)
                    if isinstance(extra_data, str):
                        try:
                            log_dict['extra_data'] = json.loads(extra_data)
                        except:
                            log_dict['extra_data'] = None
                    else:
                        log_dict['extra_data'] = extra_data
                    result.append(KnowledgeLogModel(**log_dict))
                return result
            except Exception as e:
                log.exception(f"Error getting knowledge logs: {e}")
                return []

    def get_logs_by_user_id(self, user_id: str, limit: int = 100) -> list[KnowledgeLogModel]:
        with get_db() as db:
            try:
                # 确保表存在
                self._ensure_table_exists(db)
                logs = db.query(KnowledgeLog).filter_by(user_id=user_id).order_by(KnowledgeLog.timestamp.desc()).limit(limit).all()
                
                # 处理 extra_data 字段（SQLite 中可能是字符串）
                result = []
                import json
                for log_entry in logs:
                    log_dict = {
                        'id': log_entry.id,
                        'knowledge_id': log_entry.knowledge_id,
                        'user_id': log_entry.user_id,
                        'user_name': log_entry.user_name,
                        'user_email': log_entry.user_email,
                        'action_type': log_entry.action_type,
                        'action': log_entry.action,
                        'description': log_entry.description,
                        'file_id': log_entry.file_id,
                        'file_name': log_entry.file_name,
                        'file_size': log_entry.file_size,
                        'status': log_entry.status or 'success',
                        'timestamp': log_entry.timestamp,
                    }
                    extra_data = getattr(log_entry, 'extra_data', None)
                    if isinstance(extra_data, str):
                        try:
                            log_dict['extra_data'] = json.loads(extra_data)
                        except:
                            log_dict['extra_data'] = None
                    else:
                        log_dict['extra_data'] = extra_data
                    result.append(KnowledgeLogModel(**log_dict))
                return result
            except Exception as e:
                log.exception(f"Error getting user logs: {e}")
                return []

    def delete_logs_by_knowledge_id(self, knowledge_id: str) -> bool:
        with get_db() as db:
            try:
                # 确保表存在
                self._ensure_table_exists(db)
                db.query(KnowledgeLog).filter_by(knowledge_id=knowledge_id).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting knowledge logs: {e}")
                return False

    def delete_all_logs(self) -> bool:
        with get_db() as db:
            try:
                # 确保表存在
                self._ensure_table_exists(db)
                db.query(KnowledgeLog).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting all logs: {e}")
                return False


KnowledgeLogs = KnowledgeLogsTable()
