"""
Database Session Management
Async SQLAlchemy session handling using centralized configuration
"""
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import structlog

from app.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)

# Global session factory
_session_factory: Optional[async_sessionmaker] = None
_async_engine = None


async def init_database():
    """Initialize database engine and session factory using configuration"""
    global _session_factory, _async_engine

    settings = get_settings()
    database_config = settings.database

    database_url = database_config.url
    logger.info("Initializing database",
                url=database_url.split("@")[1] if "@" in database_url else database_url,
                pool_size=database_config.pool_size,
                echo=database_config.echo)

    # Create async engine with configuration
    _async_engine = create_async_engine(
        database_url,
        echo=database_config.echo,
        pool_size=database_config.pool_size,
        max_overflow=database_config.max_overflow,
        pool_timeout=database_config.pool_timeout,
        pool_recycle=database_config.pool_recycle,
        future=True
    )

    # Create session factory
    _session_factory = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False
    )

    logger.info("Database initialized successfully")


class DatabaseSession:
    """Database session context manager"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.close()

    async def commit(self):
        """Commit current transaction"""
        try:
            await self.session.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            logger.error("Failed to commit transaction", error=str(e))
            await self.rollback()
            raise

    async def rollback(self):
        """Rollback current transaction"""
        try:
            await self.session.rollback()
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error("Failed to rollback transaction", error=str(e))

    async def close(self):
        """Close session"""
        await self.session.close()

    async def refresh(self, instance):
        """Refresh instance from database"""
        await self.session.refresh(instance)

    async def merge(self, instance):
        """Merge instance with session"""
        return await self.session.merge(instance)

    async def delete(self, instance):
        """Delete instance"""
        await self.session.delete(instance)

    async def execute(self, statement, parameters=None):
        """Execute raw SQL statement"""
        return await self.session.execute(statement, parameters)

    async def scalar(self, statement, parameters=None):
        """Execute statement and return scalar result"""
        result = await self.session.execute(statement, parameters)
        return result.scalar()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[DatabaseSession, None]:
    """
    Get database session context manager

    Usage:
        async with get_db_session() as db:
            # Use db.session for operations
            result = await db.session.execute(...)
    """
    if _session_factory is None:
        await init_database()

    async with _session_factory() as session:
        db_session = DatabaseSession(session)
        try:
            yield db_session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await db_session.rollback()
            raise
        finally:
            await db_session.close()


async def get_session() -> AsyncSession:
    """Get raw async session"""
    if _session_factory is None:
        await init_database()

    return _session_factory()


async def close_database():
    """Close database connections"""
    global _async_engine, _session_factory

    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _session_factory = None
        logger.info("Database connections closed")


# Health check function
async def check_database_health() -> bool:
    """Check if database is accessible using configuration timeout"""
    try:
        settings = get_settings()
        timeout = settings.database.health_check_timeout

        async with get_db_session() as db:
            await db.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False