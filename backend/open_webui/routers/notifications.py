import logging
import time
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user
from open_webui.services.notification_service import notification_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


class EmailConfig(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str


class WebhookConfig(BaseModel):
    webhook_url: str


class NotificationConfig(BaseModel):
    email: Optional[EmailConfig] = None
    webhook: Optional[WebhookConfig] = None


############################
# Configure Email Notifications
############################

@router.post("/email")
async def configure_email_notifications(
    request: Request,
    config: EmailConfig,
    user=Depends(get_admin_user)
):
    """Configure email notification settings"""
    try:
        notification_service.configure_email(
            smtp_server=config.smtp_server,
            smtp_port=config.smtp_port,
            smtp_username=config.smtp_username,
            smtp_password=config.smtp_password,
            from_email=config.from_email
        )
        
        return {"message": "Email notification configuration updated successfully"}
        
    except Exception as e:
        log.error(f"Error configuring email notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure email notifications"
        )


############################
# Configure Webhook Notifications
############################

@router.post("/webhook")
async def configure_webhook_notifications(
    request: Request,
    config: WebhookConfig,
    user=Depends(get_admin_user)
):
    """Configure webhook notification settings"""
    try:
        notification_service.configure_webhook(config.webhook_url)
        
        return {"message": "Webhook notification configuration updated successfully"}
        
    except Exception as e:
        log.error(f"Error configuring webhook notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure webhook notifications"
        )


############################
# Test Notifications
############################

@router.post("/test/email")
async def test_email_notification(
    request: Request,
    user=Depends(get_admin_user)
):
    """Test email notification configuration"""
    try:
        # Send test email to admin
        admin_emails = notification_service.get_admin_emails()
        if not admin_emails:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No admin email addresses found"
            )
        
        success = notification_service.send_email_notification(
            admin_emails,
            "Test Notification - Open WebUI",
            "This is a test email to verify email notification configuration.",
            is_html=False
        )
        
        if success:
            return {"message": "Test email sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error testing email notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test email notification"
        )


@router.post("/test/webhook")
async def test_webhook_notification(
    request: Request,
    user=Depends(get_admin_user)
):
    """Test webhook notification configuration"""
    try:
        test_payload = {
            "event": "test",
            "message": "This is a test webhook notification",
            "timestamp": int(time.time())
        }
        
        success = await notification_service.send_webhook_notification(test_payload)
        
        if success:
            return {"message": "Test webhook sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test webhook"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error testing webhook notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test webhook notification"
        )
