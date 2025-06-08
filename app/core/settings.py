from typing import List, Optional, Set, Any
from enum import Enum

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ========================================
    # 🖥️ SERVER CONFIGURATION
    # ========================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000  # Changed to match docker-compose
    DEBUG: bool = False
    ENVIRONMENT: AppEnvironment = AppEnvironment.PRODUCTION
    SECRET_KEY: str

    # ========================================
    # 🔐 AUTHENTICATION TOKENS
    # ========================================
    # Main API token for Pancake client
    PLATFORM_ACCESS_TOKEN: str
    # Admin token for management APIs
    ADMIN_ACCESS_TOKEN: str
    # Admin API keys for security
    ADMIN_API_KEYS: str = "dev-api-key"

    # ========================================
    # 🗄️ DATABASE CONFIGURATION - PostgreSQL
    # ========================================
    # Individual PostgreSQL components (for docker-compose compatibility)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "chatbot"  # Changed to match docker-compose default
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str

    # Complete database URL (alternative to individual components)
    DATABASE_URL: Optional[PostgresDsn] = None

    @property
    def database_url_computed(self) -> str:
        """Build async PostgreSQL URL from components or use DATABASE_URL"""
        if self.DATABASE_URL:
            return str(self.DATABASE_URL)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Database connection settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # ========================================
    # 🔴 REDIS CONFIGURATION
    # ========================================
    # Individual Redis components (for docker-compose compatibility)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Complete Redis URL (alternative to individual components)
    REDIS_URL: Optional[str] = None

    @property
    def redis_url_computed(self) -> str:
        """Build Redis URL from components or use REDIS_URL"""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Redis connection settings
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_SOCKET_TIMEOUT: int = 30

    # ========================================
    # 📊 LOGGING CONFIGURATION
    # ========================================
    LOG_LEVEL: str = "WARNING"
    LOG_JSON: bool = True
    LOG_FILE: Optional[str] = None

    # ========================================
    # 🌐 CORS CONFIGURATION
    # ========================================
    CORS_ORIGINS: str = "*"

    # ========================================
    # 🔧 SYSTEM TUNING (from old config.py)
    # ========================================
    # Race condition handling
    MAX_CONVERSATION_AGE_HOURS: int = 24
    AI_PROCESSING_TIMEOUT: int = 30
    MAX_RETRY_ATTEMPTS: int = 3

    # Memory management
    MAX_CONTEXT_SIZE: int = 100
    CLEANUP_INTERVAL_HOURS: int = 6

    # Redis TTL settings (seconds)
    CONVERSATION_STATE_TTL: int = 86400  # 24 hours
    PROCESSING_LOCK_TTL: int = 30  # 30 seconds

    # ========================================
    # 🤖 AI & LLM CONFIGURATION
    # ========================================
    # LLM settings
    DEBOUNCE_SECONDS: float = 1.0  # Time to wait for more messages before processing
    LLM_TIMEOUT_SECONDS: float = 10.0  # Timeout for LLM API calls

    # AI Service configuration
    AI_SERVICE_URL: str = "http://ai-service:8001"
    AI_SERVICE_TIMEOUT: int = 30

    # ========================================
    # 📋 QUEUE SETTINGS
    # ========================================
    DEFAULT_QUEUE_NAME: str = "default_queue"

    # ========================================
    # 👷 WORKER SETTINGS
    # ========================================
    MAX_WORKERS_PER_TYPE: int = 10
    JOB_TIMEOUT_SECONDS: int = 300  # 5 minutes
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 10
    WORKER_POLL_TIMEOUT: int = 5

    # ========================================
    # 🌾 CELERY SETTINGS
    # ========================================
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # ========================================
    # 📊 MONITORING & METRICS
    # ========================================
    PROMETHEUS_PORT: int = 8001
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True

    # ========================================
    # ⚙️ JOB PROCESSING
    # ========================================
    JOB_EXPIRY_HOURS: int = 24
    MAX_QUEUE_LENGTH: int = 1000
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: float = 60.0

    # ========================================
    # 🛠️ COMPUTED PROPERTIES
    # ========================================
    @property
    def admin_api_keys_set(self) -> Set[str]:
        """Return the admin API keys as a set."""
        if not self.ADMIN_API_KEYS:
            return {"dev-api-key"}
        return {key.strip() for key in self.ADMIN_API_KEYS.split(",")}

    @property
    def cors_origins_list(self) -> List[str]:
        """Return the CORS origins as a list."""
        if not self.CORS_ORIGINS:
            return ["http://localhost:3000"]
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def celery_broker_url(self) -> str:
        """Return Celery broker URL, defaulting to Redis URL."""
        return self.CELERY_BROKER_URL or self.redis_url_computed

    @property
    def celery_result_backend(self) -> str:
        """Return Celery result backend, defaulting to Redis URL."""
        return self.CELERY_RESULT_BACKEND or self.redis_url_computed

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Create a global settings object
settings = Settings()