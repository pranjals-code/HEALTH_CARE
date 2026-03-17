"""
Celery configuration and tasks
"""

from celery import Celery
import os
from dotenv import load_dotenv
from app.core.logger import configure_logging, get_logger

load_dotenv()
configure_logging()
logger = get_logger(__name__)

celery_app = Celery(
    "healthcare_system",
    broker=os.getenv(
        "CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1")
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/2")
    ),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def send_otp_sms_task(phone_number: str, otp: str):
    """
    Celery task: Send OTP via SMS in background

    This runs asynchronously when user clicks "Create Profile"
    """
    from app.services.sms_service import sms_service

    logger.info("Celery task sending OTP SMS to %s", phone_number)
    success, message_id = sms_service.send_otp_sms(phone_number, otp)

    return {"success": success, "phone": phone_number, "message_id": message_id}


@celery_app.task
def send_password_reset_sms_task(phone_number: str, otp: str):
    """
    Celery task: Send password reset OTP in background
    """
    from app.services.sms_service import sms_service

    logger.info("Celery task sending password reset OTP SMS to %s", phone_number)
    success, message_id = sms_service.send_password_reset_sms(phone_number, otp)

    return {"success": success, "phone": phone_number, "message_id": message_id}
