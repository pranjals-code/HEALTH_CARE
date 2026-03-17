"""
RBAC (Role-Based Access Control) utilities
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.auth import User, Role, UserRole, Permission, RolePermission


class RBACManager:
    """Manage RBAC operations"""

    @staticmethod
    def get_user_permissions(
        user_id: UUID, organization_id: Optional[UUID] = None, db: Session = None
    ) -> List[str]:
        """
        Get all permissions for a user in an organization.
        Returns list of permission names.
        """
        if not db:
            return []

        # Get user roles in organization
        user_roles_query = db.query(UserRole).filter(UserRole.user_id == user_id)

        if organization_id:
            # Org-scoped permissions
            user_roles_query = user_roles_query.filter(
                (UserRole.organization_id == organization_id)
                | (UserRole.organization_id.is_(None))  # Global roles apply everywhere
            )

        user_roles = user_roles_query.all()

        if not user_roles:
            return []

        role_ids = [ur.role_id for ur in user_roles]

        # Get permissions for those roles
        permissions = (
            db.query(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id.in_(role_ids))
            .distinct()
            .all()
        )

        return [p[0] for p in permissions]

    @staticmethod
    def has_permission(
        user_id: UUID,
        permission_name: str,
        organization_id: Optional[UUID] = None,
        db: Session = None,
    ) -> bool:
        """Check if user has a specific permission"""
        permissions = RBACManager.get_user_permissions(user_id, organization_id, db)
        return permission_name in permissions

    @staticmethod
    def assign_role_to_user(
        user_id: UUID,
        role_id: UUID,
        organization_id: Optional[UUID] = None,
        assigned_by: Optional[UUID] = None,
        db: Session = None,
    ) -> Optional[UserRole]:
        """Assign a role to a user"""
        if not db:
            return None

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            assigned_by=assigned_by,
        )
        db.add(user_role)
        db.commit()
        db.refresh(user_role)
        return user_role

    @staticmethod
    def remove_role_from_user(
        user_id: UUID,
        role_id: UUID,
        organization_id: Optional[UUID] = None,
        db: Session = None,
    ) -> bool:
        """Remove a role from a user"""
        if not db:
            return False

        result = (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.organization_id == organization_id,
            )
            .delete()
        )
        db.commit()
        return result > 0

    @staticmethod
    def get_user_roles(
        user_id: UUID, organization_id: Optional[UUID] = None, db: Session = None
    ) -> List[str]:
        """Get all role names for a user"""
        if not db:
            return []

        query = (
            db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id)
        )

        if organization_id:
            query = query.filter(
                (UserRole.organization_id == organization_id)
                | (UserRole.organization_id.is_(None))
            )

        roles = query.distinct().all()
        return [r[0] for r in roles]
