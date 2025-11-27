from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
import logging

from open_webui.models.users import Users, UserModel
from open_webui.models.feedbacks import (
    FeedbackModel,
    FeedbackResponse,
    FeedbackForm,
    Feedbacks,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetConfig
############################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": request.app.state.config.EVALUATION_ARENA_MODELS,
    }


############################
# UpdateConfig
############################


class UpdateConfigForm(BaseModel):
    ENABLE_EVALUATION_ARENA_MODELS: Optional[bool] = None
    EVALUATION_ARENA_MODELS: Optional[list[dict]] = None


@router.post("/config")
async def update_config(
    request: Request,
    form_data: UpdateConfigForm,
    user=Depends(get_admin_user),
):
    config = request.app.state.config
    if form_data.ENABLE_EVALUATION_ARENA_MODELS is not None:
        config.ENABLE_EVALUATION_ARENA_MODELS = form_data.ENABLE_EVALUATION_ARENA_MODELS
    if form_data.EVALUATION_ARENA_MODELS is not None:
        config.EVALUATION_ARENA_MODELS = form_data.EVALUATION_ARENA_MODELS
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": config.EVALUATION_ARENA_MODELS,
    }


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str = "pending"

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class FeedbackUserResponse(FeedbackResponse):
    user: Optional[UserResponse] = None


@router.get("/feedbacks/all", response_model=list[FeedbackUserResponse])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()

    feedback_list = []
    for feedback in feedbacks:
        user = Users.get_user_by_id(feedback.user_id)
        feedback_list.append(
            FeedbackUserResponse(
                **feedback.model_dump(),
                user=UserResponse(**user.model_dump()) if user else None,
            )
        )
    return feedback_list


@router.delete("/feedbacks/all")
async def delete_all_feedbacks(user=Depends(get_admin_user)):
    success = Feedbacks.delete_all_feedbacks()
    return success


@router.get("/feedbacks/all/export", response_model=list[FeedbackModel])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()
    return feedbacks


@router.get("/feedbacks/user", response_model=list[FeedbackUserResponse])
async def get_feedbacks(user=Depends(get_verified_user)):
    feedbacks = Feedbacks.get_feedbacks_by_user_id(user.id)
    return feedbacks


@router.delete("/feedbacks", response_model=bool)
async def delete_feedbacks(user=Depends(get_verified_user)):
    success = Feedbacks.delete_feedbacks_by_user_id(user.id)
    return success


@router.post("/feedback", response_model=FeedbackModel)
async def create_feedback(
    request: Request,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
):
    feedback = Feedbacks.insert_new_feedback(user_id=user.id, form_data=form_data)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    # 如果为负面反馈，创建时也尝试自动生成工单（此前只在更新时触发）
    try:
        await _handle_negative_feedback(request, feedback, user)
    except Exception as e:
        log.error(f"Error handling negative feedback on create: {e}")

    # 分析事件记录暂时禁用，避免影响反馈功能

    return feedback


@router.get("/feedback/{id}", response_model=FeedbackModel)
async def get_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        feedback = Feedbacks.get_feedback_by_id(id=id)
    else:
        feedback = Feedbacks.get_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.post("/feedback/{id}", response_model=FeedbackModel)
async def update_feedback_by_id(
    id: str, form_data: FeedbackForm, user=Depends(get_verified_user), request: Request = None
):
    if user.role == "admin":
        feedback = Feedbacks.update_feedback_by_id(id=id, form_data=form_data)
    else:
        feedback = Feedbacks.update_feedback_by_id_and_user_id(
            id=id, user_id=user.id, form_data=form_data
        )

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # 检查是否为负面反馈，如果是则自动生成工单
    await _handle_negative_feedback(request, feedback, user)

    # 分析事件记录暂时禁用，避免影响反馈功能

    return feedback


@router.delete("/feedback/{id}")
async def delete_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        success = Feedbacks.delete_feedback_by_id(id=id)
    else:
        success = Feedbacks.delete_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return success


############################
# Negative Feedback Handler
############################

async def _handle_negative_feedback(request: Request, feedback: FeedbackModel, user: UserModel):
    """
    处理负面反馈，自动生成工单
    
    Args:
        request: FastAPI请求对象
        feedback: 反馈数据
        user: 用户信息
    """
    try:
        # 检查是否为负面反馈
        if not _is_negative_feedback(feedback):
            return
        
        # 导入AI工单服务
        try:
            from open_webui.services.ai_ticket_service import ai_ticket_service
            
            # 生成工单
            ticket = await ai_ticket_service.generate_ticket_from_feedback(
                feedback_data=feedback.model_dump(),
                user_id=user.id,
                request=request
            )
        except ImportError as e:
            log.error(f"Failed to import AI ticket service: {e}")
            return
        except Exception as e:
            log.error(f"Error in AI ticket service: {e}")
            return
        
        if ticket:
            log.info(f"Auto-generated ticket {ticket.id} for negative feedback {feedback.id}")
        else:
            log.warning(f"Failed to generate ticket for negative feedback {feedback.id}")
            
    except Exception as e:
        log.error(f"Error handling negative feedback: {e}")


def _is_negative_feedback(feedback: FeedbackModel) -> bool:
    """
    判断是否为负面反馈（需要生成工单）
    评分是负数就生成工单，不需要检查评论
    
    Args:
        feedback: 反馈数据
        
    Returns:
        bool: 是否为需要生成工单的负面反馈
    """
    try:
        # 检查评分反馈
        if feedback.type == "rating" and feedback.data:
            rating = feedback.data.get("rating")
            
            if rating is not None:
                # 评分是负数就生成工单
                if isinstance(rating, (int, float)) and rating <= 0:
                    return True
                # 字符串形式的负面评分
                elif isinstance(rating, str) and rating.lower() in ["-1", "negative", "bad", "poor"]:
                    return True
                
                # 如果评分是正数，直接返回False
                if isinstance(rating, (int, float)) and rating > 0:
                    return False
                if isinstance(rating, str) and rating.lower() in ["1", "positive", "good", "excellent"]:
                    return False
        
        # 检查评论内容
        if feedback.data and feedback.data.get("comment"):
            comment = feedback.data.get("comment", "").lower()
            negative_keywords = [
                "不好", "错误", "问题", "bug", "故障", "不满意", "失望",
                "不准确", "不相关", "没用", "垃圾", "差劲", "糟糕",
                "bad", "wrong", "error", "bug", "problem", "disappointed",
                "inaccurate", "irrelevant", "useless", "terrible", "awful"
            ]
            
            for keyword in negative_keywords:
                if keyword in comment:
                    return True
        
        return False
        
    except Exception as e:
        log.error(f"Error checking negative feedback: {e}")
        return False
