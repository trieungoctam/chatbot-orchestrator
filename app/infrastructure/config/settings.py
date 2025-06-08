"""
Infrastructure Configuration Settings
Centralized configuration management using Pydantic Settings
"""
import os
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger(__name__)


# Environment Types
class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Configuration Subsections
class DatabaseConfig(BaseSettings):
    """Database configuration settings"""

    # Connection settings
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="chat_orchestrator", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="postgres", description="Database password")
    driver: str = Field(default="postgresql+asyncpg", description="Database driver")

    # Pool settings
    pool_size: int = Field(default=10, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout seconds")
    pool_recycle: int = Field(default=3600, ge=300, description="Pool recycle seconds")

    # Query settings
    echo: bool = Field(default=False, description="Enable SQL logging")

    # Health check settings
    health_check_timeout: int = Field(default=5, ge=1, description="Health check timeout")

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False
    )

    @property
    def url(self) -> str:
        """Build database URL"""
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """Build synchronous database URL"""
        sync_driver = self.driver.replace("+asyncpg", "")
        return f"{sync_driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class AIServiceConfig(BaseSettings):
    """AI service configuration settings"""

    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_organization: Optional[str] = Field(default=None, description="OpenAI organization")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")

    # Default model settings
    default_model: str = Field(default="gpt-3.5-turbo", description="Default AI model")
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_tokens: int = Field(default=1000, ge=1, description="Default max tokens")

    # Timeout and retry settings
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, description="Retry delay seconds")

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=60, ge=1, description="Rate limit per minute")
    rate_limit_tokens_per_minute: int = Field(default=40000, ge=1, description="Token rate limit per minute")

    # Content safety
    enable_content_filtering: bool = Field(default=True, description="Enable content filtering")
    content_filter_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Content filter threshold")

    # Feature flags
    enable_streaming: bool = Field(default=False, description="Enable streaming responses")
    enable_function_calling: bool = Field(default=True, description="Enable function calling")

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        case_sensitive=False
    )


class PlatformServiceConfig(BaseSettings):
    """Platform service configuration settings"""

    # Telegram settings
    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_webhook_url: Optional[str] = Field(default=None, description="Telegram webhook URL")
    telegram_webhook_secret: Optional[str] = Field(default=None, description="Telegram webhook secret")

    # Facebook settings
    facebook_app_id: Optional[str] = Field(default=None, description="Facebook app ID")
    facebook_app_secret: Optional[str] = Field(default=None, description="Facebook app secret")
    facebook_access_token: Optional[str] = Field(default=None, description="Facebook access token")
    facebook_verify_token: Optional[str] = Field(default=None, description="Facebook verify token")

    # Discord settings
    discord_bot_token: Optional[str] = Field(default=None, description="Discord bot token")
    discord_application_id: Optional[str] = Field(default=None, description="Discord application ID")

    # WhatsApp settings
    whatsapp_access_token: Optional[str] = Field(default=None, description="WhatsApp access token")
    whatsapp_phone_number_id: Optional[str] = Field(default=None, description="WhatsApp phone number ID")
    whatsapp_webhook_verify_token: Optional[str] = Field(default=None, description="WhatsApp webhook verify token")

    # Common settings
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=30, ge=1, description="Rate limit per minute")

    model_config = SettingsConfigDict(
        env_prefix="PLATFORM_",
        case_sensitive=False
    )


class NotificationServiceConfig(BaseSettings):
    """Notification service configuration settings"""

    # Email settings
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")

    # Email defaults
    default_from_email: str = Field(default="noreply@chatorch.com", description="Default from email")
    default_from_name: str = Field(default="Chat Orchestrator", description="Default from name")

    # Templates
    email_template_dir: str = Field(default="templates/email", description="Email template directory")

    # Push notification settings
    fcm_server_key: Optional[str] = Field(default=None, description="FCM server key")
    apns_key_id: Optional[str] = Field(default=None, description="APNS key ID")
    apns_team_id: Optional[str] = Field(default=None, description="APNS team ID")
    apns_bundle_id: Optional[str] = Field(default=None, description="APNS bundle ID")

    # Timeout and retry settings
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")

    model_config = SettingsConfigDict(
        env_prefix="NOTIFICATION_",
        case_sensitive=False
    )


class CacheConfig(BaseSettings):
    """Cache configuration settings"""

    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_username: Optional[str] = Field(default=None, description="Redis username")

    # Connection settings
    redis_max_connections: int = Field(default=10, ge=1, description="Redis max connections")
    redis_socket_timeout: int = Field(default=30, ge=1, description="Redis socket timeout")
    redis_connection_timeout: int = Field(default=10, ge=1, description="Redis connection timeout")

    # Cache settings
    default_ttl: int = Field(default=3600, ge=1, description="Default cache TTL seconds")
    conversation_ttl: int = Field(default=86400, ge=1, description="Conversation cache TTL")
    session_ttl: int = Field(default=1800, ge=1, description="Session cache TTL")

    # Feature flags
    enable_cache: bool = Field(default=True, description="Enable caching")
    enable_cache_compression: bool = Field(default=True, description="Enable cache compression")

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False
    )

    @property
    def redis_url(self) -> str:
        """Build Redis URL"""
        if self.redis_username and self.redis_password:
            return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        elif self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class LoggingConfig(BaseSettings):
    """Logging configuration settings"""

    # Log levels
    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    root_level: LogLevel = Field(default=LogLevel.WARNING, description="Root logger level")

    # Log format
    format_json: bool = Field(default=True, description="Use JSON format")
    include_timestamp: bool = Field(default=True, description="Include timestamp")
    include_trace_id: bool = Field(default=True, description="Include trace ID")

    # Log destinations
    enable_console: bool = Field(default=True, description="Enable console logging")
    enable_file: bool = Field(default=False, description="Enable file logging")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    file_max_size: int = Field(default=10485760, description="Max file size bytes")  # 10MB
    file_backup_count: int = Field(default=5, description="Backup file count")

    # External logging
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    enable_sentry: bool = Field(default=False, description="Enable Sentry")

    # Structured logging
    processors: List[str] = Field(
        default=[
            "structlog.stdlib.filter_by_level",
            "structlog.stdlib.add_logger_name",
            "structlog.stdlib.add_log_level",
            "structlog.stdlib.PositionalArgumentsFormatter",
            "structlog.processors.TimeStamper",
            "structlog.processors.StackInfoRenderer",
            "structlog.processors.format_exc_info"
        ],
        description="Structlog processors"
    )

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False
    )


class SecurityConfig(BaseSettings):
    """Security configuration settings"""

    # Secret keys
    secret_key: str = Field(default="dev-secret-key", description="Application secret key")
    jwt_secret_key: str = Field(default="jwt-secret-key", description="JWT secret key")

    # JWT settings
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, ge=1, description="JWT expiration hours")

    # API keys
    admin_api_keys: str = Field(default="dev-admin-key", description="Admin API keys (comma-separated)")
    platform_access_token: str = Field(default="dev-platform-token", description="Platform access token")

    # CORS settings
    cors_origins: str = Field(default="*", description="CORS allowed origins (comma-separated)")
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    cors_allow_methods: str = Field(default="*", description="CORS allowed methods")
    cors_allow_headers: str = Field(default="*", description="CORS allowed headers")

    # Rate limiting
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=100, ge=1, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=200, ge=1, description="Rate limit burst")

    # Trusted hosts
    trusted_hosts: str = Field(default="*", description="Trusted hosts (comma-separated)")

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=False
    )

    @property
    def admin_api_keys_set(self) -> Set[str]:
        """Get admin API keys as set"""
        return {key.strip() for key in self.admin_api_keys.split(",")}

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def trusted_hosts_list(self) -> List[str]:
        """Get trusted hosts as list"""
        if self.trusted_hosts == "*":
            return ["*"]
        return [host.strip() for host in self.trusted_hosts.split(",")]


# Main Settings Class
class Settings(BaseSettings):
    """Main application settings"""

    # Application settings
    app_name: str = Field(default="Chat Orchestrator", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(default="Chat Orchestrator Core Backend", description="Application description")

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of workers")

    # Documentation
    enable_docs: bool = Field(default=True, description="Enable API documentation")
    docs_url: str = Field(default="/docs", description="Swagger docs URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")

    # Health check
    health_check_path: str = Field(default="/health", description="Health check path")

    # Configuration subsections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ai_service: AIServiceConfig = Field(default_factory=AIServiceConfig)
    platform_service: PlatformServiceConfig = Field(default_factory=PlatformServiceConfig)
    # notification_service: NotificationServiceConfig = Field(default_factory=NotificationServiceConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value"""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.environment == Environment.TESTING


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton pattern)"""
    global _settings

    if _settings is None:
        _settings = Settings()
        logger.info("Configuration loaded",
                   environment=_settings.environment,
                   debug=_settings.debug,
                   database_host=_settings.database.host,
                   cache_enabled=_settings.cache.enable_cache)

    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)"""
    global _settings
    _settings = None
    return get_settings()


# Export singleton instance
settings = get_settings()