#!/usr/bin/env python
"""
Test script to verify the healthcare system backend setup
- Test database connection
- Create initial RBAC data
- Test JWT token generation
"""
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.auth import Role, Permission, RolePermission, User
from app.core.token import TokenManager
from dotenv import load_dotenv

# Load environment
load_dotenv()


def create_initial_roles_and_permissions(db: Session):
    """Create initial roles and permissions"""
    print("\n📋 Creating initial roles and permissions...")
    
    # Define roles
    roles_data = [
        {"name": "SUPER_ADMIN", "description": "Super administrator with full access"},
        {"name": "ORG_ADMIN", "description": "Organization administrator"},
        {"name": "DOCTOR", "description": "Doctor"},
        {"name": "NURSE", "description": "Nurse"},
        {"name": "LAB_TECH", "description": "Lab technician"},
        {"name": "PHARMACIST", "description": "Pharmacist"},
        {"name": "PATIENT", "description": "Patient"},
        {"name": "BILLING_EXEC", "description": "Billing executive"},
        {"name": "AUDITOR", "description": "Auditor"},
    ]
    
    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"  ✅ Created role: {role_data['name']}")
        else:
            print(f"  ⏭️  Role already exists: {role_data['name']}")
    
    db.commit()
    
    # Define permissions
    permissions_data = [
        # Patient record permissions
        {"name": "view_patient_record", "resource": "patient_record", "action": "READ"},
        {"name": "create_patient_record", "resource": "patient_record", "action": "CREATE"},
        {"name": "edit_patient_record", "resource": "patient_record", "action": "UPDATE"},
        {"name": "delete_patient_record", "resource": "patient_record", "action": "DELETE"},
        
        # Prescription permissions
        {"name": "view_prescription", "resource": "prescription", "action": "READ"},
        {"name": "create_prescription", "resource": "prescription", "action": "CREATE"},
        {"name": "edit_prescription", "resource": "prescription", "action": "UPDATE"},
        
        # Lab order permissions
        {"name": "view_lab_result", "resource": "lab_result", "action": "READ"},
        {"name": "create_lab_order", "resource": "lab_order", "action": "CREATE"},
        
        # Audit permissions
        {"name": "view_audit_logs", "resource": "audit_log", "action": "READ"},
        
        # Organization permissions
        {"name": "manage_organization", "resource": "organization", "action": "UPDATE"},
        {"name": "manage_staff", "resource": "staff", "action": "UPDATE"},
        {"name": "manage_roles", "resource": "role", "action": "UPDATE"},
    ]
    
    for perm_data in permissions_data:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            perm = Permission(**perm_data)
            db.add(perm)
            print(f"  ✅ Created permission: {perm_data['name']}")
        else:
            print(f"  ⏭️  Permission already exists: {perm_data['name']}")
    
    db.commit()


def assign_permissions_to_roles(db: Session):
    """Assign permissions to roles"""
    print("\n🔐 Assigning permissions to roles...")
    
    # Define role -> permissions mapping
    role_permissions = {
        "SUPER_ADMIN": [
            "view_patient_record", "create_patient_record", "edit_patient_record", "delete_patient_record",
            "view_prescription", "create_prescription", "edit_prescription",
            "view_lab_result", "create_lab_order",
            "view_audit_logs",
            "manage_organization", "manage_staff", "manage_roles",
        ],
        "ORG_ADMIN": [
            "view_patient_record", "create_patient_record", "edit_patient_record",
            "manage_staff", "manage_roles",
        ],
        "DOCTOR": [
            "view_patient_record", "create_patient_record", "edit_patient_record",
            "view_prescription", "create_prescription", "edit_prescription",
            "view_lab_result", "create_lab_order",
        ],
        "NURSE": [
            "view_patient_record",
            "view_prescription",
        ],
        "LAB_TECH": [
            "view_lab_result", "create_lab_order",
        ],
        "PHARMACIST": [
            "view_patient_record",
            "view_prescription",
        ],
        "PATIENT": [
            "view_patient_record",
        ],
        "AUDITOR": [
            "view_audit_logs",
        ],
    }
    
    for role_name, perm_names in role_permissions.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            for perm_name in perm_names:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    existing = db.query(RolePermission).filter(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id
                    ).first()
                    if not existing:
                        rp = RolePermission(role_id=role.id, permission_id=perm.id)
                        db.add(rp)
            db.commit()
            print(f"  ✅ Assigned {len(perm_names)} permissions to {role_name}")


def test_token_generation():
    """Test JWT token generation"""
    print("\n🔑 Testing JWT token generation...")
    
    subject = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
    token, expires_in = TokenManager.create_access_token(subject)
    
    print(f"  ✅ Generated access token (expires in {expires_in}s)")
    print(f"     Token (first 50 chars): {token[:50]}...")
    
    # Verify token
    decoded = TokenManager.decode_token(token)
    print(f"  ✅ Decoded token successfully")
    print(f"     User ID: {decoded.get('sub')}")


def main():
    """Main test function"""
    print("=" * 60)
    print("🏥 Healthcare System Backend - Initial Setup Test")
    print("=" * 60)
    
    try:
        # Test database connection
        print("\n🔗 Testing database connection...")
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        print(f"  ✅ Database connection successful")
        
        # Create initial data
        create_initial_roles_and_permissions(db)
        assign_permissions_to_roles(db)
        
        # Test token generation
        test_token_generation()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Backend is ready to run.")
        print("=" * 60)
        print("\n🚀 Start the server with:")
        print("   cd /home/dev/HEALTH-CARE-SYSTEM/backend")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("\n📖 API Docs available at: http://localhost:8000/api/docs")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
