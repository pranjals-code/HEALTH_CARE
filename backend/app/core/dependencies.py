"""
Dependencies for FastAPI routes (authentication, permissions, etc.)
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.authentication import AuthCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.token import TokenManager
from app.core.rbac import RBACManager
from app.models.auth import User
from app.schemas.auth import UserResponse

security = HTTPBearer()


async def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    Raise 401 if token invalid or user inactive.
    """
    token = credentials.credentials
    
    try:
        payload = TokenManager.decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


async def get_current_user_response(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get current user response"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


def require_permission(permission_name: str):
    """
    Dependency: Check if user has specific permission.
    Usage: @router.get('/endpoint', dependencies=[Depends(require_permission('view_patient_record'))])
    """
    async def check_permission(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        # For now, check globally (no org_id filter)
        has_perm = RBACManager.has_permission(
            current_user.id,
            permission_name,
            db=db
        )
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have '{permission_name}' permission"
            )
        return True
    
    return check_permission


def require_role(role_name: str):
    """
    Dependency: Check if user has specific role.
    Usage: @router.get('/endpoint', dependencies=[Depends(require_role('DOCTOR'))])
    """
    async def check_role(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        user_roles = RBACManager.get_user_roles(current_user.id, db=db)
        if role_name not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have '{role_name}' role"
            )
        return True
    
    return check_role
