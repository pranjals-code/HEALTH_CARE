"""
Auth & RBAC API routes
Microservice: Authentication & Authorization Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.models.auth import User, Role, Permission, Organization
from app.schemas.auth import (
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RoleCreate,
    RoleResponse,
    PermissionCreate,
    PermissionResponse,
)
from app.services.auth import AuthService
from app.core.dependencies import (
    get_current_user,
    get_current_user_response,
    require_role,
)
from app.core.rbac import RBACManager

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ==================== Authentication Routes ====================
# Note: Phone-based registration with OTP is in routes/otp_auth.py
# POST /auth/register-phone
# POST /auth/verify-phone-otp
# POST /auth/forgot-password
# POST /auth/reset-password


@router.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get JWT tokens"""
    return AuthService.login(login_request, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token"""
    return AuthService.refresh_access_token(request.refresh_token, db)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


# ==================== Role Management Routes ====================


@router.post(
    "/roles",
    response_model=RoleResponse,
    dependencies=[Depends(require_role("SUPER_ADMIN"))],
)
def create_role(
    role_create: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new role (SUPER_ADMIN only)"""
    existing_role = db.query(Role).filter(Role.name == role_create.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists"
        )

    role = Role(name=role_create.name, description=role_create.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_role("SUPER_ADMIN"))],
)
def list_roles(db: Session = Depends(get_db)):
    """List all roles (SUPER_ADMIN only)"""
    roles = db.query(Role).all()
    return roles


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_role("SUPER_ADMIN"))],
)
def get_role(role_id: UUID, db: Session = Depends(get_db)):
    """Get role by ID (SUPER_ADMIN only)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    return role


# ==================== Permission Management Routes ====================


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    dependencies=[Depends(require_role("SUPER_ADMIN"))],
)
def create_permission(
    permission_create: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new permission (SUPER_ADMIN only)"""
    existing_perm = (
        db.query(Permission).filter(Permission.name == permission_create.name).first()
    )
    if existing_perm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Permission already exists"
        )

    permission = Permission(
        name=permission_create.name,
        resource=permission_create.resource,
        action=permission_create.action,
        description=permission_create.description,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_role("SUPER_ADMIN"))],
)
def list_permissions(db: Session = Depends(get_db)):
    """List all permissions (SUPER_ADMIN only)"""
    permissions = db.query(Permission).all()
    return permissions


# ==================== NOTE ====================
# Organization and Staff Profile management routes are placeholder stubs
# These would typically be in separate microservices:
# - Organization Service (multi-tenant management)
# - Staff Service (employee/provider management)
# Phone-based authentication and OTP verification is in routes/otp_auth.py
