"""
Configuration Factory
Factory for creating environment-specific configurations and services
"""
from typing import Dict, Any, Optional
import structlog

from .settings import Settings, Environment, get_settings
from app.infrastructure.database.session import init_database
from app.infrastructure.services.openai_service import OpenAIService
from app.infrastructure.services.telegram_service import TelegramService
from app.infrastructure.services.email_notification_service import EmailNotificationService

logger = structlog.get_logger(__name__)


class ConfigurationError(Exception):
    """Configuration related errors"""
    pass


class ConfigurationFactory:
    """Factory for creating environment-specific configurations"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._services_cache: Dict[str, Any] = {}

    async def initialize_infrastructure(self) -> Dict[str, Any]:
        """Initialize all infrastructure components"""
        logger.info("Initializing infrastructure components")

        try:
            # Initialize database
            await self._initialize_database()

            # Initialize services
            services = {
                'ai_service': self.create_ai_service(),
                'platform_service': self.create_platform_service(),
                'notification_service': self.create_notification_service()
            }

            # Validate services
            await self._validate_services(services)

            logger.info("Infrastructure initialization completed successfully")
            return services

        except Exception as e:
            logger.error("Infrastructure initialization failed", error=str(e))
            raise ConfigurationError(f"Failed to initialize infrastructure: {str(e)}")

    async def _initialize_database(self):
        """Initialize database connection"""
        try:
            from app.infrastructure.database.session import init_database as init_db
            await init_db()
            logger.info("Database initialized",
                       host=self.settings.database.host,
                       database=self.settings.database.name)
        except Exception as e:
            raise ConfigurationError(f"Database initialization failed: {str(e)}")

    def create_ai_service(self) -> OpenAIService:
        """Create AI service instance"""
        if 'ai_service' in self._services_cache:
            return self._services_cache['ai_service']

        config = self.settings.ai_service

        if not config.openai_api_key:
            raise ConfigurationError("OpenAI API key is required but not configured")

        service = OpenAIService(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            organization=config.openai_organization,
            timeout=config.timeout_seconds
        )

        self._services_cache['ai_service'] = service
        logger.info("AI service created", provider="OpenAI")
        return service

    def create_platform_service(self) -> Optional[TelegramService]:
        """Create platform service instance"""
        if 'platform_service' in self._services_cache:
            return self._services_cache['platform_service']

        config = self.settings.platform_service

        # For now, only create Telegram service if token is available
        if config.telegram_bot_token:
            service = TelegramService(
                bot_token=config.telegram_bot_token,
                webhook_url=config.telegram_webhook_url,
                webhook_secret=config.telegram_webhook_secret
            )

            self._services_cache['platform_service'] = service
            logger.info("Platform service created", platform="Telegram")
            return service

        logger.warning("No platform service configured - Telegram token missing")
        return None

    def create_notification_service(self) -> Optional[EmailNotificationService]:
        """Create notification service instance"""
        if 'notification_service' in self._services_cache:
            return self._services_cache['notification_service']

        config = self.settings.notification_service

        # Only create email service if SMTP is configured
        if config.smtp_username and config.smtp_password:
            service = EmailNotificationService(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
                smtp_username=config.smtp_username,
                smtp_password=config.smtp_password,
                use_tls=config.smtp_use_tls,
                default_from_email=config.default_from_email,
                default_from_name=config.default_from_name
            )

            self._services_cache['notification_service'] = service
            logger.info("Notification service created", type="Email")
            return service

        logger.warning("No notification service configured - SMTP credentials missing")
        return None

    async def _validate_services(self, services: Dict[str, Any]):
        """Validate that services are properly configured and accessible"""
        validation_results = {}

        # Validate AI service
        if services.get('ai_service'):
            try:
                is_healthy = await services['ai_service'].health_check()
                validation_results['ai_service'] = is_healthy
                if not is_healthy:
                    logger.warning("AI service health check failed")
            except Exception as e:
                validation_results['ai_service'] = False
                logger.error("AI service validation failed", error=str(e))

        # Validate platform service
        if services.get('platform_service'):
            try:
                is_healthy = await services['platform_service'].health_check()
                validation_results['platform_service'] = is_healthy
                if not is_healthy:
                    logger.warning("Platform service health check failed")
            except Exception as e:
                validation_results['platform_service'] = False
                logger.error("Platform service validation failed", error=str(e))

        logger.info("Service validation completed", results=validation_results)

    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        config = {
            'environment': self.settings.environment.value,
            'debug': self.settings.debug,
            'database_url': self.settings.database.url,
            'logging_level': self.settings.logging.level.value,
            'api_docs_enabled': self.settings.enable_docs,
        }

        # Add environment-specific settings
        if self.settings.environment == Environment.PRODUCTION:
            config.update({
                'cors_origins': self.settings.security.cors_origins_list,
                'trusted_hosts': self.settings.security.trusted_hosts_list,
                'rate_limiting_enabled': self.settings.security.enable_rate_limiting
            })
        elif self.settings.environment == Environment.DEVELOPMENT:
            config.update({
                'cors_origins': ['*'],
                'sql_echo': True,
                'reload': True
            })
        elif self.settings.environment == Environment.TESTING:
            config.update({
                'database_url': self.settings.database.url.replace(
                    self.settings.database.name,
                    f"test_{self.settings.database.name}"
                ),
                'logging_level': 'DEBUG'
            })

        return config

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy"""
        return {
            'url': self.settings.database.url,
            'echo': self.settings.database.echo,
            'pool_size': self.settings.database.pool_size,
            'max_overflow': self.settings.database.max_overflow,
            'pool_timeout': self.settings.database.pool_timeout,
            'pool_recycle': self.settings.database.pool_recycle,
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration"""
        return {
            'redis_url': self.settings.cache.redis_url,
            'max_connections': self.settings.cache.redis_max_connections,
            'socket_timeout': self.settings.cache.redis_socket_timeout,
            'default_ttl': self.settings.cache.default_ttl,
            'enabled': self.settings.cache.enable_cache
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': self.settings.logging.level.value,
            'format_json': self.settings.logging.format_json,
            'enable_console': self.settings.logging.enable_console,
            'enable_file': self.settings.logging.enable_file,
            'file_path': self.settings.logging.file_path,
            'sentry_dsn': self.settings.logging.sentry_dsn,
            'processors': self.settings.logging.processors
        }

    def validate_configuration(self) -> Dict[str, bool]:
        """Validate all configuration sections"""
        validation = {}

        # Validate database configuration
        try:
            db_config = self.settings.database
            validation['database'] = (
                bool(db_config.host) and
                bool(db_config.name) and
                bool(db_config.user) and
                bool(db_config.password)
            )
        except Exception:
            validation['database'] = False

        # Validate AI service configuration
        try:
            ai_config = self.settings.ai_service
            validation['ai_service'] = bool(ai_config.openai_api_key)
        except Exception:
            validation['ai_service'] = False

        # Validate security configuration
        try:
            sec_config = self.settings.security
            validation['security'] = (
                bool(sec_config.secret_key) and
                sec_config.secret_key != "dev-secret-key" if self.settings.is_production() else True
            )
        except Exception:
            validation['security'] = False

        return validation


# Global factory instance
_factory: Optional[ConfigurationFactory] = None


def get_configuration_factory() -> ConfigurationFactory:
    """Get global configuration factory instance"""
    global _factory

    if _factory is None:
        _factory = ConfigurationFactory()

    return _factory