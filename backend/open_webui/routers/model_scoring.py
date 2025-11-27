from typing import Optional, List, Dict, Any
import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import text, func, desc, asc
from sqlalchemy.orm import Session

from open_webui.models.users import Users, UserModel
from open_webui.models.feedbacks import Feedbacks, FeedbackModel
from open_webui.internal.db import get_db
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()


############################
# Model Scoring Models
############################

class ModelScore(BaseModel):
    model_id: str
    model_name: str
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    thumbs_up: int
    thumbs_down: int
    average_rating: float
    win_rate: float
    total_messages: int
    last_updated: int


class ModelScoringResponse(BaseModel):
    models: List[ModelScore]
    total_models: int
    last_updated: int


class ModelDetailResponse(BaseModel):
    model_id: str
    model_name: str
    scores: ModelScore
    recent_feedback: List[Dict[str, Any]]
    performance_trend: List[Dict[str, Any]]


############################
# Get Model Scoring Leaderboard
############################

@router.get("/leaderboard", response_model=ModelScoringResponse)
async def get_model_scoring_leaderboard(
    request: Request,
    limit: int = 50,
    sort_by: str = "average_rating",
    order: str = "desc",
    user=Depends(get_admin_user)
):
    """获取模型评分排行榜"""
    try:
        with get_db() as db:
            # 构建基础查询
            base_query = text("""
                SELECT 
                    COALESCE(f.data->>'model_id', 'unknown') as model_id,
                    COALESCE(f.data->>'model_id', 'unknown') as model_name,
                    COUNT(DISTINCT f.id) as total_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '1' THEN f.id END) as positive_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '-1' THEN f.id END) as negative_feedback,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_up' THEN mr.id END) as thumbs_up,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_down' THEN mr.id END) as thumbs_down,
                    AVG(CAST(f.data->>'rating' AS FLOAT)) as average_rating,
                    COUNT(DISTINCT m.id) as total_messages,
                    MAX(f.updated_at) as last_updated
                FROM feedback f
                LEFT JOIN message_reaction mr ON mr.message_id = f.meta->>'message_id'
                LEFT JOIN message m ON m.id = f.meta->>'message_id'
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' IS NOT NULL
                GROUP BY f.data->>'model_id'
                HAVING COUNT(DISTINCT f.id) > 0
            """)
            
            # 添加排序
            if sort_by == "average_rating":
                order_clause = "ORDER BY average_rating DESC" if order == "desc" else "ORDER BY average_rating ASC"
            elif sort_by == "total_feedback":
                order_clause = "ORDER BY total_feedback DESC" if order == "desc" else "ORDER BY total_feedback ASC"
            elif sort_by == "win_rate":
                order_clause = "ORDER BY (positive_feedback * 1.0 / NULLIF(total_feedback, 0)) DESC" if order == "desc" else "ORDER BY (positive_feedback * 1.0 / NULLIF(total_feedback, 0)) ASC"
            else:
                order_clause = "ORDER BY average_rating DESC"
            
            # 添加限制
            limit_clause = f"LIMIT {limit}"
            
            # 执行查询
            query = f"{base_query} {order_clause} {limit_clause}"
            result = db.execute(query)
            
            models = []
            for row in result:
                total_feedback = row.total_feedback or 0
                positive_feedback = row.positive_feedback or 0
                negative_feedback = row.negative_feedback or 0
                thumbs_up = row.thumbs_up or 0
                thumbs_down = row.thumbs_down or 0
                average_rating = float(row.average_rating) if row.average_rating else 0.0
                total_messages = row.total_messages or 0
                
                # 计算胜率
                win_rate = (positive_feedback * 1.0 / total_feedback) if total_feedback > 0 else 0.0
                
                model_score = ModelScore(
                    model_id=row.model_id,
                    model_name=row.model_name,
                    total_feedback=total_feedback,
                    positive_feedback=positive_feedback,
                    negative_feedback=negative_feedback,
                    thumbs_up=thumbs_up,
                    thumbs_down=thumbs_down,
                    average_rating=average_rating,
                    win_rate=win_rate,
                    total_messages=total_messages,
                    last_updated=row.last_updated or 0
                )
                models.append(model_score)
            
            # 获取总数
            count_query = text("""
                SELECT COUNT(DISTINCT f.data->>'model_id') as total_models
                FROM feedback f
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' IS NOT NULL
            """)
            count_result = db.execute(count_query).fetchone()
            total_models = count_result.total_models if count_result else 0
            
            return ModelScoringResponse(
                models=models,
                total_models=total_models,
                last_updated=int(time.time())
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型评分排行榜失败: {str(e)}"
        )


############################
# Get Model Detail
############################

@router.get("/model/{model_id}", response_model=ModelDetailResponse)
async def get_model_detail(
    model_id: str,
    request: Request,
    user=Depends(get_admin_user)
):
    """获取特定模型的详细评分信息"""
    try:
        with get_db() as db:
            # 获取模型基础评分信息
            score_query = text("""
                SELECT 
                    COALESCE(f.data->>'model_id', 'unknown') as model_id,
                    COALESCE(f.data->>'model_id', 'unknown') as model_name,
                    COUNT(DISTINCT f.id) as total_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '1' THEN f.id END) as positive_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '-1' THEN f.id END) as negative_feedback,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_up' THEN mr.id END) as thumbs_up,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_down' THEN mr.id END) as thumbs_down,
                    AVG(CAST(f.data->>'rating' AS FLOAT)) as average_rating,
                    COUNT(DISTINCT m.id) as total_messages,
                    MAX(f.updated_at) as last_updated
                FROM feedback f
                LEFT JOIN message_reaction mr ON mr.message_id = f.meta->>'message_id'
                LEFT JOIN message m ON m.id = f.meta->>'message_id'
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' = :model_id
                GROUP BY f.data->>'model_id'
            """)
            
            result = db.execute(score_query, {"model_id": model_id}).fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"模型 {model_id} 未找到"
                )
            
            # 构建评分数据
            total_feedback = result.total_feedback or 0
            positive_feedback = result.positive_feedback or 0
            negative_feedback = result.negative_feedback or 0
            thumbs_up = result.thumbs_up or 0
            thumbs_down = result.thumbs_down or 0
            average_rating = float(result.average_rating) if result.average_rating else 0.0
            total_messages = result.total_messages or 0
            win_rate = (positive_feedback * 1.0 / total_feedback) if total_feedback > 0 else 0.0
            
            scores = ModelScore(
                model_id=result.model_id,
                model_name=result.model_name,
                total_feedback=total_feedback,
                positive_feedback=positive_feedback,
                negative_feedback=negative_feedback,
                thumbs_up=thumbs_up,
                thumbs_down=thumbs_down,
                average_rating=average_rating,
                win_rate=win_rate,
                total_messages=total_messages,
                last_updated=result.last_updated or 0
            )
            
            # 获取最近的反馈
            recent_feedback_query = text("""
                SELECT 
                    f.id,
                    f.data,
                    f.meta,
                    f.created_at,
                    u.name as user_name,
                    u.profile_image_url
                FROM feedback f
                LEFT JOIN user u ON u.id = f.user_id
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' = :model_id
                ORDER BY f.created_at DESC
                LIMIT 10
            """)
            
            recent_result = db.execute(recent_feedback_query, {"model_id": model_id})
            recent_feedback = []
            for row in recent_result:
                recent_feedback.append({
                    "id": row.id,
                    "data": row.data,
                    "meta": row.meta,
                    "created_at": row.created_at,
                    "user_name": row.user_name,
                    "profile_image_url": row.profile_image_url
                })
            
            # 获取性能趋势（按天统计）
            trend_query = text("""
                SELECT 
                    DATE(f.created_at/1000, 'unixepoch') as date,
                    COUNT(*) as daily_feedback,
                    AVG(CAST(f.data->>'rating' AS FLOAT)) as daily_rating
                FROM feedback f
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' = :model_id
                AND f.created_at >= :start_time
                GROUP BY DATE(f.created_at/1000, 'unixepoch')
                ORDER BY date DESC
                LIMIT 30
            """)
            
            # 计算30天前的时间戳
            thirty_days_ago = int(time.time() - 30 * 24 * 60 * 60) * 1000
            
            trend_result = db.execute(trend_query, {
                "model_id": model_id,
                "start_time": thirty_days_ago
            })
            
            performance_trend = []
            for row in trend_result:
                performance_trend.append({
                    "date": row.date,
                    "daily_feedback": row.daily_feedback,
                    "daily_rating": float(row.daily_rating) if row.daily_rating else 0.0
                })
            
            return ModelDetailResponse(
                model_id=model_id,
                model_name=result.model_name,
                scores=scores,
                recent_feedback=recent_feedback,
                performance_trend=performance_trend
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型详情失败: {str(e)}"
        )


############################
# Update Model Scoring
############################

@router.post("/update")
async def update_model_scoring(
    request: Request,
    user=Depends(get_admin_user)
):
    """手动更新模型评分统计"""
    try:
        # 这里可以添加缓存更新逻辑
        # 或者重新计算评分统计
        
        return {
            "message": "模型评分统计已更新",
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型评分失败: {str(e)}"
        )


############################
# Export Model Scoring Data
############################

@router.get("/export")
async def export_model_scoring_data(
    request: Request,
    format: str = "json",
    user=Depends(get_admin_user)
):
    """导出模型评分数据"""
    try:
        with get_db() as db:
            # 获取所有模型评分数据
            query = text("""
                SELECT 
                    COALESCE(f.data->>'model_id', 'unknown') as model_id,
                    COUNT(DISTINCT f.id) as total_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '1' THEN f.id END) as positive_feedback,
                    COUNT(DISTINCT CASE WHEN f.data->>'rating' = '-1' THEN f.id END) as negative_feedback,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_up' THEN mr.id END) as thumbs_up,
                    COUNT(DISTINCT CASE WHEN mr.name = 'thumbs_down' THEN mr.id END) as thumbs_down,
                    AVG(CAST(f.data->>'rating' AS FLOAT)) as average_rating,
                    COUNT(DISTINCT m.id) as total_messages,
                    MAX(f.updated_at) as last_updated
                FROM feedback f
                LEFT JOIN message_reaction mr ON mr.message_id = f.meta->>'message_id'
                LEFT JOIN message m ON m.id = f.meta->>'message_id'
                WHERE f.type = 'rating' 
                AND f.data->>'model_id' IS NOT NULL
                GROUP BY f.data->>'model_id'
                ORDER BY average_rating DESC
            """)
            
            result = db.execute(query)
            
            data = []
            for row in result:
                total_feedback = row.total_feedback or 0
                positive_feedback = row.positive_feedback or 0
                win_rate = (positive_feedback * 1.0 / total_feedback) if total_feedback > 0 else 0.0
                
                data.append({
                    "model_id": row.model_id,
                    "total_feedback": total_feedback,
                    "positive_feedback": positive_feedback,
                    "negative_feedback": row.negative_feedback or 0,
                    "thumbs_up": row.thumbs_up or 0,
                    "thumbs_down": row.thumbs_down or 0,
                    "average_rating": float(row.average_rating) if row.average_rating else 0.0,
                    "win_rate": win_rate,
                    "total_messages": row.total_messages or 0,
                    "last_updated": row.last_updated or 0
                })
            
            if format.lower() == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
                writer.writeheader()
                writer.writerows(data)
                
                return {
                    "data": output.getvalue(),
                    "format": "csv",
                    "filename": f"model_scoring_{int(time.time())}.csv"
                }
            else:
                return {
                    "data": data,
                    "format": "json",
                    "total_models": len(data),
                    "exported_at": int(time.time())
                }
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出模型评分数据失败: {str(e)}"
        )
