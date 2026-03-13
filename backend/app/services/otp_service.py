"""
OTP Service - Generate, store, and verify OTP using Redis
"""
import random
import string
import os
from typing import Tuple, Optional
from dotenv import load_dotenv
from app.core.logger import get_logger
from app.services.redis_service import redis_service

load_dotenv()
logger = get_logger(__name__)


class OTPService:
    """OTP generation and verification"""
    
    def __init__(self):
        self.otp_length = int(os.getenv("OTP_LENGTH", 6))
        self.otp_expiry = int(os.getenv("OTP_EXPIRY_SECONDS", 300))  # 5 minutes
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        otp = ''.join(random.choices(string.digits, k=self.otp_length))
        return otp
    
    def store_otp(self, key: str, otp: str, ttl: Optional[int] = None) -> bool:
        """
        Store OTP in Redis with auto-expiry
        Key is provided by the caller (supports multiple flows)
        """
        expiry = ttl if ttl is not None else self.otp_expiry
        success = redis_service.set_with_expiry(key, otp, expiry_seconds=expiry)
        if success:
            logger.info("OTP stored in Redis: %s", key)
        return success
    
    def verify_otp(self, key: str, otp: str) -> bool:
        """Verify OTP from Redis"""
        stored_otp = redis_service.get(key)
        
        if not stored_otp:
            logger.warning("OTP expired or not found: %s", key)
            return False
        
        is_valid = stored_otp == otp
        if is_valid:
            logger.info("OTP verified: %s", key)
        else:
            logger.warning("OTP mismatch: %s", key)
        
        return is_valid
    
    def clear_otp(self, key: str) -> bool:
        """Delete OTP from Redis after verification"""
        success = redis_service.delete(key)
        if success:
            logger.info("OTP cleared: %s", key)
        return success
    
    def get_remaining_time(self, key: str) -> Optional[int]:
        """Get remaining TTL for OTP in seconds"""
        return redis_service.get_ttl(key)


otp_service = OTPService()
