# Healthcare System Backend - Production-Grade

A **HIPAA-conscious**, **microservice-ready** healthcare platform backend built with **FastAPI**, **PostgreSQL**, and **Alembic migrations**.

## Architecture Overview

```
Healthcare System Backend
│
├── Auth/RBAC Service (Current)
│   ├── User authentication (JWT + refresh tokens)
│   ├── Role-based access control (9 roles)
│   ├── Fine-grained permissions (13+ permissions)
│   ├── Organization multi-tenancy
│   └── Audit logging (HIPAA compliant)
│
└── Future Microservices (Separate Services)
    ├── Patient Service
    ├── Clinical Service (prescriptions, lab orders)
    ├── Billing Service
    └── Notification Service
```

## Features

✅ **JWT Authentication**
- Access tokens (30 min expiry)
- Refresh tokens (7 day expiry)
- Bcrypt password hashing
- Token refresh endpoint

✅ **Role-Based Access Control (RBAC)**
- 9 predefined roles (SUPER_ADMIN, ORG_ADMIN, DOCTOR, NURSE, etc.)
- 13+ granular permissions (view, create, edit, delete)
- Organization-scoped role assignments
- Permission inheritance via role-permission mapping

✅ **Multi-Tenant Architecture**
- Organization isolation
- Department hierarchy
- Org-scoped data access

✅ **HIPAA-Aligned**
- Immutable audit logs (WHO, WHAT, WHEN, WHY)
- Consent tracking
- License expiry tracking
- Encrypted password storage

✅ **Database**
- PostgreSQL with UUID primary keys
- Alembic migrations (auto-generated)
- Relational schema with foreign key constraints
- Indexes on frequently queried columns

## Setup Instructions

### 1. Prerequisites

```bash
# Python 3.10+
python --version

# PostgreSQL 12+
psql --version

# Create database
createdb health_care
```

### 2. Install Dependencies

```bash
cd /home/dev/HEALTH-CARE-SYSTEM/backend
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your PostgreSQL credentials
# DATABASE_URL=postgresql://postgres:password@localhost:5432/health_care
#
# Optional for local development:
# Set ELASTICSEARCH_ENABLED=False if you are not running Elasticsearch.
```

### 4. Run Migrations

```bash
# Create initial schema
python -m alembic upgrade head

# Verify tables were created
psql health_care -c "\dt"
```

### 5. Seed Initial Data

```bash
# Initialize roles and permissions
python test_setup.py
```

### 6. Start the Server

```bash
# Development (with auto-reload)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

If you want patient search enabled locally, make sure Elasticsearch is running on port `9200`:

```bash
# Start Elasticsearch locally on port 9200 before using patient search.
# If Elasticsearch is not running, set ELASTICSEARCH_ENABLED=False in .env.
```

## API Endpoints

### Authentication

```bash
# Register
POST /api/v1/auth/register
{
  "email": "doctor@hospital.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}

# Login
POST /api/v1/auth/login
{
  "email": "doctor@hospital.com",
  "password": "SecurePassword123!"
}

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Refresh Token
POST /api/v1/auth/refresh
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# Get Current User
GET /api/v1/auth/me
Headers: Authorization: Bearer {access_token}
```

### Role Management (SUPER_ADMIN only)

```bash
# List roles
GET /api/v1/auth/roles
Headers: Authorization: Bearer {access_token}

# Create role
POST /api/v1/auth/roles
{
  "name": "CUSTOM_ROLE",
  "description": "Custom role for healthcare staff"
}

# Assign role to user
POST /api/v1/auth/assign-role
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": "a2c15697-bdee-4875-a750-194e4231b386",
  "organization_id": "org-uuid-here"
}
```

### Organization Management

```bash
# Create organization
POST /api/v1/auth/organizations
{
  "name": "City Hospital",
  "registration_number": "REG-2024-001",
  "headquarters_address": "123 Main St",
  "phone": "+1234567890",
  "email": "admin@cityhospital.com"
}
```

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (staff, patients) |
| `roles` | Role definitions |
| `permissions` | Fine-grained permissions |
| `user_roles` | User-to-role assignments (org-scoped) |
| `role_permissions` | Role-to-permission mappings |
| `organizations` | Hospital/clinic entities |
| `departments` | Organizational units |
| `staff_profiles` | Extended staff metadata (license, specialization) |
| `patients` | Patient records |
| `audit_logs` | Immutable access trail |

### Relationships

```
users ──1:N──> user_roles ──N:1──> roles
      └─> user_roles ──N:1──> organizations
      └─> staff_profiles
      └─> audit_logs

roles ──N:M──> permissions (via role_permissions)

organizations ──1:N──> departments
           └─> patients
           └─> staff_profiles
```

## Development

### Add a New Migration

```bash
# Auto-generate migration from model changes
python -m alembic revision --autogenerate -m "Add new table"

# Apply migrations
python -m alembic upgrade head

# Rollback last migration
python -m alembic downgrade -1
```

### Create a New User with Roles

```python
from app.database import SessionLocal
from app.models.auth import User, Role, UserRole
from app.core.token import TokenManager

db = SessionLocal()

# Create user
user = User(
    email="newuser@hospital.com",
    password_hash=TokenManager.hash_password("SecurePassword123!"),
    first_name="Jane",
    last_name="Smith"
)
db.add(user)
db.commit()

# Get DOCTOR role
doctor_role = db.query(Role).filter(Role.name == "DOCTOR").first()

# Assign role
user_role = UserRole(user_id=user.id, role_id=doctor_role.id)
db.add(user_role)
db.commit()
```

### Test Permissions

```python
from app.core.rbac import RBACManager
from app.database import SessionLocal

db = SessionLocal()

# Check if user has permission
has_perm = RBACManager.has_permission(
    user_id=user.id,
    permission_name="view_patient_record",
    db=db
)
print(has_perm)  # True or False
```

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## Security Considerations

### HIPAA Compliance

✅ **What's Implemented**
- Audit logging of all sensitive data access
- Encrypted password storage (bcrypt)
- JWT token expiration
- Role-based access control

⚠️ **Additional Steps for Production**
- Enable HTTPS/TLS (nginx/load balancer)
- Add rate limiting (middleware)
- Implement 2FA
- Add request signing
- Enable database encryption at rest
- Use environment-specific secrets (AWS Secrets Manager, HashiCorp Vault)
- Implement data retention policies
- Add HIPAA BAA agreements

### JWT Security

- **Secret Key**: Change `SECRET_KEY` in `.env` to a strong random string
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **Token Expiry**: Access tokens expire in 30 minutes
- **Refresh Tokens**: Rotate refresh tokens on use (optional)
- **HTTPS Only**: Always use HTTPS in production

## Microservice Architecture Plan

### Phase 1: Auth Service (✅ Current)
- User authentication
- RBAC & permissions
- Organization management

### Phase 2: Patient Service
- Patient records
- Addresses & contacts
- Medical history
- Encounters (visits)

### Phase 3: Clinical Service
- Prescriptions
- Lab orders & results
- Vital signs
- Clinical notes

### Phase 4: Billing Service
- Charges & invoicing
- Insurance claims
- Payments

### Phase 5: Notification Service
- Email notifications
- SMS alerts
- In-app notifications

## Troubleshooting

### Database Connection Error

```
psycopg2.OperationalError: could not connect to server
```

**Solution**: Check PostgreSQL is running and DATABASE_URL is correct
```bash
psql postgres -c "SELECT 1"
```

### Migration Issues

```
sqlalchemy.exc.DatabaseError: Failed to execute
```

**Solution**: Reset database and re-run migrations
```bash
dropdb health_care
createdb health_care
python -m alembic upgrade head
python test_setup.py
```

### JWT Token Invalid

```
HTTPException 401: Invalid authentication token
```

**Solution**: Ensure the `SECRET_KEY` in `.env` matches the one used to generate tokens

## Contributing

When adding new features:
1. Create new models in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Add schemas in `app/schemas/`
4. Add routes in `app/routes/`
5. Test with: `pytest tests/`

## License

Proprietary - Healthcare System

## Contact

For questions or issues, contact the backend team.
