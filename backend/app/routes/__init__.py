"""
Initialize app routes package
"""

from . import auth, otp_auth, patients
from . import media

__all__ = ["auth", "otp_auth", "patients", "media"]
