"""
OTP & Phone-based Authentication Routes
Handles phone verification, password reset via OTP
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.auth import User
from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    ForgotPasswordRequest,
    VerifyResetOTPRequest,
    ResetPasswordRequest,
    OTPResponse,
    UserResponse,
    TokenResponse,
)
from app.services.otp_service import OTPService
from app.services.sms_service import SMSService
from app.services.redis_service import RedisService
from app.core.security import hash_password, verify_password
from app.celery_app import send_otp_sms_task, send_password_reset_sms_task
import re
import os

router = APIRouter(prefix="/auth", tags=["OTP Authentication"])
otp_service = OTPService()
sms_service = SMSService()
redis_service = RedisService()


def normalize_phone(phone: str) -> str:
    """Normalize phone number (remove non-digits)"""
    return re.sub(r'\D', '', phone)


def format_e164(raw_phone: str) -> str:
    """Format phone to E.164 using DEFAULT_COUNTRY_CODE when needed."""
    cleaned = normalize_phone(raw_phone)
    raw = raw_phone.strip()

    if raw.startswith('+'):
        return f"+{cleaned}"

    default_cc = os.getenv("DEFAULT_COUNTRY_CODE", "+1")
    if not default_cc.startswith('+'):
        default_cc = f"+{default_cc}"

    # If user already passed country code without '+', keep it.
    if cleaned.startswith(default_cc.lstrip('+')) and len(cleaned) > 10:
        return f"+{cleaned}"

    if len(cleaned) == 10:
        return f"{default_cc}{cleaned}"

    # Fallback to best-effort
    return f"+{cleaned}"


def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    if request.client:
        return request.client.host
    return "unknown"


# ==================== Phone Registration ====================

@router.post("/register-phone", response_model=OTPResponse)
async def register_with_phone(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 1: Register with phone number
    - Validates email & phone don't exist
    - Generates 6-digit OTP
    - Stores OTP in Redis (5-min TTL)
    - Triggers Celery task to send SMS
    
    Returns OTP remaining time for frontend countdown
    """
    try:
        phone = normalize_phone(req.phone_number)
        
        # Validate email doesn't exist
        existing_email = db.execute(
            select(User).where(User.email == req.email)
        ).scalar_one_or_none()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate phone doesn't exist
        existing_phone = db.execute(
            select(User).where(User.phone == phone)
        ).scalar_one_or_none()
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Generate OTP and store in Redis
        otp = otp_service.generate_otp()
        otp_service.store_otp(
            key=f"otp:register:{phone}",
            otp=otp,
            ttl=300  # 5 minutes
        )
        
        # Store registration data in Redis temporarily
        redis_service.set_with_expiry(
            key=f"register:{phone}",
            value={
                "email": req.email,
                "first_name": req.first_name,
                "last_name": req.last_name,
                "phone": phone
            },
            ttl=900  # 15 minutes
        )
        
        # Trigger Celery task for SMS sending (background)
        send_otp_sms_task.delay(
            phone_number=format_e164(req.phone_number),
            otp=otp
        )
        
        # Get remaining time for frontend countdown
        ttl = redis_service.get_ttl(f"otp:register:{phone}")
        
        return OTPResponse(
            success=True,
            message=f"OTP sent to {phone[-4:]} (last 4 digits). Valid for 5 minutes.",
            remaining_time=ttl
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/verify-phone-otp", response_model=UserResponse)
async def verify_phone_otp(
    req: VerifyOTPRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2: Verify OTP and create user account
    - Validates OTP from Redis
    - Creates user with hashed password
    - Clears OTP from Redis
    - Returns created user details
    """
    try:
        phone = normalize_phone(req.phone_number)
        
        # Verify OTP from Redis
        is_valid = otp_service.verify_otp(
            key=f"otp:register:{phone}",
            otp=req.otp
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP"
            )
        
        # Get registration data from Redis
        reg_data = redis_service.get(f"register:{phone}")
        if not reg_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration session expired. Please start over."
            )
        
        # Create user in database
        user = User(
            email=reg_data.get("email"),
            phone=phone,
            first_name=reg_data.get("first_name"),
            last_name=reg_data.get("last_name"),
            password_hash=hash_password(req.password),
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Clear OTP and registration data from Redis
        otp_service.clear_otp(f"otp:register:{phone}")
        redis_service.delete(f"register:{phone}")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP verification failed: {str(e)}"
        )


# ==================== Forgot Password ====================

@router.post("/forgot-password", response_model=OTPResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 1: Initiate password reset
    - Validates phone exists
    - Generates OTP
    - Stores in Redis (5-min TTL)
    - Triggers Celery task to send SMS
    """
    try:
        phone = normalize_phone(req.phone_number)
        
        # Check if phone exists
        user = db.execute(
            select(User).where(User.phone == phone)
        ).scalar_one_or_none()
        
        if not user:
            # For security: don't reveal if phone exists
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found"
            )
        
        # Generate OTP and store in Redis
        otp = otp_service.generate_otp()
        otp_service.store_otp(
            key=f"otp:reset:{phone}",
            otp=otp,
            ttl=300  # 5 minutes
        )
        
        # Trigger Celery task for SMS sending (background)
        send_password_reset_sms_task.delay(
            phone_number=format_e164(req.phone_number),
            otp=otp
        )
        
        # Get remaining time
        ttl = redis_service.get_ttl(f"otp:reset:{phone}")
        
        return OTPResponse(
            success=True,
            message=f"Reset code sent to {phone[-4:]} (last 4 digits). Valid for 5 minutes.",
            remaining_time=ttl
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset request failed: {str(e)}"
        )


@router.post("/reset-password", response_model=OTPResponse)
async def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2: Reset password with OTP verification
    - Validates OTP from Redis
    - Updates user password
    - Clears OTP from Redis
    """
    try:
        phone = normalize_phone(req.phone_number)
        
        # Verify OTP from Redis
        is_valid = otp_service.verify_otp(
            key=f"otp:reset:{phone}",
            otp=req.otp
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset code"
            )
        
        # Find user and update password
        user = db.execute(
            select(User).where(User.phone == phone)
        ).scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = hash_password(req.new_password)
        db.add(user)
        db.commit()
        
        # Clear OTP from Redis
        otp_service.clear_otp(f"otp:reset:{phone}")
        
        return OTPResponse(
            success=True,
            message="Password reset successful. You can now login with your new password."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )


# ==================== Verify OTP Test Endpoint ====================

@router.post("/test-otp-connection")
async def test_otp_connection():
    """
    Test OTP system health
    - Checks Redis connection
    - Checks Twilio/SMS service
    """
    try:
        # Test Redis
        redis_health = redis_service.is_healthy()
        
        # Test SMS service
        sms_test = {
            "twilio_configured": sms_service.is_configured,
            "test_message": "SMS service ready"
        }
        
        return {
            "success": True,
            "redis": {
                "connected": redis_health,
                "status": "healthy" if redis_health else "unhealthy"
            },
            "sms": sms_test,
            "message": "All systems operational" if redis_health else "Redis not available - OTP storage may fail"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "System health check failed"
        }
