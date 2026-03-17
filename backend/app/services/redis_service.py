"""
Redis service for OTP and caching
"""

import redis
import os
import json
from typing import Optional, Any
from dotenv import load_dotenv
from app.core.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class RedisService:
    """Redis connection and OTP management"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning("Redis not available: %s", str(e))
            self.client = None

    def set_with_expiry(
        self,
        key: str,
        value: Any,
        expiry_seconds: Optional[int] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set key with automatic expiry"""
        try:
            if self.client:
                expiry = expiry_seconds if expiry_seconds is not None else ttl
                if expiry is None:
                    raise ValueError("expiry_seconds or ttl is required")

                if isinstance(value, (str, bytes, int, float)):
                    payload = value
                else:
                    payload = json.dumps(value)

                self.client.setex(key, expiry, payload)
                return True
            return False
        except Exception as e:
            logger.error("Redis set error: %s", str(e))
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            if self.client:
                value = self.client.get(key)
                if value is None:
                    return None
                if isinstance(value, str):
                    # Only decode JSON for objects/arrays we stored as JSON.
                    if value.startswith("{") or value.startswith("["):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                    return value
                return value
            return None
        except Exception as e:
            logger.error("Redis get error: %s", str(e))
            return None

    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            if self.client:
                self.client.delete(key)
                return True
            return False
        except Exception as e:
            logger.error("Redis delete error: %s", str(e))
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL in seconds"""
        try:
            if self.client:
                ttl = self.client.ttl(key)
                return ttl if ttl > 0 else None
            return None
        except:
            return None

    def is_healthy(self) -> bool:
        """Check Redis health"""
        try:
            if self.client:
                self.client.ping()
                return True
            return False
        except:
            return False


redis_service = RedisService()
