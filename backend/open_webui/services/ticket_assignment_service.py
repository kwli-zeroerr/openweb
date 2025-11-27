import logging
import random
from typing import Optional, List, Dict, Any
from open_webui.models.users import Users
from open_webui.models.tickets import Tickets, TicketModel, TicketCategory, TicketPriority
from open_webui.models.groups import Groups
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class TicketAssignmentService:
    """工单自动派发服务"""
    
    def __init__(self):
        # 工单分类与管理员角色的映射
        self.category_assignment_rules = {
            TicketCategory.BUG: {
                "preferred_roles": ["admin", "developer", "technical_support"],
                "required_permissions": ["workspace.tickets_execute"],
                "fallback_role": "admin"
            },
            TicketCategory.TECHNICAL_SUPPORT: {
                "preferred_roles": ["admin", "technical_support"],
                "required_permissions": ["workspace.tickets_execute"],
                "fallback_role": "admin"
            },
            TicketCategory.FEATURE_REQUEST: {
                "preferred_roles": ["admin", "product_manager"],
                "required_permissions": ["workspace.tickets_execute"],
                "fallback_role": "admin"
            },
            TicketCategory.GENERAL_INQUIRY: {
                "preferred_roles": ["admin", "customer_service"],
                "required_permissions": ["workspace.tickets_execute"],
                "fallback_role": "admin"
            },
            TicketCategory.OTHER: {
                "preferred_roles": ["admin"],
                "required_permissions": ["workspace.tickets_execute"],
                "fallback_role": "admin"
            }
        }
        
        # 优先级权重（优先级越高，分配给经验更丰富的管理员）
        self.priority_weights = {
            TicketPriority.LOW: 1,
            TicketPriority.MEDIUM: 2,
            TicketPriority.HIGH: 3,
            TicketPriority.URGENT: 4
        }

    async def auto_assign_ticket(self, ticket: TicketModel) -> Optional[str]:
        """
        自动派发工单给合适的管理员
        
        Args:
            ticket: 工单对象
            
        Returns:
            被分配的管理员ID，如果无法分配则返回None
        """
        try:
            # 获取可用的管理员列表
            available_admins = self._get_available_admins(ticket)
            
            if not available_admins:
                log.warning(f"No available admins for ticket {ticket.id}")
                return None
            
            # 根据工单特征选择最佳管理员
            assigned_admin = self._select_best_admin(ticket, available_admins)
            
            if assigned_admin:
                # 更新工单分配
                success = self._assign_ticket_to_admin(ticket.id, assigned_admin["id"], assigned_admin["name"])
                
                if success:
                    log.info(f"Auto-assigned ticket {ticket.id} to admin {assigned_admin['name']} ({assigned_admin['id']})")
                    return assigned_admin["id"]
                else:
                    log.error(f"Failed to assign ticket {ticket.id} to admin {assigned_admin['id']}")
            
            return None
            
        except Exception as e:
            log.error(f"Error in auto-assignment for ticket {ticket.id}: {e}")
            return None

    def _get_available_admins(self, ticket: TicketModel) -> List[Dict[str, Any]]:
        """
        获取可用的管理员列表
        
        Args:
            ticket: 工单对象
            
        Returns:
            可用管理员列表
        """
        try:
            # 获取所有管理员用户
            all_users_result = Users.get_users()
            all_users = all_users_result.get('data', [])
            admins = []
            
            for user in all_users:
                if user.role == "admin":
                    # 检查用户是否在线（简单检查，可以根据需要扩展）
                    is_online = self._is_user_available(user.id)
                    
                    # 获取用户的工作负载
                    workload = self._get_user_workload(user.id)
                    
                    # 获取用户专业领域
                    expertise = self._get_user_expertise(user.id, ticket)
                    
                    admins.append({
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "is_online": is_online,
                        "workload": workload,
                        "expertise": expertise,
                        "role": user.role
                    })
            
            # 获取支持团队成员
            support_members = self._get_support_group_members(ticket)
            admins.extend(support_members)
            
            # 去重
            unique_admins = {}
            for admin in admins:
                if admin["id"] not in unique_admins:
                    unique_admins[admin["id"]] = admin
            
            return list(unique_admins.values())
            
        except Exception as e:
            log.error(f"Error getting available admins: {e}")
            return []

    def _get_support_group_members(self, ticket: TicketModel) -> List[Dict[str, Any]]:
        """
        获取有工单执行权限的用户
        
        Args:
            ticket: 工单对象
            
        Returns:
            有工单执行权限的用户列表
        """
        try:
            from open_webui.utils.access_control import has_permission
            from open_webui.config import DEFAULT_USER_PERMISSIONS
            
            # 获取所有用户
            all_users_result = Users.get_users()
            all_users = all_users_result.get('data', [])
            
            members = []
            for user in all_users:
                # 检查用户是否有工单执行权限
                if has_permission(user.id, "workspace.tickets_execute", DEFAULT_USER_PERMISSIONS):
                    members.append({
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "is_online": self._is_user_available(user.id),
                        "workload": self._get_user_workload(user.id),
                        "expertise": self._get_user_expertise(user.id, ticket),
                        "role": user.role
                    })
            
            return members
            
        except Exception as e:
            log.error(f"Error getting support group members: {e}")
            return []

    def _select_best_admin(self, ticket: TicketModel, admins: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        选择最佳管理员
        
        Args:
            ticket: 工单对象
            admins: 可用管理员列表
            
        Returns:
            选中的管理员
        """
        try:
            if not admins:
                return None
            
            # 获取工单分类的分配规则
            category_rules = self.category_assignment_rules.get(ticket.category, {})
            preferred_roles = category_rules.get("preferred_roles", ["admin"])
            
            # 计算每个管理员的得分
            scored_admins = []
            for admin in admins:
                score = self._calculate_admin_score(admin, ticket, preferred_roles)
                scored_admins.append((admin, score))
            
            # 按得分排序（得分越高越好）
            scored_admins.sort(key=lambda x: x[1], reverse=True)
            
            # 选择得分最高的管理员
            if scored_admins:
                return scored_admins[0][0]
            
            return None
            
        except Exception as e:
            log.error(f"Error selecting best admin: {e}")
            return None

    def _calculate_admin_score(self, admin: Dict[str, Any], ticket: TicketModel, preferred_roles: List[str]) -> float:
        """
        计算管理员得分
        
        Args:
            admin: 管理员信息
            ticket: 工单对象
            preferred_roles: 首选角色列表
            
        Returns:
            管理员得分
        """
        try:
            score = 0.0
            
            # 基础分数
            score += 10.0
            
            # 角色匹配分数
            if admin["role"] in preferred_roles:
                score += 20.0
            
            # 在线状态分数
            if admin["is_online"]:
                score += 15.0
            
            # 工作负载分数（工作负载越低分数越高）
            workload_score = max(0, 20.0 - admin["workload"] * 2)
            score += workload_score
            
            # 专业领域匹配分数
            expertise_score = admin["expertise"] * 10
            score += expertise_score
            
            # 优先级权重调整
            priority_weight = self.priority_weights.get(ticket.priority, 2)
            score *= (1 + priority_weight * 0.1)
            
            # AI生成工单的额外分数（优先分配给经验丰富的管理员）
            if ticket.is_ai_generated:
                score += 5.0
            
            return score
            
        except Exception as e:
            log.error(f"Error calculating admin score: {e}")
            return 0.0

    def _is_user_available(self, user_id: str) -> bool:
        """
        检查用户是否可用（在线）
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否可用
        """
        try:
            # 这里可以实现更复杂的在线状态检查
            # 目前简单返回True，表示所有用户都可用
            return True
        except Exception as e:
            log.error(f"Error checking user availability: {e}")
            return False

    def _get_user_workload(self, user_id: str) -> int:
        """
        获取用户当前工作负载
        
        Args:
            user_id: 用户ID
            
        Returns:
            工作负载数量
        """
        try:
            # 获取用户当前处理的工单数量
            result = Tickets.get_tickets(
                assigned_to=user_id,
                status="open",  # 只计算未关闭的工单
                limit=1000
            )
            return result.get("total", 0)
        except Exception as e:
            log.error(f"Error getting user workload: {e}")
            return 0

    def _get_user_expertise(self, user_id: str, ticket: TicketModel) -> float:
        """
        获取用户对特定工单类型的专业程度
        
        Args:
            user_id: 用户ID
            ticket: 工单对象
            
        Returns:
            专业程度分数 (0-1)
        """
        try:
            # 获取用户历史处理的类似工单数量
            result = Tickets.get_tickets(
                assigned_to=user_id,
                category=ticket.category,
                limit=1000
            )
            
            # 基于历史处理数量计算专业程度
            historical_count = result.get("total", 0)
            expertise = min(1.0, historical_count / 10.0)  # 最多10个工单达到满分
            
            return expertise
            
        except Exception as e:
            log.error(f"Error getting user expertise: {e}")
            return 0.0

    def _assign_ticket_to_admin(self, ticket_id: str, admin_id: str, admin_name: str) -> bool:
        """
        将工单分配给管理员
        
        Args:
            ticket_id: 工单ID
            admin_id: 管理员ID
            admin_name: 管理员姓名
            
        Returns:
            是否分配成功
        """
        try:
            # 更新工单分配信息
            updates = {
                "assigned_to": admin_id,
                "assigned_to_name": admin_name,
                "status": "in_progress"  # 自动设置为进行中状态
            }
            
            updated_ticket = Tickets.update_ticket(ticket_id, updates)
            return updated_ticket is not None
            
        except Exception as e:
            log.error(f"Error assigning ticket to admin: {e}")
            return False

    def get_assignment_stats(self) -> Dict[str, Any]:
        """
        获取工单分配统计信息
        
        Returns:
            统计信息
        """
        try:
            # 获取所有工单
            all_tickets = Tickets.get_tickets(limit=10000)
            tickets = all_tickets.get("tickets", [])
            
            # 统计信息
            stats = {
                "total_tickets": len(tickets),
                "assigned_tickets": len([t for t in tickets if t.assigned_to]),
                "unassigned_tickets": len([t for t in tickets if not t.assigned_to]),
                "ai_generated_tickets": len([t for t in tickets if t.is_ai_generated]),
                "assignment_by_category": {},
                "assignment_by_admin": {}
            }
            
            # 按分类统计
            for ticket in tickets:
                category = ticket.category
                if category not in stats["assignment_by_category"]:
                    stats["assignment_by_category"][category] = {
                        "total": 0,
                        "assigned": 0,
                        "unassigned": 0
                    }
                
                stats["assignment_by_category"][category]["total"] += 1
                if ticket.assigned_to:
                    stats["assignment_by_category"][category]["assigned"] += 1
                else:
                    stats["assignment_by_category"][category]["unassigned"] += 1
            
            # 按管理员统计
            for ticket in tickets:
                if ticket.assigned_to:
                    admin_id = ticket.assigned_to
                    if admin_id not in stats["assignment_by_admin"]:
                        stats["assignment_by_admin"][admin_id] = {
                            "name": ticket.assigned_to_name,
                            "count": 0
                        }
                    stats["assignment_by_admin"][admin_id]["count"] += 1
            
            return stats
            
        except Exception as e:
            log.error(f"Error getting assignment stats: {e}")
            return {}


# 创建全局实例
ticket_assignment_service = TicketAssignmentService()
