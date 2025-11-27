from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
import logging
import time
from functools import lru_cache

from open_webui.models.analytics import Analytics, AnalyticsSummary, UserActivityStats, DailyStats
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission

log = logging.getLogger(__name__)

router = APIRouter()

# 简单的内存缓存
analytics_cache = {}
CACHE_TTL = 300  # 5分钟缓存

def get_cached_data(cache_key: str, ttl: int = CACHE_TTL):
    """获取缓存数据"""
    if cache_key in analytics_cache:
        data, timestamp = analytics_cache[cache_key]
        if time.time() - timestamp < ttl:
            return data
    return None

def set_cached_data(cache_key: str, data):
    """设置缓存数据"""
    analytics_cache[cache_key] = (data, time.time())

def clear_analytics_cache():
    """清除所有分析缓存"""
    global analytics_cache
    analytics_cache.clear()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    request: Request,
    days: int = 30,
    user=Depends(get_verified_user)
):
    """获取运营分析摘要 (需要analytics权限)"""
    try:
        # 检查用户是否有运营分析权限（管理员自动拥有所有权限）
        if user.role != "admin" and not has_permission(
            user.id,
            "workspace.analytics",
            request.app.state.config.USER_PERMISSIONS,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问运营分析数据。请联系管理员申请权限。",
            )
        
        # 检查缓存
        cache_key = f"analytics_summary_{days}"
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        summary = Analytics.get_analytics_summary(days=days)
        
        # 设置缓存
        set_cached_data(cache_key, summary)
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting analytics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics summary"
        )


@router.get("/users", response_model=list[UserActivityStats])
async def get_user_activity_stats(
    request: Request,
    user_id: Optional[str] = None,
    days: int = 30,
    limit: int = 50,
    user=Depends(get_verified_user)
):
    """获取用户活动统计 (需要analytics权限)"""
    try:
        # 检查用户是否有运营分析权限（管理员自动拥有所有权限）
        if user.role != "admin" and not has_permission(
            user.id,
            "workspace.analytics",
            request.app.state.config.USER_PERMISSIONS,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问用户活动数据。请联系管理员申请权限。",
            )
        
        # 检查缓存
        cache_key = f"user_activity_stats_{user_id}_{days}_{limit}"
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        stats = Analytics.get_user_activity_stats(user_id=user_id, days=days)
        result = stats[:limit]
        
        # 设置缓存
        set_cached_data(cache_key, result)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting user activity stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user activity stats"
        )


@router.get("/daily", response_model=list[DailyStats])
async def get_daily_stats(
    request: Request,
    days: int = 30,
    user=Depends(get_verified_user)
):
    """获取每日统计 (需要analytics权限)"""
    try:
        # 检查用户是否有运营分析权限（管理员自动拥有所有权限）
        if user.role != "admin" and not has_permission(
            user.id,
            "workspace.analytics",
            request.app.state.config.USER_PERMISSIONS,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问每日统计数据。请联系管理员申请权限。",
            )
        
        # 检查缓存
        cache_key = f"daily_stats_{days}"
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        stats = Analytics.get_daily_stats(days=days)
        
        # 设置缓存
        set_cached_data(cache_key, stats)
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting daily stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get daily stats"
        )


@router.get("/my-stats", response_model=UserActivityStats)
async def get_my_activity_stats(
    request: Request,
    days: int = 30,
    user=Depends(get_verified_user)
):
    """获取当前用户的活动统计"""
    try:
        stats = Analytics.get_user_activity_stats(user_id=user.id, days=days)
        if stats:
            return stats[0]
        else:
            # 返回空统计
            return UserActivityStats(
                user_id=user.id,
                user_name=user.name,
                user_email=user.email
            )
    except Exception as e:
        log.error(f"Error getting user activity stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user activity stats"
        )


@router.post("/log-event")
async def log_analytics_event(
    request: Request,
    event_type: str,
    event_data: Optional[dict] = None,
    session_id: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """记录分析事件"""
    try:
        from open_webui.models.analytics import AnalyticsEventType
        
        # 验证事件类型
        if event_type not in [e.value for e in AnalyticsEventType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}"
            )
        
        success = Analytics.log_event(
            user_id=user.id,
            event_type=AnalyticsEventType(event_type),
            event_data=event_data,
            session_id=session_id
        )
        
        if success:
            # 记录事件后清除缓存，确保数据实时性
            clear_analytics_cache()
            return {"message": "Event logged successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log event"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error logging analytics event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log event"
        )
