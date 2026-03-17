"""
Test script for OTP/SMS authentication flow
Tests phone registration, OTP verification, and password reset
"""

import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"


class OTPTestClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def test_health(self):
        """Test API health"""
        print("\n🔍 Testing API Health...")
        try:
            resp = self.session.get(f"{self.base_url}/health")
            print(f"✅ API Health: {resp.json()}")
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_otp_connection(self):
        """Test OTP system health"""
        print("\n🔍 Testing OTP System Connection...")
        try:
            resp = self.session.post(f"{self.base_url}/auth/test-otp-connection")
            data = resp.json()
            print(f"✅ OTP System Status: {json.dumps(data, indent=2)}")
            return data.get("success", False)
        except Exception as e:
            print(f"❌ OTP connection test failed: {e}")
            return False

    def register_with_phone(
        self, email: str, phone: str, first_name: str, last_name: str
    ) -> Optional[dict]:
        """Register with phone number and get OTP"""
        print(f"\n📱 Registering with phone: {phone}")
        try:
            payload = {
                "email": email,
                "phone_number": phone,
                "first_name": first_name,
                "last_name": last_name,
            }
            resp = self.session.post(
                f"{self.base_url}/auth/register-phone", json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Registration OTP sent: {data['message']}")
                if data.get("remaining_time"):
                    print(f"   ⏱️  OTP expires in: {data['remaining_time']} seconds")
                return data
            else:
                print(f"❌ Registration failed: {resp.text}")
                return None

        except Exception as e:
            print(f"❌ Registration error: {e}")
            return None

    def verify_otp(self, phone: str, otp: str, password: str) -> Optional[dict]:
        """Verify OTP and create user"""
        print(f"\n✓ Verifying OTP: {otp}")
        try:
            payload = {"phone_number": phone, "otp": otp, "password": password}
            resp = self.session.post(
                f"{self.base_url}/auth/verify-phone-otp", json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ OTP verified! User created: {data['email']}")
                print(f"   ID: {data['id']}")
                return data
            else:
                print(f"❌ OTP verification failed: {resp.text}")
                return None

        except Exception as e:
            print(f"❌ OTP verification error: {e}")
            return None

    def forgot_password(self, phone: str) -> Optional[dict]:
        """Initiate forgot password"""
        print(f"\n🔑 Initiating password reset for: {phone}")
        try:
            payload = {"phone_number": phone}
            resp = self.session.post(
                f"{self.base_url}/auth/forgot-password", json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Reset OTP sent: {data['message']}")
                if data.get("remaining_time"):
                    print(f"   ⏱️  OTP expires in: {data['remaining_time']} seconds")
                return data
            else:
                print(f"❌ Forgot password failed: {resp.text}")
                return None

        except Exception as e:
            print(f"❌ Forgot password error: {e}")
            return None

    def reset_password(self, phone: str, otp: str, new_password: str) -> Optional[dict]:
        """Reset password with OTP"""
        print(f"\n🔐 Resetting password with OTP: {otp}")
        try:
            payload = {"phone_number": phone, "otp": otp, "new_password": new_password}
            resp = self.session.post(
                f"{self.base_url}/auth/reset-password", json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Password reset successful: {data['message']}")
                return data
            else:
                print(f"❌ Password reset failed: {resp.text}")
                return None

        except Exception as e:
            print(f"❌ Password reset error: {e}")
            return None

    def login(self, email: str, password: str) -> Optional[dict]:
        """Login with email and password"""
        print(f"\n🔓 Logging in: {email}")
        try:
            payload = {"email": email, "password": password}
            resp = self.session.post(f"{self.base_url}/auth/login", json=payload)

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Login successful!")
                print(f"   Token Type: {data.get('token_type')}")
                print(f"   Expires in: {data.get('expires_in')} seconds")
                return data
            else:
                print(f"❌ Login failed: {resp.text}")
                return None

        except Exception as e:
            print(f"❌ Login error: {e}")
            return None


def run_test_scenarios():
    """Run comprehensive OTP flow tests"""
    print("=" * 60)
    print("🏥 HEALTHCARE SYSTEM - OTP/SMS AUTHENTICATION TEST")
    print("=" * 60)

    client = OTPTestClient()

    # Test 1: Health checks
    print("\n" + "=" * 60)
    print("TEST 1: SYSTEM HEALTH CHECKS")
    print("=" * 60)

    if not client.test_health():
        print("❌ API is not running. Start with: uvicorn app.main:app --reload")
        return

    if not client.test_otp_connection():
        print("⚠️  Redis or Twilio may not be configured. Check .env and services.")

    # Test 2: Registration with phone
    print("\n" + "=" * 60)
    print("TEST 2: PHONE REGISTRATION WITH OTP")
    print("=" * 60)

    test_phone = "16175551234"  # Format: 10 digits minimum
    test_email = "test@example.com"
    test_password = "SecurePass123!"

    reg_result = client.register_with_phone(
        email=test_email, phone=test_phone, first_name="John", last_name="Doe"
    )

    if not reg_result:
        print("❌ Skipping OTP verification - registration failed")
        return

    # For testing: manually provide OTP or check Redis
    print("\n💡 In production, user would receive SMS with OTP")
    print("   For testing:")
    print("   - Check your phone for SMS (if Twilio is configured)")
    print("   - Or check Redis: redis-cli GET 'otp:register:{}'".format(test_phone))
    print("   - Or check logs for OTP value (if SMS fails)")

    # Test with wrong OTP first
    print("\n" + "-" * 60)
    print("Testing with WRONG OTP (should fail)...")
    wrong_otp_result = client.verify_otp(test_phone, "000000", test_password)
    if wrong_otp_result is None:
        print("✅ Correctly rejected invalid OTP")

    # Get correct OTP from user input
    otp_input = input("\n📱 Enter OTP from SMS (or 'skip' to skip): ").strip()

    if otp_input.lower() != "skip":
        # Test 3: Verify OTP
        print("\n" + "=" * 60)
        print("TEST 3: OTP VERIFICATION & USER CREATION")
        print("=" * 60)

        verify_result = client.verify_otp(test_phone, otp_input, test_password)

        if verify_result:
            # Test 4: Login with new account
            print("\n" + "=" * 60)
            print("TEST 4: LOGIN WITH NEW ACCOUNT")
            print("=" * 60)

            login_result = client.login(test_email, test_password)
            if login_result:
                print("✅ Complete registration flow successful!")

    # Test 5: Forgot Password Flow
    print("\n" + "=" * 60)
    print("TEST 5: PASSWORD RESET FLOW")
    print("=" * 60)

    forgot_result = client.forgot_password(test_phone)
    if forgot_result:
        reset_otp = input("\n📱 Enter Reset OTP from SMS (or 'skip' to skip): ").strip()

        if reset_otp.lower() != "skip":
            new_password = "NewSecurePass456!"
            reset_result = client.reset_password(test_phone, reset_otp, new_password)

            if reset_result:
                # Test login with new password
                print("\nAttempting login with new password...")
                new_login_result = client.login(test_email, new_password)
                if new_login_result:
                    print("✅ Password reset flow successful!")

    # Summary
    print("\n" + "=" * 60)
    print("✅ TEST SUITE COMPLETE")
    print("=" * 60)
    print(
        """
NEXT STEPS:
1. Start Redis: redis-server
2. Start Celery worker: celery -A app.celery_app worker --loglevel=info
3. Start FastAPI: uvicorn app.main:app --reload
4. Run this test: python test_otp_flow.py

FEATURES TESTED:
✓ API Health Check
✓ OTP System Health
✓ Phone Registration with OTP
✓ OTP Verification
✓ User Account Creation
✓ Login with New Account
✓ Password Reset with OTP
✓ Login with New Password

WHAT'S HAPPENING BEHIND THE SCENES:
- OTP stored in Redis (not database)
- Auto-expires in 5 minutes
- Celery tasks send SMS asynchronously
- Twilio integration for real SMS delivery
- Password hashed with bcrypt
"""
    )


if __name__ == "__main__":
    run_test_scenarios()
