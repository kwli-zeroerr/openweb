import time
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timedelta

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Boolean, Index, DateTime, Float


class AnalyticsEventType(str, Enum):
    """分析事件类型"""
    CHAT_MESSAGE = "chat_message"
    CHAT_THUMBS_UP = "chat_thumbs_up"
    CHAT_THUMBS_DOWN = "chat_thumbs_down"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    MODEL_USAGE = "model_usage"
    KNOWLEDGE_ACCESS = "knowledge_access"
    TOOL_USAGE = "tool_usage"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"


class AnalyticsEvent(Base):
    """分析事件表"""
    __tablename__ = "analytics_events"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSONField, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # 索引
    __table_args__ = (
        Index('idx_analytics_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_analytics_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_analytics_session', 'session_id'),
    )


class UserActivityStats(BaseModel):
    """用户活动统计"""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    user_name: str
    user_email: str
    total_messages: int = 0
    total_thumbs_up: int = 0
    total_thumbs_down: int = 0
    thumbs_up_ratio: float = 0.0
    last_active: Optional[datetime] = None
    login_count: int = 0
    session_count: int = 0
    model_usage_count: int = 0
    knowledge_access_count: int = 0
    tool_usage_count: int = 0
    ticket_count: int = 0


class DailyStats(BaseModel):
    """每日统计"""
    model_config = ConfigDict(from_attributes=True)
    
    date: str
    daily_active_users: int = 0
    total_messages: int = 0
    total_thumbs_up: int = 0
    total_thumbs_down: int = 0
    thumbs_up_ratio: float = 0.0
    new_users: int = 0
    total_sessions: int = 0
    model_usage_count: int = 0
    knowledge_access_count: int = 0
    tool_usage_count: int = 0
    ticket_count: int = 0


class AnalyticsSummary(BaseModel):
    """分析摘要"""
    model_config = ConfigDict(from_attributes=True)
    
    total_users: int = 0
    active_users_today: int = 0
    active_users_this_week: int = 0
    active_users_this_month: int = 0
    total_messages: int = 0
    total_thumbs_up: int = 0
    total_thumbs_down: int = 0
    overall_thumbs_up_ratio: float = 0.0
    daily_stats: List[DailyStats] = []
    top_users: List[UserActivityStats] = []


class Analytics:
    """分析数据管理类"""
    
    @staticmethod
    def log_event(
        user_id: str,
        event_type: AnalyticsEventType,
        event_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """记录分析事件"""
        try:
            with get_db() as db:
                event = AnalyticsEvent(
                    id=f"{int(time.time() * 1000)}-{user_id}",
                    user_id=user_id,
                    event_type=event_type.value,
                    event_data=event_data or {},
                    timestamp=datetime.now(),
                    session_id=session_id
                )
                db.add(event)
                db.commit()
                return True
        except Exception as e:
            print(f"Error logging analytics event: {e}")
            return False
    
    @staticmethod
    def get_user_activity_stats(
        user_id: Optional[str] = None,
        days: int = 30
    ) -> List[UserActivityStats]:
        """获取用户活动统计 - 直接使用chat和feedback表"""
        try:
            with get_db() as db:
                from open_webui.models.users import Users
                from sqlalchemy import text
                import json
                
                # 获取所有用户
                users_result = Users.get_users()
                users = users_result.get('users', [])
                
                # 如果指定了用户ID，只获取该用户
                if user_id:
                    users = [u for u in users if u.id == user_id]
                
                stats = []
                cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
                
                for user in users:
                    # 从chat表获取对话数量（一问一答算一次对话）
                    try:
                        result = db.execute(text("""
                            SELECT chat FROM chat 
                            WHERE user_id = :user_id AND created_at >= :cutoff_timestamp
                        """), {
                            "user_id": user.id,
                            "cutoff_timestamp": cutoff_timestamp
                        })
                        chat_records = result.fetchall()
                        
                        total_messages = 0  # 对话数
                        for (chat_json,) in chat_records:
                            if chat_json:
                                try:
                                    chat_data = json.loads(chat_json)
                                    if 'messages' in chat_data:
                                        messages = chat_data['messages']
                                        # 计算对话数（一问一答算一次对话）
                                        conversations = 0
                                        for i in range(0, len(messages), 2):
                                            if i + 1 < len(messages):
                                                user_msg = messages[i]
                                                assistant_msg = messages[i + 1]
                                                if (user_msg.get('role') == 'user' and 
                                                    assistant_msg.get('role') == 'assistant'):
                                                    conversations += 1
                                        total_messages += conversations
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"Error getting chat data for user {user.id}: {e}")
                        total_messages = 0
                    
                    # 从feedback表获取点赞点踩数据
                    try:
                        result = db.execute(text("""
                            SELECT 
                                SUM(CASE WHEN JSON_EXTRACT(f.data, '$.rating') = 1 THEN 1 ELSE 0 END) as thumbs_up,
                                SUM(CASE WHEN JSON_EXTRACT(f.data, '$.rating') = -1 THEN 1 ELSE 0 END) as thumbs_down
                            FROM feedback f
                            WHERE f.user_id = :user_id 
                                AND f.created_at >= :cutoff_timestamp
                        """), {
                            "user_id": user.id,
                            "cutoff_timestamp": cutoff_timestamp
                        })
                        
                        feedback_data = result.fetchone()
                        total_thumbs_up = int(feedback_data[0] or 0)
                        total_thumbs_down = int(feedback_data[1] or 0)
                            
                    except Exception as e:
                        print(f"Error getting feedback data for user {user.id}: {e}")
                        total_thumbs_up = 0
                        total_thumbs_down = 0
                    
                    # 计算点赞比例
                    thumbs_up_ratio = 0.0
                    if total_messages > 0:
                        thumbs_up_ratio = total_thumbs_up / total_messages
                    
                    # 获取最后活跃时间
                    last_active = None
                    if user.last_active_at:
                        last_active = datetime.fromtimestamp(user.last_active_at)
                    
                    # 简化统计 - 基于现有数据
                    login_count = 1 if user.last_active_at else 0  # 简化：有活跃时间就算登录过
                    session_count = 1 if total_messages > 0 else 0  # 简化：有对话就算有会话
                    model_usage_count = total_messages  # 简化：对话数等于模型使用次数
                    knowledge_access_count = 0  # 暂时设为0
                    tool_usage_count = 0  # 暂时设为0
                    ticket_count = 0  # 暂时设为0
                    
                    stats.append(UserActivityStats(
                        user_id=user.id,
                        user_name=user.name,
                        user_email=user.email,
                        total_messages=total_messages,
                        total_thumbs_up=total_thumbs_up,
                        total_thumbs_down=total_thumbs_down,
                        thumbs_up_ratio=thumbs_up_ratio,
                        last_active=last_active,
                        login_count=login_count,
                        session_count=session_count,
                        model_usage_count=model_usage_count,
                        knowledge_access_count=knowledge_access_count,
                        tool_usage_count=tool_usage_count,
                        ticket_count=ticket_count
                    ))
                
                # 按消息数量排序
                stats.sort(key=lambda x: x.total_messages, reverse=True)
                return stats
                
        except Exception as e:
            print(f"Error getting user activity stats: {e}")
            return []
    
    @staticmethod
    def get_daily_stats(days: int = 30) -> List[DailyStats]:
        """获取每日统计 - 直接使用chat和feedback表"""
        try:
            with get_db() as db:
                from sqlalchemy import text
                import json
                
                stats = []
                
                for i in range(days):
                    date = datetime.now() - timedelta(days=i)
                    date_str = date.strftime('%Y-%m-%d')
                    
                    # 获取当天的开始和结束时间戳
                    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_day = start_of_day + timedelta(days=1)
                    start_timestamp = int(start_of_day.timestamp())
                    end_timestamp = int(end_of_day.timestamp())
                    
                    # 从chat表获取当天的对话数量和活跃用户
                    try:
                        result = db.execute(text("""
                            SELECT user_id, chat FROM chat 
                            WHERE created_at >= :start_timestamp AND created_at < :end_timestamp
                        """), {
                            "start_timestamp": start_timestamp,
                            "end_timestamp": end_timestamp
                        })
                        chat_records = result.fetchall()
                        
                        daily_messages = 0  # 当天的对话数
                        active_users = set()  # 当天的活跃用户
                        
                        for user_id, chat_json in chat_records:
                            active_users.add(user_id)
                            if chat_json:
                                try:
                                    chat_data = json.loads(chat_json)
                                    if 'messages' in chat_data:
                                        messages = chat_data['messages']
                                        # 计算对话数（一问一答算一次对话）
                                        conversations = 0
                                        for j in range(0, len(messages), 2):
                                            if j + 1 < len(messages):
                                                user_msg = messages[j]
                                                assistant_msg = messages[j + 1]
                                                if (user_msg.get('role') == 'user' and 
                                                    assistant_msg.get('role') == 'assistant'):
                                                    conversations += 1
                                        daily_messages += conversations
                                except Exception:
                                    pass
                        
                        daily_active_users = len(active_users)
                        total_messages = daily_messages
                        
                    except Exception as e:
                        print(f"Error getting daily chat data: {e}")
                        daily_active_users = 0
                        total_messages = 0
                    
                    # 从feedback表获取当天的点赞点踩数据
                    try:
                        result = db.execute(text("""
                            SELECT 
                                SUM(CASE WHEN JSON_EXTRACT(f.data, '$.rating') = 1 THEN 1 ELSE 0 END) as thumbs_up,
                                SUM(CASE WHEN JSON_EXTRACT(f.data, '$.rating') = -1 THEN 1 ELSE 0 END) as thumbs_down
                            FROM feedback f
                            WHERE f.created_at >= :start_timestamp AND f.created_at < :end_timestamp
                        """), {
                            "start_timestamp": start_timestamp,
                            "end_timestamp": end_timestamp
                        })
                        
                        feedback_data = result.fetchone()
                        total_thumbs_up = int(feedback_data[0] or 0)
                        total_thumbs_down = int(feedback_data[1] or 0)
                            
                    except Exception as e:
                        print(f"Error getting daily feedback data: {e}")
                        total_thumbs_up = 0
                        total_thumbs_down = 0
                    
                    # 计算点赞比例
                    thumbs_up_ratio = 0.0
                    if total_messages > 0:
                        thumbs_up_ratio = total_thumbs_up / total_messages
                    
                    # 简化统计 - 基于现有数据
                    new_users = 0  # 暂时设为0，需要根据用户注册时间计算
                    total_sessions = daily_active_users  # 简化：活跃用户数等于会话数
                    model_usage_count = total_messages  # 简化：对话数等于模型使用次数
                    knowledge_access_count = 0  # 暂时设为0
                    tool_usage_count = 0  # 暂时设为0
                    ticket_count = 0  # 暂时设为0
                    
                    stats.append(DailyStats(
                        date=date_str,
                        daily_active_users=daily_active_users,
                        total_messages=total_messages,
                        total_thumbs_up=total_thumbs_up,
                        total_thumbs_down=total_thumbs_down,
                        thumbs_up_ratio=thumbs_up_ratio,
                        new_users=new_users,
                        total_sessions=total_sessions,
                        model_usage_count=model_usage_count,
                        knowledge_access_count=knowledge_access_count,
                        tool_usage_count=tool_usage_count,
                        ticket_count=ticket_count
                    ))
                
                # 按日期排序（最新的在前）
                stats.sort(key=lambda x: x.date, reverse=True)
                return stats
                
        except Exception as e:
            print(f"Error getting daily stats: {e}")
            return []
    
    @staticmethod
    def get_analytics_summary(days: int = 30) -> AnalyticsSummary:
        """获取分析摘要"""
        try:
            # 获取用户统计
            user_stats = Analytics.get_user_activity_stats(days=days)
            
            # 获取每日统计
            daily_stats = Analytics.get_daily_stats(days=days)
            
            # 计算总体统计
            total_users = len(user_stats)
            active_users_today = len([u for u in user_stats if u.last_active and u.last_active.date() == datetime.now().date()])
            active_users_this_week = len([u for u in user_stats if u.last_active and u.last_active >= datetime.now() - timedelta(days=7)])
            active_users_this_month = len([u for u in user_stats if u.last_active and u.last_active >= datetime.now() - timedelta(days=30)])
            
            total_messages = sum(u.total_messages for u in user_stats)
            total_thumbs_up = sum(u.total_thumbs_up for u in user_stats)
            total_thumbs_down = sum(u.total_thumbs_down for u in user_stats)
            
            # 计算总体点赞比例 - 总点赞数 / 总消息数（对话数）
            overall_thumbs_up_ratio = 0.0
            if total_messages > 0:
                overall_thumbs_up_ratio = total_thumbs_up / total_messages
            
            # 获取前10名活跃用户
            top_users = user_stats[:10]
            
            return AnalyticsSummary(
                total_users=total_users,
                active_users_today=active_users_today,
                active_users_this_week=active_users_this_week,
                active_users_this_month=active_users_this_month,
                total_messages=total_messages,
                total_thumbs_up=total_thumbs_up,
                total_thumbs_down=total_thumbs_down,
                overall_thumbs_up_ratio=overall_thumbs_up_ratio,
                daily_stats=daily_stats,
                top_users=top_users
            )
            
        except Exception as e:
            print(f"Error getting analytics summary: {e}")
            return AnalyticsSummary()
