"""
Pydantic schemas for request/response validation - Auth & RBAC
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


# ==================== Registration & OTP ====================


class RegisterRequest(BaseModel):
    """Initial registration request with phone number"""

    email: EmailStr
    phone_number: str
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("phone_number")
    def validate_phone(cls, v):
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) < 10:
            raise ValueError("Phone must have at least 10 digits")
        return v


class VerifyOTPRequest(BaseModel):
    """Verify OTP and create account"""

    phone_number: str
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    password: str = Field(..., min_length=8, max_length=100)


class OTPResponse(BaseModel):
    """Response for OTP requests"""

    success: bool
    message: str
    remaining_time: Optional[int] = None


# ==================== Password Reset ====================


class ForgotPasswordRequest(BaseModel):
    """Request password reset"""

    phone_number: str


class VerifyResetOTPRequest(BaseModel):
    """Verify OTP for password reset"""

    phone_number: str
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    """Reset password with new password"""

    phone_number: str
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)


# ==================== Login ====================


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


# ==================== User ====================


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class UserResponse(UserBase):
    """User response"""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Role & Permission ====================


class RoleBase(BaseModel):
    """Base role schema"""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    """Role response"""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """Base permission schema"""

    name: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    """Permission response"""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
