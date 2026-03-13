"""
Security utilities - Password hashing and verification
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BCRYPT_MAX_BYTES = 72


def _normalize_password(password: str) -> str:
    """
    Normalize password to bcrypt's 72-byte limit.
    Truncate by bytes (UTF-8) to avoid passlib error.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= _BCRYPT_MAX_BYTES:
        return password
    return password_bytes[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(_normalize_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)
