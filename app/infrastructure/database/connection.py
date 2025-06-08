"""
Database Connection Configuration
Manages database connection settings and engine creation using centralized config
"""
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import QueuePool
import structlog

from app.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


def get_database_url(config=None) -> str:
    """
    Build database URL from configuration

    Args:
        config: Optional database config (uses global settings if None)

    Returns:
        Database URL string
    """
    if config is None:
        settings = get_settings()
        config = settings.database

    return config.url


def create_engine_instance(
    database_url: Optional[str] = None,
    config=None
) -> Engine:
    """
    Create SQLAlchemy engine with configuration settings

    Args:
        database_url: Database URL (optional, uses config if None)
        config: Database configuration (uses global settings if None)

    Returns:
        SQLAlchemy Engine instance
    """
    if config is None:
        settings = get_settings()
        config = settings.database

    if database_url is None:
        database_url = config.url

    logger.info("Creating database engine",
                url=database_url.split("@")[1] if "@" in database_url else database_url,
                pool_size=config.pool_size,
                echo=config.echo)

    engine = create_engine(
        database_url,
        echo=config.echo,
        poolclass=QueuePool,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        # Async settings
        future=True,
        # Connection options
        connect_args={
            "server_settings": {
                "application_name": "chat_orchestrator",
                "jit": "off"  # Disable JIT for better performance with small queries
            }
        }
    )

    return engine


# Global engine instance
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create global engine instance using configuration"""
    global _engine
    if _engine is None:
        _engine = create_engine_instance()
    return _engine


def close_engine():
    """Close global engine instance"""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None