"""
Auth service - Business logic for authentication & authorization
"""
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.auth import User, Organization
from app.core.token import TokenManager
from app.schemas.auth import LoginRequest, TokenResponse
from app.monitoring import record_failed_auth_attempt, record_login_attempt
from fastapi import HTTPException, status


class AuthService:
    """Authentication and authorization business logic"""
    
    # Note: User registration is done via OTP-based flow in routes/otp_auth.py
    # This service handles login and token refresh only
    
    @staticmethod
    def authenticate_user(
        login_request: LoginRequest,
        db: Session
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email & password.
        Returns: (User, None) if valid, (None, reason) if invalid.
        """
        user = db.query(User).filter(User.email == login_request.email).first()
        
        if not user:
            return None, "user_not_found"
        
        if not TokenManager.verify_password(login_request.password, user.password_hash):
            return None, "invalid_password"
        
        if not user.is_active:
            return None, "inactive_user"
        
        return user, None
    
    @staticmethod
    def login(
        login_request: LoginRequest,
        db: Session
    ) -> TokenResponse:
        """
        Login user and return tokens.
        Raises: HTTPException if authentication fails.
        """
        record_login_attempt(auth_method="password")
        user, failure_reason = AuthService.authenticate_user(login_request, db)
        
        if not user:
            record_failed_auth_attempt(
                auth_method="password",
                reason=failure_reason or "invalid_credentials",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create tokens
        token_subject = {"sub": str(user.id)}
        access_token, expires_in = TokenManager.create_access_token(token_subject)
        refresh_token = TokenManager.create_refresh_token(token_subject)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in
        )
    
    @staticmethod
    def refresh_access_token(
        refresh_token: str,
        db: Session
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.
        Raises: HTTPException if refresh token invalid.
        """
        try:
            payload = TokenManager.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise Exception("Not a refresh token")
        except Exception:
            record_failed_auth_attempt(
                auth_method="refresh_token",
                reason="invalid_refresh_token",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            record_failed_auth_attempt(
                auth_method="refresh_token",
                reason="invalid_token_payload",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verify user still exists and is active
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user or not user.is_active:
            record_failed_auth_attempt(
                auth_method="refresh_token",
                reason="user_not_found_or_inactive",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_subject = {"sub": user_id}
        access_token, expires_in = TokenManager.create_access_token(token_subject)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep the same refresh token
            token_type="bearer",
            expires_in=expires_in
        )
