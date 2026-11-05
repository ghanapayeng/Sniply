import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(url: str | None) -> str:
    """Normalize database URL for SQLAlchemy (handles postgres:// -> postgresql://)."""
    if not url:
        return "postgresql://sniply:sniplypassword@127.0.0.1:5433/sniply"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "sniply-dev-secret-key-change-in-production-389104")
    
    # Database - Prefer pooled connection for web application traffic, fallback to DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL_POOLED") or os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
        "pool_pre_ping": True,
    }

    # Redis & Caching
    REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "3600"))
    
    # Rate Limiting
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "120/minute")
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_HEADERS_ENABLED = True

    # Application URLs
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    
    # CORS
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000")
    CORS_ALLOWED_ORIGINS = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]

    # Cookies & Sessions
    SESSION_COOKIE_NAME = "sniply_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
    SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_LIFETIME_DAYS", "14")))
    
    # URL Shortener Policies
    ANONYMOUS_MAX_EXPIRY_DAYS = int(os.getenv("ANONYMOUS_MAX_EXPIRY_DAYS", "30"))
    DEFAULT_EXPIRY_DAYS = int(os.getenv("DEFAULT_EXPIRY_DAYS", "90"))
    ANONYMOUS_DAILY_LIMIT = int(os.getenv("ANONYMOUS_DAILY_LIMIT", "20"))
    AUTHENTICATED_DAILY_LIMIT = int(os.getenv("AUTHENTICATED_DAILY_LIMIT", "500"))
    
    # Security
    IP_HASH_SALT = os.getenv("IP_HASH_SALT", "sniply-visitor-salt-value-privacy")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://sniply:sniplypassword@127.0.0.1:5433/sniply_test"
    )
    RATELIMIT_STORAGE_URI = "memory://"
    REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6379/1")
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    # Ensure SSL is enforced if Neon or remote PostgreSQL is used
    if BaseConfig.SQLALCHEMY_DATABASE_URI and "sslmode=" not in BaseConfig.SQLALCHEMY_DATABASE_URI and "localhost" not in BaseConfig.SQLALCHEMY_DATABASE_URI and "127.0.0.1" not in BaseConfig.SQLALCHEMY_DATABASE_URI:
        sep = "&" if "?" in BaseConfig.SQLALCHEMY_DATABASE_URI else "?"
        SQLALCHEMY_DATABASE_URI = f"{BaseConfig.SQLALCHEMY_DATABASE_URI}{sep}sslmode=require"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
