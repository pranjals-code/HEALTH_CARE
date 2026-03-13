"""
Auth/RBAC Models - Core authentication and authorization
Microservice: Auth Service
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, UniqueConstraint, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, INET
from app.models.base import BaseModel
import uuid


class User(BaseModel):
    """
    Core user identity. All system users (staff, patients) start here.
    """
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan")
    staff_profile = relationship("StaffProfile", uselist=False, back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="actor_user")


class Role(BaseModel):
    """
    Role definitions (SUPER_ADMIN, ORG_ADMIN, DOCTOR, NURSE, etc.)
    """
    __tablename__ = "roles"
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(BaseModel):
    """
    Granular permission definitions (e.g., 'view_patient_record', 'edit_prescription')
    """
    __tablename__ = "permissions"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False)  # patient_record, prescription, lab_result
    action = Column(String(20), nullable=False)    # CREATE, READ, UPDATE, DELETE, EXECUTE
    description = Column(Text)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class UserRole(BaseModel):
    """
    Many-to-many: Users to Roles (org-scoped)
    A user can have multiple roles across different organizations
    """
    __tablename__ = "user_roles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)  # NULL = global scope
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Who made the assignment
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'organization_id', name='unique_user_role_org'),
    )
    
    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")


class RolePermission(BaseModel):
    """
    Many-to-many: Roles to Permissions
    """
    __tablename__ = "role_permissions"
    
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='unique_role_permission'),
    )
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class Organization(BaseModel):
    """
    Multi-tenant: Hospitals, clinics, health networks
    """
    __tablename__ = "organizations"
    
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=False, index=True)
    headquarters_address = Column(String(500))
    phone = Column(String(20))
    email = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="organization", cascade="all, delete-orphan")
    staff_profiles = relationship("StaffProfile", back_populates="organization", cascade="all, delete-orphan")


class Department(BaseModel):
    """
    Departments within an organization
    """
    __tablename__ = "departments"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20))
    head_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'code', name='unique_org_dept_code'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="departments")


class StaffProfile(BaseModel):
    """
    Extended staff metadata (doctors, nurses, lab techs, etc.)
    """
    __tablename__ = "staff_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    employee_id = Column(String(50), nullable=False)
    license_number = Column(String(100))
    license_expiry = Column(String(10))  # YYYY-MM-DD format
    specialization = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'employee_id', name='unique_org_employee_id'),
    )
    
    # Relationships
    user = relationship("User", back_populates="staff_profile")
    organization = relationship("Organization", back_populates="staff_profiles")


class AuditLog(BaseModel):
    """
    Immutable audit trail of all sensitive operations
    HIPAA compliance: WHO accessed WHAT, WHEN, WHY
    """
    __tablename__ = "audit_logs"
    
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # VIEW, CREATE, UPDATE, DELETE, EXECUTE
    resource_type = Column(String(100), nullable=False, index=True)  # patient_record, prescription
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    old_values = Column(String, nullable=True)  # JSON as string for audit
    new_values = Column(String, nullable=True)  # JSON as string for audit
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)
    reason_code = Column(String(50))  # TREATMENT, ADMIN, AUDIT, QUERY
    status = Column(String(20), default="SUCCESS")  # SUCCESS, DENIED, FAILED
    
    # Relationships
    actor_user = relationship("User", back_populates="audit_logs")


class Patient(BaseModel):
    """
    Core patient record
    """
    __tablename__ = "patients"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=True)  # Optional patient login
    mrn = Column(String(50), nullable=False, index=True)  # Medical Record Number
    date_of_birth = Column(String(10), nullable=False)  # YYYY-MM-DD format
    gender = Column(String(20))  # M, F, Other, Declined
    blood_type = Column(String(10))
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    is_active = Column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'mrn', name='unique_org_mrn'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="patients")
