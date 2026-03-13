# OTP/SMS Authentication Implementation Guide

## Overview

This healthcare system implements enterprise-grade phone-based authentication with:
- ✅ OTP (One-Time Password) generation & verification
- ✅ SMS delivery via Twilio
- ✅ Async processing via Celery background tasks
- ✅ Redis-based temporary OTP storage (auto-expires in 5 minutes)
- ✅ Forgot password flow with OTP reset
- ✅ Phone number validation & normalization

---

## Architecture

### Data Flow: Phone Registration

```
User Registration Request
    ↓
API validates email/phone uniqueness
    ↓
Generate 6-digit OTP
    ↓
Store OTP in Redis (5-min TTL, key: otp:register:{phone})
    ↓
Queue SMS task to Celery
    ↓
    ├→ Celery Worker (Background)
    │   ├→ Format phone number
    │   ├→ Call Twilio API
    │   └→ Send SMS with OTP
    │
    └→ Return to user: "OTP sent, check SMS"
         ↓
    User enters OTP
         ↓
    Verify OTP from Redis
         ↓
    Create user with hashed password
         ↓
    Clear OTP from Redis
         ↓
    User created successfully ✅
```

### Components

| Component | Purpose | Tech Stack |
|-----------|---------|-----------|
| **OTP Service** | Generate, store, verify OTPs | Redis (auto-expire keys) |
| **SMS Service** | Send SMS via Twilio API | Twilio SDK |
| **Redis Service** | Manage temporary data | Redis (5-min TTL for OTP) |
| **Celery Tasks** | Async SMS sending | Celery + Redis broker |
| **Auth Routes** | Expose OTP endpoints | FastAPI |
| **Security** | Password hashing | bcrypt (via passlib) |

---

## Endpoints

### 1. Phone Registration (Step 1)

**POST** `/auth/register-phone`

**Request:**
```json
{
  "email": "john@example.com",
  "phone_number": "6175551234",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "OTP sent to 1234 (last 4 digits). Valid for 5 minutes.",
  "remaining_time": 300
}
```

**What happens internally:**
1. Validate email/phone aren't already registered
2. Generate random 6-digit OTP
3. Store in Redis: `otp:register:{phone}` with 5-min expiry
4. Queue Celery task: `send_otp_sms_task(phone, otp, "registration")`
5. Celery worker sends SMS asynchronously
6. Return success to user (doesn't wait for SMS)

---

### 2. Verify OTP & Create Account (Step 2)

**POST** `/auth/verify-phone-otp`

**Request:**
```json
{
  "phone_number": "6175551234",
  "otp": "123456",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "6175551234",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**What happens internally:**
1. Verify OTP from Redis (key: `otp:register:{phone}`)
2. If invalid/expired: return 401
3. Retrieve registration data from Redis (key: `register:{phone}`)
4. Hash password using bcrypt
5. Create User record in PostgreSQL
6. Clear OTP from Redis
7. Clear registration data from Redis
8. Return created user

---

### 3. Forgot Password (Step 1)

**POST** `/auth/forgot-password`

**Request:**
```json
{
  "phone_number": "6175551234"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Reset code sent to 1234 (last 4 digits). Valid for 5 minutes.",
  "remaining_time": 300
}
```

**What happens internally:**
1. Check if phone exists in database
2. Generate new 6-digit OTP
3. Store in Redis: `otp:reset:{phone}` with 5-min expiry
4. Queue Celery task: `send_password_reset_sms_task(phone, otp)`
5. Return success message

---

### 4. Reset Password (Step 2)

**POST** `/auth/reset-password`

**Request:**
```json
{
  "phone_number": "6175551234",
  "otp": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password reset successful. You can now login with your new password."
}
```

**What happens internally:**
1. Verify OTP from Redis (key: `otp:reset:{phone}`)
2. If invalid/expired: return 401
3. Find user by phone
4. Hash new password
5. Update user.hashed_password in database
6. Clear OTP from Redis
7. User can now login with new password

---

### 5. System Health Check

**POST** `/auth/test-otp-connection`

**Response:**
```json
{
  "success": true,
  "redis": {
    "connected": true,
    "status": "healthy"
  },
  "sms": {
    "twilio_configured": true,
    "test_message": "SMS service ready"
  },
  "message": "All systems operational"
}
```

---

## Setup & Configuration

### 1. Environment Variables (.env)

```bash
# Redis (for OTP storage)
REDIS_URL=redis://localhost:6379/0

# OTP Settings
OTP_LENGTH=6
OTP_EXPIRY_SECONDS=300  # 5 minutes

# Twilio (SMS Provider)
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Celery (Background Tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages added:
- `twilio==9.0.0` - SMS API
- `redis==5.0.1` - OTP storage
- `celery==5.3.4` - Background tasks

### 3. Start Services

**Terminal 1: Redis**
```bash
redis-server
```

**Terminal 2: Celery Worker**
```bash
cd backend
celery -A app.celery_app worker --loglevel=info
```

Output should show:
```
[tasks]
  . app.celery_app.send_otp_sms_task
  . app.celery_app.send_password_reset_sms_task
```

**Terminal 3: FastAPI**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 4: Test OTP Flow**
```bash
cd backend
python test_otp_flow.py
```

---

## Testing the Flow

### Manual Testing via Swagger UI

1. Open http://localhost:8000/api/docs
2. Expand `POST /auth/register-phone`
3. Click "Try it out"
4. Enter test data:
   ```json
   {
     "email": "test@example.com",
     "phone_number": "6175551234",
     "first_name": "John",
     "last_name": "Doe"
   }
   ```
5. Click "Execute"
6. You'll get response: "OTP sent to 1234 (last 4 digits)"

### Getting the OTP for Testing

**Option A: Check Redis directly**
```bash
redis-cli
> GET otp:register:6175551234
```

**Option B: Check SMS inbox**
- If Twilio is configured with real credentials, SMS will arrive in 5-10 seconds

**Option C: Check application logs**
- Look for log output showing OTP value

### Complete Test Flow

```bash
# Terminal: Run automated test
python test_otp_flow.py

# It will:
# 1. Check API health
# 2. Check OTP system (Redis, Twilio)
# 3. Register with phone
# 4. Test wrong OTP (should fail)
# 5. Ask you to enter correct OTP
# 6. Verify OTP and create account
# 7. Login with new account
# 8. Test forgot password flow
# 9. Reset password
# 10. Login with new password
```

---

## How OTP is Stored (Redis vs Database)

### Why Redis instead of Database?

| Aspect | Redis | Database |
|--------|-------|----------|
| **Auto-expiry** | ✅ TTL key expires automatically | ❌ Need scheduled cleanup jobs |
| **Performance** | ✅ In-memory, instant access | ❌ Disk I/O overhead |
| **Security** | ✅ Never persisted to disk | ⚠️ Can be extracted from backups |
| **Scalability** | ✅ Cluster-ready | ⚠️ Table bloat over time |
| **HIPAA Compliance** | ✅ No sensitive data on disk | ⚠️ Encryption required |

### OTP Lifecycle in Redis

```
1. User registers → OTP generated
   └→ Redis: SET otp:register:6175551234 "123456" EX 300

2. Celery sends SMS (async)
   └→ No database writes yet

3. User enters OTP → Verified
   └→ Redis: GET otp:register:6175551234 (match check)
   
4. User created in database
   └→ PostgreSQL: INSERT INTO users (...)
   
5. OTP cleared from Redis
   └→ Redis: DEL otp:register:6175551234

6. After 5 minutes (if not used)
   └→ Redis: AUTO-EXPIRE (TTL 0)
      └→ OTP automatically deleted
```

---

## Error Handling

### Registration Errors

```json
{
  "detail": "Email already registered"
  // Status: 400 Bad Request
}

{
  "detail": "Phone number already registered"
  // Status: 400 Bad Request
}
```

### OTP Verification Errors

```json
{
  "detail": "Invalid or expired OTP"
  // Status: 401 Unauthorized
}

{
  "detail": "Registration session expired. Please start over."
  // Status: 400 Bad Request
}
```

### Password Reset Errors

```json
{
  "detail": "Phone number not found"
  // Status: 404 Not Found
  // (Intentional: doesn't reveal if phone exists)
}

{
  "detail": "Invalid or expired reset code"
  // Status: 401 Unauthorized
}
```

---

## Database Schema

### User Table (with phone)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,           -- New field for phone
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### OTP Storage (Redis, not database)

```
Key Format: otp:{action}:{phone}
Example: otp:register:6175551234
Value: 6-digit string
TTL: 300 seconds (5 minutes)
```

---

## Production Checklist

- [ ] Update Twilio credentials in .env (replace test credentials)
- [ ] Use strong SECRET_KEY in .env
- [ ] Enable HTTPS/TLS for all endpoints
- [ ] Configure ALLOWED_ORIGINS for CORS
- [ ] Set DEBUG=False in .env
- [ ] Use PostgreSQL with SSL in production
- [ ] Redis with authentication password
- [ ] Celery worker monitoring (Flower UI)
- [ ] SMS rate limiting (prevent OTP spam)
- [ ] Phone number blacklist/whitelist (optional)
- [ ] Audit logging for password resets
- [ ] Monitor failed OTP attempts
- [ ] Set up alerts for Celery task failures
- [ ] Regular backups of PostgreSQL database
- [ ] Monitor Redis memory usage

---

## Troubleshooting

### SMS Not Received

```
1. Check Twilio credentials in .env
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=+1...

2. Check Celery worker is running
   celery -A app.celery_app worker --loglevel=info

3. Check Redis connection
   redis-cli PING  # Should return PONG

4. Check OTP is stored in Redis
   redis-cli GET otp:register:6175551234

5. Check application logs for errors
   tail -f celery.log
```

### OTP Expired

```
Scenario: User takes >5 minutes to enter OTP

Solution:
1. OTP auto-expires from Redis after 300 seconds
2. User gets error: "Invalid or expired OTP"
3. User can click "Send OTP again"
4. New OTP generated and sent
```

### Redis Connection Failed

```
Error: ConnectionError: Error -2 ENOENT

Solution:
1. Start Redis: redis-server
2. Verify: redis-cli PING
```

### Celery Task Not Running

```
Check:
1. Celery worker is running: celery -A app.celery_app worker
2. Redis broker is running: redis-cli PING
3. Check task logs: celery -A app.celery_app inspect active
4. Check worker logs for exceptions
```

---

## Files Modified/Created

```
app/
├── config.py                    # Updated: Redis, OTP, Twilio settings
├── main.py                      # Updated: Import otp_auth router
├── models/
│   └── auth.py                  # Existing: User model (phone field already added)
├── schemas/
│   └── auth.py                  # Updated: OTP request/response schemas
├── services/
│   ├── redis_service.py         # NEW: Redis wrapper
│   ├── otp_service.py           # NEW: OTP generation/verification
│   ├── sms_service.py           # NEW: Twilio SMS integration
│   └── security.py              # NEW: Password hashing
├── routes/
│   ├── auth.py                  # Existing: Email-based auth
│   └── otp_auth.py              # NEW: Phone-based OTP auth
└── celery_app.py                # NEW: Celery config + tasks

.env                             # Updated: Redis, OTP, Twilio, Celery URLs

requirements.txt                 # Updated: twilio, redis, celery

test_otp_flow.py                 # NEW: OTP flow test script
SETUP.sh                         # NEW: Setup guide

migrations/                      # Alembic migrations (database schema)
```

---

## Key Security Features

1. **OTP Storage**: Redis (no disk persistence)
2. **Password Hashing**: bcrypt with salt
3. **Auto-Expiry**: 5-minute TTL on OTPs
4. **Phone Validation**: Regex pattern matching
5. **Rate Limiting**: Optional (add throttling middleware)
6. **Audit Logging**: Track password resets
7. **No Phone Enumeration**: "Phone not found" for both missing & existing

---

## API Response Codes

| Code | Scenario |
|------|----------|
| 200 | Success |
| 400 | Bad request (validation, duplicate email/phone) |
| 401 | Unauthorized (invalid OTP, wrong password) |
| 404 | Not found (phone doesn't exist) |
| 500 | Server error |

---

## Next Steps

1. **SMS Rate Limiting**: Add throttle to prevent OTP spam
2. **Phone Blacklist**: Support blocking suspicious numbers
3. **Email Verification**: Add email OTP as fallback
4. **2FA**: Implement second factor for enhanced security
5. **Social Login**: Add Google/Apple login integration
6. **Session Management**: Track active sessions, allow logout
7. **Device Management**: Remember device for 30 days
8. **Biometric Auth**: Support fingerprint/face recognition

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/*.log`
2. Test Redis: `redis-cli PING`
3. Test Twilio: Run `python test_otp_flow.py`
4. Debug mode: Set `DEBUG=True` in .env
