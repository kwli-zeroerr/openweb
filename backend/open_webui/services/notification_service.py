import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os
import time
import hmac
import hashlib
import base64
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, quote_plus
import asyncio
import aiohttp

from open_webui.models.users import Users
from open_webui.models.groups import Groups
from open_webui.env import CONFIG_JSON
from open_webui.models.tickets import TicketModel
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Simplest hard-coded DingTalk config per user request
DINGTALK_ACCESS_TOKEN = "b117c763001b1d02902d18fcf7f8877369e0ab33bb10122ba35b4003da24994b"
DINGTALK_SECRET = "SEC54f185a76ebb75c491497bc02155efcc0dfc3763ac5de2e2ab46d4ede8d8fce9"


class NotificationService:
    def __init__(self):
        self.smtp_server = None
        self.smtp_port = None
        self.smtp_username = None
        self.smtp_password = None
        self.from_email = None
        self.webhook_url = None
        # Optional: DingTalk signing secret, read from env if provided
        self.webhook_secret = (
            os.environ.get("DINGTALK_WEBHOOK_SECRET")
            or os.environ.get("WEBHOOK_SIGNING_SECRET")
            or CONFIG_JSON.get("DINGTALK_WEBHOOK_SECRET")
            or CONFIG_JSON.get("WEBHOOK_SIGNING_SECRET")
        )
        # Hardcoded fallbacks (as requested). Only used if未配置。
        self._fallback_dingtalk_url = (
            CONFIG_JSON.get("DINGTALK_WEBHOOK_URL")
            or CONFIG_JSON.get("WEBHOOK_URL")
            or "https://oapi.dingtalk.com/robot/send?access_token=b117c763001b1d02902d18fcf7f8877369e0ab33bb10122ba35b4003da24994b"
        )
        self._fallback_dingtalk_secret = (
            self.webhook_secret
            or "SEC54f185a76ebb75c491497bc02155efcc0dfc3763ac5de2e2ab46d4ede8d8fce9"
        )
        
    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str
    ):
        """Configure email notification settings"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        
    def configure_webhook(self, webhook_url: str):
        """Configure webhook notification settings"""
        self.webhook_url = webhook_url
        # Allow updating secret from env at runtime
        self.webhook_secret = (
            os.environ.get("DINGTALK_WEBHOOK_SECRET")
            or os.environ.get("WEBHOOK_SIGNING_SECRET")
            or CONFIG_JSON.get("DINGTALK_WEBHOOK_SECRET")
            or CONFIG_JSON.get("WEBHOOK_SIGNING_SECRET")
        )
        if not self.webhook_secret:
            self.webhook_secret = self._fallback_dingtalk_secret
        
    def get_admin_emails(self) -> List[str]:
        """Get email addresses of all admin users"""
        try:
            admin_users = Users.get_users_by_user_ids(
                [user.id for user in Users.get_users()["users"] if user.role == "admin"]
            )
            return [user.email for user in admin_users if user.email]
        except Exception as e:
            log.error(f"Error getting admin emails: {e}")
            return []

    def get_group_emails_by_name(self, group_name: str) -> List[str]:
        """Get email addresses for users in a group by group name"""
        try:
            groups = Groups.get_groups()
            group = next((g for g in groups if g.name == group_name), None)
            if not group:
                return []
            users = Users.get_users_by_user_ids(group.user_ids or [])
            return [user.email for user in users if user.email]
        except Exception as e:
            log.error(f"Error getting emails for group {group_name}: {e}")
            return []

    def get_user_email_by_name(self, name: str) -> Optional[str]:
        """Try to find a user by name and return email if present"""
        try:
            result = Users.get_users({"query": name})
            for u in result.get("users", []):
                if u.name == name and u.email:
                    return u.email
            return None
        except Exception:
            return None
            
    def send_email_notification(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """Send email notification"""
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password, self.from_email]):
            log.warning("Email configuration incomplete, skipping email notification")
            return False
            
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
                
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            log.info(f"Email notification sent to {len(to_emails)} recipients")
            return True
            
        except Exception as e:
            log.error(f"Error sending email notification: {e}")
            return False
            
    async def send_webhook_notification(self, data: dict) -> bool:
        """Minimal DingTalk sender: fixed token/secret, simple text."""
        try:
            ts = str(int(time.time() * 1000))
            string_to_sign = f"{ts}\n{DINGTALK_SECRET}"
            h = hmac.new(DINGTALK_SECRET.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
            sign = quote_plus(base64.b64encode(h).decode("utf-8"))
            url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_ACCESS_TOKEN}&timestamp={ts}&sign={sign}"

            # Build markdown with required fields
            t = data.get("ticket") or {}
            title = t.get('title', '')
            # normalize enums to readable
            def _norm(v: str) -> str:
                s = str(v)
                if '.' in s:
                    s = s.split('.')[-1]
                return s.lower()
            status_map = {
                'open': '待处理',
                'in_progress': '处理中',
                'resolved': '已解决',
                'closed': '已关闭',
            }
            priority_map = {
                'low': '低',
                'medium': '中',
                'high': '高',
                'urgent': '紧急',
            }
            category_map = {
                'bug': 'Bug 报告',
                'feature_request': '功能请求',
                'general_inquiry': '一般咨询',
                'technical_support': '技术支持',
                'other': '其他',
            }
            status = status_map.get(_norm(t.get('status','')), str(t.get('status','')))
            assignee = t.get('assigned_to_name') or t.get('assigned_to') or 'Don'
            priority = priority_map.get(_norm(t.get('priority','')), str(t.get('priority','')))
            category = category_map.get(_norm(t.get('category','')), str(t.get('category','')))
            submitter = f"{t.get('user_name','')}" + (f" ({t.get('user_email')})" if t.get('user_email') else '')
            # format created_at
            created_at = t.get('created_at')
            try:
                ts = int(created_at)
                from datetime import datetime
                created_at_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            except Exception:
                created_at_str = str(created_at or '')
            desc = (t.get('description') or '').strip()
            
            # 如果是AI生成的工单，尝试提取用户反馈评论
            user_feedback = ""
            if t.get('is_ai_generated') and t.get('ai_analysis'):
                try:
                    import json
                    analysis = t.get('ai_analysis')
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)
                    
                    # 优先从feedback_data.data.comment中获取用户反馈评论
                    if analysis.get('feedback_data') and analysis['feedback_data'].get('data'):
                        feedback_data = analysis['feedback_data']['data']
                        comment = feedback_data.get('comment')
                        reason = feedback_data.get('reason')
                        
                        if comment and comment.strip():
                            user_feedback = f"用户反馈：{comment.strip()}"
                        elif reason and reason.strip():
                            user_feedback = f"反馈原因：{reason.strip()}"
                        else:
                            # 如果没有评论和原因，说明不应该生成工单
                            user_feedback = "用户对AI回复不满意（无具体评论）"
                    else:
                        user_feedback = "用户对AI回复不满意"
                except Exception as e:
                    log.warning(f"Failed to extract user feedback from AI analysis: {e}")
                    user_feedback = "用户对AI回复不满意"
            
            # 如果有用户反馈，优先显示反馈内容
            if user_feedback:
                content_info = user_feedback
            else:
                content_info = desc
                
            # 只保留前500字符，避免过长
            if len(content_info) > 500:
                content_info = content_info[:500] + '…'

            md_title = f"工单通知｜{title or '新工单'}"
            md_text = (
                "工单（包含关键词：工单）\n\n"  # 固定关键词以便通过钉钉关键词校验
                f"- **标题**：{title}\n"
                f"- **状态**：{status}\n"
                f"- **代办人**：{assignee}\n"
                f"- **优先级**：{priority}\n"
                f"- **提交人**：{submitter}\n"
                f"- **创建时间**：{created_at_str}\n"
                f"- **工单类型**：{category}\n"
                f"- **内容信息**：{content_info}"
            )
            # Add comment info when present (chat under ticket)
            comment = data.get("comment") or {}
            if comment:
                c_content = (str(comment.get("content", "")).strip())
                if len(c_content) > 500:
                    c_content = c_content[:500] + '…'
                c_author = comment.get("author_name") or ""
                c_time = comment.get("created_at")
                try:
                    ts2 = int(c_time)
                    from datetime import datetime
                    c_time_str = datetime.fromtimestamp(ts2).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    c_time_str = str(c_time or '')
                md_text += ("\n\n"
                            "---\n"
                            "**最新评论**\n\n"
                            f"- **评论人**：{c_author}\n"
                            f"- **评论时间**：{c_time_str}\n"
                            f"- **评论内容**：{c_content}")
            payload = {"msgtype": "markdown", "markdown": {"title": md_title, "text": md_text}}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    ok = resp.status == 200
                    msg = await resp.text()
                    if ok:
                        log.info("Webhook notification sent successfully")
                        return True
                    log.error(f"Webhook notification failed: {resp.status} {msg}")
                    return False
        except Exception as e:
            log.error(f"Error sending webhook notification: {e}")
            return False
            
    def create_ticket_email_body(self, ticket: TicketModel) -> str:
        """Create email body for new ticket notification"""
        return f"""
新的问题工单已提交

工单信息：
- 标题: {ticket.title}
- 类型: {ticket.category}
- 优先级: {ticket.priority}
- 状态: {ticket.status}
- 提交者: {ticket.user_name} ({ticket.user_email})
- 创建时间: {ticket.created_at}

问题描述：
{ticket.description}

请登录系统查看和处理此工单。
        """.strip()
        
    def create_ticket_html_body(self, ticket: TicketModel) -> str:
        """Create HTML email body for new ticket notification"""
        return f"""
        <html>
        <body>
            <h2>新的问题工单已提交</h2>
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px;">
                <h3>工单信息</h3>
                <ul>
                    <li><strong>标题:</strong> {ticket.title}</li>
                    <li><strong>类型:</strong> {ticket.category}</li>
                    <li><strong>优先级:</strong> {ticket.priority}</li>
                    <li><strong>状态:</strong> {ticket.status}</li>
                    <li><strong>提交者:</strong> {ticket.user_name} ({ticket.user_email})</li>
                    <li><strong>创建时间:</strong> {ticket.created_at}</li>
                </ul>
                
                <h3>问题描述</h3>
                <div style="background-color: white; padding: 15px; border-radius: 3px; border-left: 4px solid #007bff;">
                    {ticket.description.replace(chr(10), '<br>')}
                </div>
                
                <p style="margin-top: 20px;">
                    <a href="/tickets/{ticket.id}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px;">
                        查看工单详情
                    </a>
                </p>
            </div>
        </body>
        </html>
        """.strip()
        
    def create_webhook_payload(self, ticket: TicketModel, event_type: str) -> dict:
        """Create webhook payload for ticket notification"""
        return {
            "event": event_type,
            "ticket": {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "category": ticket.category,
                "user_id": ticket.user_id,
                "user_name": ticket.user_name,
                "user_email": ticket.user_email,
                "assigned_to": ticket.assigned_to,
                "assigned_to_name": ticket.assigned_to_name,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "tags": ticket.tags or []
            },
            "timestamp": ticket.created_at
        }
        
    async def notify_new_ticket(self, ticket: TicketModel) -> bool:
        """Send notifications for new ticket"""
        success = True
        
        # Collect recipients: admins + specific group + tester (Don)
        recipients: List[str] = []
        recipients += self.get_admin_emails()
        # Notify maintenance knowledge base group
        recipients += self.get_group_emails_by_name("维护知识库成员")
        # Ensure tester Don is included if exists
        don_email = self.get_user_email_by_name("Don")
        if don_email:
            recipients.append(don_email)

        # Deduplicate
        recipients = sorted(list({e for e in recipients if e}))

        if recipients:
            subject = f"新工单: {ticket.title}"
            plain_body = self.create_ticket_email_body(ticket)
            html_body = self.create_ticket_html_body(ticket)
            
            email_success = self.send_email_notification(
                recipients,
                subject,
                plain_body,
                is_html=False
            )
            success = success and email_success
            
        # Send webhook notification (URL will be resolved/fallback internally)
        webhook_payload = self.create_webhook_payload(ticket, "ticket.created")
        webhook_success = await self.send_webhook_notification(webhook_payload)
        success = success and webhook_success
            
        return success
        
    async def notify_ticket_updated(self, ticket: TicketModel) -> bool:
        """Send notifications for ticket update"""
        success = True
        
        # Send webhook notification (URL will be resolved/fallback internally)
        webhook_payload = self.create_webhook_payload(ticket, "ticket.updated")
        webhook_success = await self.send_webhook_notification(webhook_payload)
        success = success and webhook_success
            
        return success
        
    async def notify_ticket_commented(self, ticket: TicketModel, comment: dict) -> bool:
        """Send notifications for ticket comment"""
        success = True
        
        # Send webhook notification (URL will be resolved/fallback internally)
        webhook_payload = self.create_webhook_payload(ticket, "ticket.commented")
        webhook_payload["comment"] = comment
        webhook_success = await self.send_webhook_notification(webhook_payload)
        success = success and webhook_success
            
        return success
        
    async def notify_ticket_assigned(self, ticket: TicketModel, assignee_name: str) -> bool:
        """Send notifications for ticket assignment"""
        success = True
        
        # Send webhook notification
        webhook_payload = self.create_webhook_payload(ticket, "ticket.assigned")
        webhook_payload["assignee"] = assignee_name
        webhook_success = await self.send_webhook_notification(webhook_payload)
        success = success and webhook_success
            
        return success
        
    async def notify_ticket_transferred(self, ticket: TicketModel, from_admin: str, to_admin: str) -> bool:
        """Send notifications for ticket transfer"""
        success = True
        
        # Send webhook notification
        webhook_payload = self.create_webhook_payload(ticket, "ticket.transferred")
        webhook_payload["from_admin"] = from_admin
        webhook_payload["to_admin"] = to_admin
        webhook_success = await self.send_webhook_notification(webhook_payload)
        success = success and webhook_success
            
        return success


# Global notification service instance
notification_service = NotificationService()
