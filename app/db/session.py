from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.settings import settings

# Create async engine
engine = create_async_engine(
    settings.database_url_computed,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    poolclass=NullPool if settings.ENVIRONMENT == "testing" else None,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False
)


# Dependency for FastAPI endpoints
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async SQLAlchemy session.

    Yields:
        AsyncSession: Async SQLAlchemy session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()