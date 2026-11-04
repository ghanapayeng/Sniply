import json
import logging
from typing import Optional, Dict, Any
from backend.app.extensions import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    @staticmethod
    def _key(code: str) -> str:
        return f"url:{code.strip()}"

    @classmethod
    def get_url(cls, code: str) -> Optional[Dict[str, Any]]:
        """Retrieve URL payload from Redis cache."""
        redis_conn = get_redis()
        if not redis_conn:
            return None
        try:
            val = redis_conn.get(cls._key(code))
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning("Cache GET failed for %s: %s", code, e)
        return None

    @classmethod
    def set_url(cls, code: str, payload: Dict[str, Any], ttl: int = 3600) -> bool:
        """Store URL payload in Redis cache with TTL."""
        redis_conn = get_redis()
        if not redis_conn:
            return False
        try:
            # If TTL is 0 or negative, don't cache
            if ttl <= 0:
                return False
            redis_conn.setex(cls._key(code), ttl, json.dumps(payload))
            return True
        except Exception as e:
            logger.warning("Cache SET failed for %s: %s", code, e)
            return False

    @classmethod
    def invalidate(cls, short_code: str, custom_alias: Optional[str] = None) -> bool:
        """Remove short_code and custom_alias mappings from Redis cache."""
        redis_conn = get_redis()
        if not redis_conn:
            return False
        try:
            keys = [cls._key(short_code)]
            if custom_alias:
                keys.append(cls._key(custom_alias))
            redis_conn.delete(*keys)
            return True
        except Exception as e:
            logger.warning("Cache INVALIDATE failed for %s: %s", short_code, e)
            return False
