import logging
from typing import Optional
import uuid
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, File, UploadFile
from pydantic import BaseModel
from typing import List

from open_webui.models.tickets import (
    TicketModel,
    TicketListResponse,
    CreateTicketForm,
    UpdateTicketForm,
    AddCommentForm,
    TicketComment,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    Tickets,
)
from open_webui.models.ticket_config import TicketConfigs, TicketConfigModel
from open_webui.models.users import Users
from open_webui.models.groups import Groups
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.services.notification_service import notification_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

# 简单的内存缓存实现
_config_cache = {"data": None, "timestamp": 0}
CONFIG_CACHE_TTL = 300  # 5分钟

def get_cached_config():
    """缓存工单配置查询"""
    now = time.time()
    if _config_cache["data"] is None or (now - _config_cache["timestamp"]) > CONFIG_CACHE_TTL:
        _config_cache["data"] = TicketConfigs.get_config()
        _config_cache["timestamp"] = now
    return _config_cache["data"]


############################
# Generate AI Analysis for Manual Ticket
############################

@router.post("/{ticket_id}/generate-ai-analysis", response_model=dict)
async def generate_ai_analysis_for_ticket(
    ticket_id: str,
    request: Request,
    user=Depends(get_verified_user)
):
    """为人工创建的工单生成AI分析"""
    
    # 只有管理员可以触发AI分析
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can generate AI analysis"
        )
    
    try:
        # 获取工单信息
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # 检查是否已经有AI分析
        if ticket.ai_analysis:
            return {
                "success": True,
                "message": "AI analysis already exists",
                "ai_analysis": ticket.ai_analysis
            }
        
        # 检查是否启用了AI工单生成
        from open_webui.models.ticket_config import TicketConfigs
        config = TicketConfigs.get_config()
        if not config or not config.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI ticket generation is disabled"
            )
        
        # 使用AI服务生成分析
        from open_webui.services.ai_ticket_service import AITicketService
        ai_service = AITicketService()
        
        # 构建分析数据
        analysis_data = {
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority,
            "category": ticket.category,
            "tags": ticket.tags or [],
            "user_name": ticket.user_name,
            "created_at": ticket.created_at
        }
        
        # 生成AI分析
        ai_analysis = await ai_service._analyze_manual_ticket_with_ai(
            analysis_data, 
            request,
            user
        )
        
        if ai_analysis:
            # 更新工单的AI分析字段
            Tickets.update_ticket_ai_analysis(ticket_id, ai_analysis)
            
            return {
                "success": True,
                "message": "AI analysis generated successfully",
                "ai_analysis": ai_analysis
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI analysis"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error generating AI analysis for ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################

@router.post("/", response_model=TicketModel)
async def create_ticket(
    request: Request,
    form_data: CreateTicketForm,
    user=Depends(get_verified_user)
):
    """Create a new support ticket"""
    # Admins are always allowed. Users with tickets permission are allowed.
    if user.role != "admin":
        if not has_permission(
            user.id,
            "workspace.tickets",
            request.app.state.config.USER_PERMISSIONS,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限创建工单。请联系管理员申请权限，或在工单下留言说明创建需求。",
            )
    
    try:
        # Generate unique ticket ID
        ticket_id = str(uuid.uuid4())
        
        # Get user info
        user_info = Users.get_user_by_id(user.id)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.USER_NOT_FOUND
            )
        
        # Create ticket
        ticket = Tickets.create_ticket(
            id=ticket_id,
            title=form_data.title,
            description=form_data.description,
            user_id=user.id,
            user_name=user_info.name,
            user_email=user_info.email,
            priority=form_data.priority,
            category=form_data.category,
            attachments=form_data.attachments,
            tags=form_data.tags,
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create ticket"
            )
        
        # 异步生成AI分析（不阻塞工单创建）
        import asyncio
        try:
            config = get_cached_config()
            if config and config.enabled:
                # 在后台任务中生成AI分析，不阻塞响应
                async def generate_ai_analysis_background():
                    try:
                        from open_webui.services.ai_ticket_service import AITicketService
                        ai_service = AITicketService()
                        
                        # 构建分析数据
                        analysis_data = {
                            "title": ticket.title,
                            "description": ticket.description,
                            "priority": ticket.priority,
                            "category": ticket.category,
                            "tags": ticket.tags or [],
                            "user_name": ticket.user_name,
                            "created_at": ticket.created_at
                        }
                        
                        # 生成AI分析
                        ai_analysis = await ai_service._analyze_manual_ticket_with_ai(
                            analysis_data, 
                            request,
                            user
                        )
                        
                        if ai_analysis:
                            # 更新工单的AI分析字段
                            Tickets.update_ticket_ai_analysis(ticket.id, ai_analysis)
                            log.info(f"Auto-generated AI analysis for manual ticket {ticket.id}")
                    except Exception as e:
                        log.warning(f"Failed to auto-generate AI analysis for ticket {ticket.id}: {e}")
                
                # 启动后台任务
                asyncio.create_task(generate_ai_analysis_background())
        except Exception as e:
            log.warning(f"Failed to start AI analysis generation for ticket {ticket.id}: {e}")
        
        # Send notification to admins
        try:
            await notification_service.notify_new_ticket(ticket)
        except Exception as e:
            log.warning(f"Failed to send notification for new ticket: {e}")
        
        # 记录工单创建分析事件
        try:
            from open_webui.services.analytics_service import AnalyticsService, get_session_id
            session_id = get_session_id(request)
            AnalyticsService.log_ticket_created(user.id, ticket.id, session_id)
        except Exception as e:
            log.error(f"Failed to log ticket created analytics event: {e}")
        
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Get Tickets
############################

@router.get("/", response_model=TicketListResponse)
async def get_tickets(
    request: Request,
    user_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    category: Optional[TicketCategory] = None,
    skip: Optional[int] = 0,
    limit: Optional[int] = 50,
    user=Depends(get_verified_user)
):
    """Get tickets with optional filters"""
    # 优化权限检查：先检查角色，再检查权限
    
    # 检查是否有查看全部工单的权限
    has_view_all_permission = has_permission(
        user.id,
        "workspace.tickets_view_all",
        request.app.state.config.USER_PERMISSIONS,
    )
    
    log.info(f"Ticket permissions check for user {user.id}: role={user.role}, has_view_all_permission={has_view_all_permission}")
    
    if user.role != "admin" and not has_view_all_permission:
        if not has_permission(
            user.id,
            "workspace.tickets",
            request.app.state.config.USER_PERMISSIONS,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问工单系统。请联系管理员申请权限，或在工单下留言说明访问需求。",
            )
    
    try:
        # Determine what tickets the user can see
        if user.role == "admin" or has_view_all_permission:
            # Admins and users with view_all permission can see all tickets
            # If assigned_to is specified, filter by that
            if assigned_to:
                result = Tickets.get_tickets(
                    assigned_to=assigned_to,
                    status=status,
                    priority=priority,
                    category=category,
                    skip=skip,
                    limit=limit,
                )
            else:
                result = Tickets.get_tickets(
                    status=status,
                    priority=priority,
                    category=category,
                    skip=skip,
                    limit=limit,
                )
        else:
            # Regular users can see their own tickets AND tickets assigned to them
            # We need to get both types of tickets
            user_created_tickets = Tickets.get_tickets(
                user_id=user.id,
                status=status,
                priority=priority,
                category=category,
                skip=0,  # We'll handle pagination manually
                limit=1000,  # Get all to combine with assigned tickets
            )
            
            assigned_tickets = Tickets.get_tickets(
                assigned_to=user.id,
                status=status,
                priority=priority,
                category=category,
                skip=0,
                limit=1000,
            )
            
            # Combine and deduplicate tickets
            all_tickets = user_created_tickets.get("tickets", []) + assigned_tickets.get("tickets", [])
            unique_tickets = {}
            for ticket in all_tickets:
                if ticket.id not in unique_tickets:
                    unique_tickets[ticket.id] = ticket
            
            # Apply pagination
            tickets_list = list(unique_tickets.values())
            total = len(tickets_list)
            paginated_tickets = tickets_list[skip:skip + limit]
            
            result = {
                "tickets": paginated_tickets,
                "total": total
            }
        
        return TicketListResponse(**result)
        
    except Exception as e:
        log.error(f"Error getting tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Ticket Configuration API
############################

class TicketConfigRequest(BaseModel):
    enabled: bool
    model_id: str
    system_prompt: str


class TicketConfigResponse(BaseModel):
    enabled: bool
    model_id: str
    system_prompt: str


@router.get("/config", response_model=TicketConfigResponse)
async def get_ticket_config(user=Depends(get_admin_user)):
    """获取工单配置 (admin only)"""
    try:
        # 从数据库获取配置
        config = TicketConfigs.get_config()
        
        if not config:
            # 如果数据库中没有配置，返回默认配置
            config = TicketConfigs.get_default_config()
            # 保存默认配置到数据库
            TicketConfigs.save_config(config.model_dump())
        
        return TicketConfigResponse(
            enabled=config.enabled,
            model_id=config.model_id,
            system_prompt=config.system_prompt
        )
        
    except Exception as e:
        log.error(f"Error getting ticket config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket config"
        )


@router.put("/config")
async def save_ticket_config(config_data: TicketConfigRequest, user=Depends(get_admin_user)):
    """保存工单配置 (admin only)"""
    try:
        # 验证数据
        if not config_data.model_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model ID is required"
            )
        
        if not config_data.system_prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System prompt is required"
            )
        
        # 保存配置到数据库
        success = TicketConfigs.save_config(config_data.model_dump())
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save ticket config"
            )
        
        log.info(f"Ticket config saved by admin {user.id}")
        
        return {"message": "Ticket config saved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error saving ticket config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save ticket config"
        )


############################
# Get Available Admins
############################

@router.get("/available-admins")
async def get_available_admins(request: Request, user=Depends(get_admin_user)):
    """获取可分配工单的用户列表 (admin only)"""
    try:
        # 获取所有用户
        all_users_result = Users.get_users()
        all_users = all_users_result.get('users', [])
        
        available_admins = []
        for user_obj in all_users:
            # 检查用户是否有工单执行权限
            has_execute_permission = False
            if user_obj.role == "admin":
                has_execute_permission = True
            else:
                has_execute_permission = has_permission(
                    user_obj.id,
                    "workspace.tickets_execute",
                    request.app.state.config.USER_PERMISSIONS,
                )
            
            if has_execute_permission:
                # 获取工作负载
                workload_result = Tickets.get_tickets(
                    assigned_to=user_obj.id,
                    status="open",
                    limit=1000
                )
                workload = workload_result.get("total", 0)
                
                available_admins.append({
                    "id": user_obj.id,
                    "name": user_obj.name,
                    "email": user_obj.email,
                    "workload": workload,
                    "role": user_obj.role
                })
        
        
        # 按工作负载排序（工作负载少的排在前面）
        available_admins.sort(key=lambda x: x["workload"])
        
        return {"admins": available_admins}
        
    except Exception as e:
        log.error(f"Error getting available admins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Get Ticket by ID
############################

@router.get("/{ticket_id}", response_model=TicketModel)
async def get_ticket(
    request: Request,
    ticket_id: str,
    user=Depends(get_verified_user)
):
    """Get a specific ticket by ID"""
    try:
        log.info(f"Getting ticket with ID: {ticket_id}, user: {user.id}, role: {user.role}")
        ticket = Tickets.get_ticket_by_id(ticket_id)
        log.info(f"Ticket query result: {ticket is not None}")
        if not ticket:
            log.warning(f"Ticket not found: {ticket_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Check access permissions
        # Admins can see all tickets
        # Users with tickets_view_all permission can see all tickets
        # Users can see their own tickets
        # Assigned users can see tickets assigned to them
        
        # 检查是否有查看全部工单的权限
        has_view_all_permission = has_permission(
            user.id,
            "workspace.tickets_view_all",
            request.app.state.config.USER_PERMISSIONS,
        )
        
        log.info(f"Ticket access check for user {user.id}: role={user.role}, has_view_all_permission={has_view_all_permission}")
        
        # 允许访问的条件：
        # 1. 管理员
        # 2. 有查看全部工单权限的用户
        # 3. 工单创建者
        # 4. 工单被分配者
        if (user.role != "admin" and 
            not has_view_all_permission and 
            ticket.user_id != user.id and 
            ticket.assigned_to != user.id):
            log.warning(f"Access denied for user {user.id} to ticket {ticket_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket"
            )
        
        # 调试：检查交付数据
        log.info(f"Ticket delivery data for {ticket_id}: delivery_files={ticket.delivery_files}, type={type(ticket.delivery_files)}")
        
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Update Ticket
############################

@router.put("/{ticket_id}", response_model=TicketModel)
async def update_ticket(
    request: Request,
    ticket_id: str,
    form_data: UpdateTicketForm,
    user=Depends(get_verified_user)
):
    """Update a ticket"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Regular users can only update limited fields
        if user.role != "admin":
            if ticket.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            updates = {}
            # Owner updates
            if form_data.title is not None:
                updates["title"] = form_data.title
            if form_data.description is not None:
                updates["description"] = form_data.description
        else:
            # Admins can update all fields
            updates = form_data.model_dump(exclude_unset=True)
        
        if not updates:
            return ticket
        
        updated_ticket = Tickets.update_ticket(ticket_id, updates)
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update ticket"
            )
        
        return updated_ticket
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Add Comment
############################

@router.post("/{ticket_id}/comments")
async def add_comment(
    request: Request,
    ticket_id: str,
    form_data: AddCommentForm,
    user=Depends(get_verified_user)
):
    """Add a comment to a ticket"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Allow commenting for: ticket creator, assigned user, and admins
        can_comment = (
            user.role == "admin" or  # Admins can comment on any ticket
            ticket.user_id == user.id or  # Ticket creator can comment
            ticket.assigned_to == user.id  # Assigned user can comment
        )
        
        if not can_comment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Regular users cannot add internal comments
        if user.role != "admin" and form_data.is_internal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can add internal comments"
            )
        
        # Get user info
        user_info = Users.get_user_by_id(user.id)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.USER_NOT_FOUND
            )
        
        # Create comment
        comment = TicketComment(
            id=str(uuid.uuid4()),
            content=form_data.content,
            author_id=user.id,
            author_name=user_info.name,
            is_internal=form_data.is_internal,
            created_at=int(time.time()),
        )
        
        success = Tickets.add_comment(ticket_id, comment)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add comment"
            )
        
        # Send notification for new comment
        try:
            updated_ticket = Tickets.get_ticket_by_id(ticket_id)
            if updated_ticket:
                await notification_service.notify_ticket_commented(updated_ticket, comment.model_dump())
        except Exception as e:
            log.warning(f"Failed to send notification for ticket comment: {e}")
        
        return {"message": "Comment added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error adding comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Delete Ticket (Admin only)
############################

@router.delete("/{ticket_id}")
async def delete_ticket(
    request: Request,
    ticket_id: str,
    user=Depends(get_admin_user)
):
    """Delete a ticket (admin only)"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        success = Tickets.delete_ticket(ticket_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete ticket"
            )
        
        return {"message": "Ticket deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Get Ticket Statistics (Admin only)
############################

@router.get("/stats/summary")
async def get_ticket_stats(
    request: Request,
    user=Depends(get_admin_user)
):
    """Get ticket statistics (admin only)"""
    try:
        stats = Tickets.get_ticket_stats()
        
        # 添加AI生成工单的统计
        ai_stats = {
            "ai_generated_total": 0,
            "ai_generated_open": 0,
            "ai_generated_in_progress": 0,
            "ai_generated_resolved": 0,
            "ai_generated_closed": 0
        }
        
        # 获取所有工单以计算AI生成工单统计
        all_tickets = Tickets.get_tickets(limit=10000)
        tickets = all_tickets.get("tickets", [])
        
        for ticket in tickets:
            if ticket.is_ai_generated:
                ai_stats["ai_generated_total"] += 1
                if ticket.status == "open":
                    ai_stats["ai_generated_open"] += 1
                elif ticket.status == "in_progress":
                    ai_stats["ai_generated_in_progress"] += 1
                elif ticket.status == "resolved":
                    ai_stats["ai_generated_resolved"] += 1
                elif ticket.status == "closed":
                    ai_stats["ai_generated_closed"] += 1
        
        # 合并统计信息
        stats.update(ai_stats)
        
        return stats
        
    except Exception as e:
        log.error(f"Error getting ticket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats/assignment")
async def get_ticket_assignment_stats(user=Depends(get_admin_user)):
    """Get ticket assignment statistics (admin only)"""
    try:
        from open_webui.services.ticket_assignment_service import ticket_assignment_service
        stats = ticket_assignment_service.get_assignment_stats()
        return stats
        
    except Exception as e:
        log.error(f"Error getting assignment stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


############################
# Ticket Assignment APIs
############################

class AssignTicketForm(BaseModel):
    assigned_to: str
    task_requirements: Optional[str] = None  # 具体任务要求
    completion_criteria: Optional[str] = None  # 完成标准
    task_deadline: Optional[int] = None  # 截止时间（时间戳）
    task_priority: Optional[str] = None  # 任务优先级
    reason: Optional[str] = None  # 分配原因
    
    # 交付要求
    required_files: Optional[str] = None  # 需要提交的文件类型（JSON字符串）
    required_text: Optional[str] = None  # 需要提交的文字说明
    required_images: Optional[str] = None  # 需要提交的图片要求
    delivery_instructions: Optional[str] = None  # 交付说明


class TransferTicketForm(BaseModel):
    assigned_to: str
    reason: str  # 转派原因


@router.post("/{ticket_id}/assign")
async def assign_ticket(
    request: Request,
    ticket_id: str,
    form_data: AssignTicketForm,
    user=Depends(get_admin_user)
):
    """手动分配工单给管理员 (admin only)"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # 验证目标用户是否存在
        target_user = Users.get_user_by_id(form_data.assigned_to)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found"
            )
        
        # 检查目标用户是否有工单执行权限
        if target_user.role != "admin":
            if not has_permission(
                target_user.id,
                "workspace.tickets_execute",
                request.app.state.config.USER_PERMISSIONS,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Target user doesn't have ticket execution permission"
                )
        
        # 更新工单分配和任务详情
        updates = {
            "assigned_to": form_data.assigned_to,
            "assigned_to_name": target_user.name,
            "status": "in_progress",  # 分配后自动设置为进行中
            "task_requirements": form_data.task_requirements,
            "completion_criteria": form_data.completion_criteria,
            "task_deadline": form_data.task_deadline,
            "task_priority": form_data.task_priority,
            "required_files": form_data.required_files,
            "required_text": form_data.required_text,
            "required_images": form_data.required_images,
            "delivery_instructions": form_data.delivery_instructions,
            "completion_status": "pending",  # 初始状态为待完成
        }
        
        updated_ticket = Tickets.update_ticket(ticket_id, updates)
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign ticket"
            )
        
        # 添加任务分配记录到评论
        assignment_comment_content = f"工单已分配给 {target_user.name}\n\n"
        
        if form_data.task_requirements:
            assignment_comment_content += f"**任务要求：**\n{form_data.task_requirements}\n\n"
        
        if form_data.completion_criteria:
            assignment_comment_content += f"**完成标准：**\n{form_data.completion_criteria}\n\n"
        
        if form_data.task_deadline:
            deadline_str = datetime.fromtimestamp(form_data.task_deadline).strftime('%Y-%m-%d %H:%M:%S')
            assignment_comment_content += f"**截止时间：** {deadline_str}\n\n"
        
        if form_data.task_priority:
            assignment_comment_content += f"**任务优先级：** {form_data.task_priority}\n\n"
        
        if form_data.reason:
            assignment_comment_content += f"**分配原因：** {form_data.reason}"
        
        assignment_comment = TicketComment(
            id=str(uuid.uuid4()),
            content=assignment_comment_content,
            author_id=user.id,
            author_name=user.name,
            is_internal=True,
            created_at=int(time.time()),
        )
        Tickets.add_comment(ticket_id, assignment_comment)
        
        # 发送通知
        try:
            await notification_service.notify_ticket_assigned(updated_ticket, target_user.name)
        except Exception as e:
            log.warning(f"Failed to send assignment notification: {e}")
        
        return {"message": f"Ticket assigned to {target_user.name} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{ticket_id}/transfer")
async def transfer_ticket(
    request: Request,
    ticket_id: str,
    form_data: TransferTicketForm,
    user=Depends(get_admin_user)
):
    """转派工单给其他管理员 (admin only)"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # 验证目标管理员是否存在
        target_admin = Users.get_user_by_id(form_data.assigned_to)
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target admin not found"
            )
        
        # 检查是否是转派给自己
        if form_data.assigned_to == ticket.assigned_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer ticket to the same admin"
            )
        
        # 记录原分配人
        original_assignee = ticket.assigned_to_name or "未分配"
        
        # 更新工单分配
        updates = {
            "assigned_to": form_data.assigned_to,
            "assigned_to_name": target_admin.name,
        }
        
        updated_ticket = Tickets.update_ticket(ticket_id, updates)
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to transfer ticket"
            )
        
        # 添加转派记录到评论
        transfer_comment = TicketComment(
            id=str(uuid.uuid4()),
            content=f"工单已从 {original_assignee} 转派给 {target_admin.name}。转派原因：{form_data.reason}",
            author_id=user.id,
            author_name=user.name,
            is_internal=True,
            created_at=int(time.time()),
        )
        Tickets.add_comment(ticket_id, transfer_comment)
        
        # 发送通知
        try:
            await notification_service.notify_ticket_transferred(updated_ticket, original_assignee, target_admin.name)
        except Exception as e:
            log.warning(f"Failed to send transfer notification: {e}")
        
        return {"message": f"Ticket transferred to {target_admin.name} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error transferring ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )




############################
# Ticket Configuration API
############################

class TicketConfigRequest(BaseModel):
    enabled: bool
    model_id: str
    system_prompt: str


class TicketConfigResponse(BaseModel):
    enabled: bool
    model_id: str
    system_prompt: str


@router.get("/config", response_model=TicketConfigResponse)
async def get_ticket_config(user=Depends(get_admin_user)):
    """获取工单配置 (admin only)"""
    try:
        # 从数据库获取配置
        config = TicketConfigs.get_config()
        
        if not config:
            # 如果数据库中没有配置，返回默认配置
            config = TicketConfigs.get_default_config()
            # 保存默认配置到数据库
            TicketConfigs.save_config(config.model_dump())
        
        return TicketConfigResponse(
            enabled=config.enabled,
            model_id=config.model_id,
            system_prompt=config.system_prompt
        )
        
    except Exception as e:
        log.error(f"Error getting ticket config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket config"
        )

############################
# Task Delivery APIs
############################

class TaskDeliveryForm(BaseModel):
    delivery_text: Optional[str] = None  # 提交的文字说明
    completion_notes: Optional[str] = None  # 完成说明
    # 文件信息将通过multipart form data传递


@router.post("/{ticket_id}/deliver")
async def deliver_task(
    request: Request,
    ticket_id: str,
    delivery_text: Optional[str] = Form(None),
    completion_notes: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    images: List[UploadFile] = File(None),
    user=Depends(get_verified_user)
):
    """提交任务交付 (assigned user only)"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # 检查用户是否有权限提交交付
        if ticket.assigned_to != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only assigned user can deliver this task"
            )
        
        # 检查任务是否已完成
        if ticket.completion_status == "verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task already completed and verified"
            )
        
        # 处理文件上传
        delivery_files = []
        delivery_images = []
        
        # 处理普通文件（实际上传到文件服务，保存file_id以供下载/预览）
        if files:
            for file in files:
                if file.filename:
                    try:
                        # 延迟导入以避免循环依赖
                        from open_webui.routers.files import upload_file_handler

                        metadata = {
                            "ticket_id": ticket_id,
                            "delivery_type": "file",
                            "user_id": user.id,
                        }

                        file_item = upload_file_handler(
                            request,
                            file=file,
                            metadata=metadata,
                            process=False,
                            user=user,
                            background_tasks=None,
                        )

                        # 兼容FileModel或dict两种返回
                        fi = file_item if isinstance(file_item, dict) else file_item.model_dump()
                        meta = fi.get("meta", {}) or {}

                        delivery_files.append(
                            {
                                "id": fi.get("id"),
                                "name": fi.get("filename") or file.filename,
                                "size": meta.get("size", 0),
                                "type": meta.get("content_type", file.content_type or "application/octet-stream"),
                                # 不直接拼接受保护的下载URL，前端通过文件ID携带认证头拉取
                                "url": None,
                            }
                        )
                    except Exception as e:
                        log.warning(f"Failed to upload delivery file {file.filename}: {e}")
        
        # 处理图片文件（实际上传）
        if images:
            for image in images:
                if image.filename:
                    try:
                        from open_webui.routers.files import upload_file_handler

                        metadata = {
                            "ticket_id": ticket_id,
                            "delivery_type": "image",
                            "user_id": user.id,
                        }

                        file_item = upload_file_handler(
                            request,
                            file=image,
                            metadata=metadata,
                            process=False,
                            user=user,
                            background_tasks=None,
                        )

                        fi = file_item if isinstance(file_item, dict) else file_item.model_dump()
                        meta = fi.get("meta", {}) or {}

                        delivery_images.append(
                            {
                                "id": fi.get("id"),
                                "name": fi.get("filename") or image.filename,
                                "size": meta.get("size", 0),
                                "type": meta.get("content_type", image.content_type or "image/*"),
                                "url": None,
                            }
                        )
                    except Exception as e:
                        log.warning(f"Failed to upload delivery image {image.filename}: {e}")
        
        # 更新交付信息
        updates = {
            "delivery_files": delivery_files if delivery_files else None,
            "delivery_text": delivery_text,
            "delivery_images": delivery_images if delivery_images else None,
            "completion_notes": completion_notes,
            "completion_status": "submitted",  # 状态改为已提交
            "status": "resolved",  # 工单状态自动更新为已解决
            "updated_at": int(time.time())
        }
        
        updated_ticket = Tickets.update_ticket(ticket_id, updates)
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit delivery"
            )
        
        # 添加交付记录到评论
        delivery_comment_content = f"任务交付已提交，工单状态已自动更新为已解决\n\n"
        
        if delivery_text:
            delivery_comment_content += f"**文字说明：**\n{delivery_text}\n\n"
        
        if completion_notes:
            delivery_comment_content += f"**完成说明：**\n{completion_notes}\n\n"
        
        if delivery_files:
            delivery_comment_content += f"**提交文件：**\n"
            for file_info in delivery_files:
                delivery_comment_content += f"- {file_info.get('name', 'Unknown file')}\n"
            delivery_comment_content += "\n"
        
        if delivery_images:
            delivery_comment_content += f"**提交图片：**\n"
            for img_info in delivery_images:
                delivery_comment_content += f"- {img_info.get('name', 'Unknown image')}\n"
            delivery_comment_content += "\n"
        
        delivery_comment = TicketComment(
            id=str(uuid.uuid4()),
            content=delivery_comment_content,
            author_id=user.id,
            author_name=user.name,
            is_internal=False,
            created_at=int(time.time())
        )
        
        Tickets.add_comment(ticket_id, delivery_comment)
        
        return {"message": "Task delivery submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error delivering task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


class TaskVerificationForm(BaseModel):
    verified: bool  # True: 通过验证, False: 拒绝
    verification_notes: Optional[str] = None  # 验证说明
    verification_score: Optional[int] = None  # 验证评分 (0-100)
    verification_checklist: Optional[list] = None  # 验证检查清单


@router.post("/{ticket_id}/verify")
async def verify_task_completion(
    request: Request,
    ticket_id: str,
    form_data: TaskVerificationForm,
    user=Depends(get_admin_user)
):
    """验证任务完成情况 (admin only)"""
    try:
        ticket = Tickets.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # 检查任务是否已提交
        if ticket.completion_status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task has not been submitted for verification"
            )
        
        # 更新验证状态
        new_status = "verified" if form_data.verified else "rejected"
        updates = {
            "completion_status": new_status,
            "completion_notes": form_data.verification_notes,
            "updated_at": int(time.time())
        }
        
        # 添加验证评分和检查清单
        if form_data.verification_score is not None:
            updates["verification_score"] = form_data.verification_score
        
        if form_data.verification_checklist:
            updates["verification_checklist"] = form_data.verification_checklist
        
        # 如果验证通过，更新工单状态为已解决
        if form_data.verified:
            updates["status"] = "resolved"
            updates["resolved_at"] = int(time.time())
        
        updated_ticket = Tickets.update_ticket(ticket_id, updates)
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify task completion"
            )
        
        # 添加验证记录到评论
        verification_comment_content = f"任务验证{'通过' if form_data.verified else '未通过'}\n\n"
        
        # 添加验证评分
        if form_data.verification_score is not None:
            verification_comment_content += f"**验证评分：** {form_data.verification_score}%\n\n"
        
        # 添加检查清单
        if form_data.verification_checklist:
            verification_comment_content += f"**检查清单：**\n"
            for item in form_data.verification_checklist:
                status = "✅" if item.get('checked', False) else "❌"
                verification_comment_content += f"- {status} {item.get('label', 'Unknown')}\n"
            verification_comment_content += "\n"
        
        if form_data.verification_notes:
            verification_comment_content += f"**验证说明：**\n{form_data.verification_notes}\n\n"
        
        verification_comment = TicketComment(
            id=str(uuid.uuid4()),
            content=verification_comment_content,
            author_id=user.id,
            author_name=user.name,
            is_internal=True,
            created_at=int(time.time())
        )
        
        Tickets.add_comment(ticket_id, verification_comment)
        
        return {"message": f"Task verification {'passed' if form_data.verified else 'failed'}"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error verifying task completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
