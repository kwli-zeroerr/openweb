import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from open_webui.models.analytics import Analytics, AnalyticsEventType

log = logging.getLogger(__name__)


class AnalyticsService:
    """分析服务 - 用于记录用户活动事件"""
    
    @staticmethod
    def log_chat_message(user_id: str, chat_id: str, message_id: str, content: str, session_id: Optional[str] = None):
        """记录聊天消息事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.CHAT_MESSAGE,
                event_data={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "content_length": len(content) if content else 0,
                    "has_content": bool(content)
                },
                session_id=session_id
            )
            log.debug(f"Logged chat message event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log chat message event: {e}")
    
    @staticmethod
    def log_user_login(user_id: str, session_id: Optional[str] = None):
        """记录用户登录事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.USER_LOGIN,
                event_data={
                    "login_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged user login event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log user login event: {e}")
    
    @staticmethod
    def log_user_logout(user_id: str, session_id: Optional[str] = None):
        """记录用户登出事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.USER_LOGOUT,
                event_data={
                    "logout_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged user logout event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log user logout event: {e}")
    
    @staticmethod
    def log_thumbs_up(user_id: str, chat_id: str, message_id: str, session_id: Optional[str] = None):
        """记录点赞事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.CHAT_THUMBS_UP,
                event_data={
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                session_id=session_id
            )
            log.debug(f"Logged thumbs up event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log thumbs up event: {e}")
    
    @staticmethod
    def log_thumbs_down(user_id: str, chat_id: str, message_id: str, session_id: Optional[str] = None):
        """记录点踩事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.CHAT_THUMBS_DOWN,
                event_data={
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                session_id=session_id
            )
            log.debug(f"Logged thumbs down event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log thumbs down event: {e}")
    
    @staticmethod
    def log_model_usage(user_id: str, model_id: str, session_id: Optional[str] = None):
        """记录模型使用事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.MODEL_USAGE,
                event_data={
                    "model_id": model_id,
                    "usage_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged model usage event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log model usage event: {e}")
    
    @staticmethod
    def log_knowledge_access(user_id: str, knowledge_id: str, session_id: Optional[str] = None):
        """记录知识库访问事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.KNOWLEDGE_ACCESS,
                event_data={
                    "knowledge_id": knowledge_id,
                    "access_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged knowledge access event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log knowledge access event: {e}")
    
    @staticmethod
    def log_tool_usage(user_id: str, tool_id: str, session_id: Optional[str] = None):
        """记录工具使用事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.TOOL_USAGE,
                event_data={
                    "tool_id": tool_id,
                    "usage_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged tool usage event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log tool usage event: {e}")
    
    @staticmethod
    def log_ticket_created(user_id: str, ticket_id: str, session_id: Optional[str] = None):
        """记录工单创建事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.TICKET_CREATED,
                event_data={
                    "ticket_id": ticket_id,
                    "creation_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged ticket created event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log ticket created event: {e}")
    
    @staticmethod
    def log_ticket_updated(user_id: str, ticket_id: str, session_id: Optional[str] = None):
        """记录工单更新事件"""
        try:
            Analytics.log_event(
                user_id=user_id,
                event_type=AnalyticsEventType.TICKET_UPDATED,
                event_data={
                    "ticket_id": ticket_id,
                    "update_time": datetime.now().isoformat()
                },
                session_id=session_id
            )
            log.debug(f"Logged ticket updated event for user {user_id}")
        except Exception as e:
            log.error(f"Failed to log ticket updated event: {e}")


def get_session_id(request) -> Optional[str]:
    """从请求中获取会话ID"""
    try:
        # 尝试从请求头中获取会话ID
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id
        
        # 如果没有会话ID，生成一个
        return str(uuid.uuid4())
    except Exception:
        return None
