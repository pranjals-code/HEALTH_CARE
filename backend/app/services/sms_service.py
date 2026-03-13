"""
SMS Service - Send SMS via Twilio
"""
from twilio.rest import Client
from typing import Tuple
import os
from dotenv import load_dotenv
from app.core.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class SMSService:
    """Twilio SMS service"""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.is_configured = False

        if self.account_sid and self.auth_token and self.twilio_phone:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                self.is_configured = True
                logger.info("Twilio SMS service initialized")
            except Exception as e:
                logger.warning("Twilio initialization error: %s", str(e))
        else:
            logger.warning("Twilio not configured in .env")
    
    def send_otp_sms(self, phone_number: str, otp: str) -> Tuple[bool, str]:
        """Send OTP via SMS for registration"""
        if not self.is_configured:
            return False, "SMS service not configured"
        
        try:
            message = self.client.messages.create(
                body=f"Your Healthcare System verification code is: {otp}\n\nValid for 5 minutes. Do not share.",
                from_=self.twilio_phone,
                to=phone_number
            )
            logger.info("Registration SMS sent to %s | Message: %s", phone_number, message.sid)
            return True, message.sid
        
        except Exception as e:
            error_msg = str(e)
            logger.error("SMS send failed to %s: %s", phone_number, error_msg)
            return False, error_msg
    
    def send_password_reset_sms(self, phone_number: str, otp: str) -> Tuple[bool, str]:
        """Send OTP via SMS for password reset"""
        if not self.is_configured:
            return False, "SMS service not configured"
        
        try:
            message = self.client.messages.create(
                body=f"Your Healthcare System password reset code is: {otp}\n\nValid for 5 minutes. Do not share.",
                from_=self.twilio_phone,
                to=phone_number
            )
            logger.info("Password reset SMS sent to %s | Message: %s", phone_number, message.sid)
            return True, message.sid
        
        except Exception as e:
            error_msg = str(e)
            logger.error("Password reset SMS failed to %s: %s", phone_number, error_msg)
            return False, error_msg
    
    def test_connection(self) -> bool:
        """Test Twilio connection"""
        if not self.is_configured:
            return False
        
        try:
            account = self.client.api.accounts(self.account_sid).fetch()
            logger.info("Twilio connected: %s", account.friendly_name)
            return True
        except Exception as e:
            logger.error("Twilio test failed: %s", str(e))
            return False


sms_service = SMSService()
