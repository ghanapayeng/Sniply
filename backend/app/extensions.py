import logging
import redis
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()

# Initialize limiter with default remote address key function
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)

# Global Redis client reference
redis_client = None


def init_redis(app):
    """Initialize Redis connection with graceful fallback if unavailable."""
    global redis_client
    redis_url = app.config.get("REDIS_URL")
    if not redis_url:
        logger.warning("No REDIS_URL configured; running in fallback mode (no cache).")
        redis_client = None
        return None

    try:
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        client.ping()
        redis_client = client
        logger.info("Connected to Redis successfully.")
        return client
    except Exception as e:
        logger.warning("Failed to connect to Redis at %s: %s. Continuing in fallback mode.", redis_url, e)
        redis_client = None
        return None


def get_redis():
    """Return active Redis client or None if unavailable."""
    return redis_client
