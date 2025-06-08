import structlog
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.settings import settings

logger = structlog.get_logger(__name__)

# Tắt hoàn toàn SQLAlchemy logging ở level engine
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

# Create async engine
engine = create_async_engine(
    settings.database_url_computed,
    echo=False,
    poolclass=NullPool if settings.ENVIRONMENT == "testing" else None,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncSession:
    """Get database session for dependency injection"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    from app.db.base import Base

    # logger.info("Creating database tables...")  # Remove verbose log
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # logger.info("Database tables created successfully")  # Remove verbose log

async def close_db():
    """Close database connections"""
    # logger.info("Closing database connections...")  # Remove verbose log
    await engine.dispose()
    # logger.info("Database connections closed")  # Remove verbose log