"""
Core configuration module for Healthcare System Backend
Microservice Architecture: Auth/RBAC Service + OTP/SMS + Celery Background Tasks
"""

from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/healthcare_system"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Uploads
    UPLOAD_DIR: str = str(Path(__file__).resolve().parents[1] / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 50

    # Service
    SERVICE_NAME: str = "healthcare-auth-service"
    SERVICE_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # CORS (comma-separated string)
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:8000"
    )

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # OTP Configuration
    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 300  # 5 minutes
    DEFAULT_COUNTRY_CODE: str = "+91"

    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED: bool = True
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_PATIENT_INDEX: str = "patients"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        """Allow common env strings such as development/release."""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "production"}:
                return False

        return bool(value)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
