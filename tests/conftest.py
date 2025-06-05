from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_async_session
from app.db.base import Base

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test async engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create test async session
TestAsyncSessionFactory = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Override the get_async_session dependency
async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the dependency in the app
app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # Create the database tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Drop the database tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_backend(async_client: AsyncClient) -> dict:
    """Create a test Core AI Backend configuration."""
    backend_data = {
        "name": "Test Backend",
        "api_endpoint_url": "https://api.example.com/v1",
        "auth_token": "test-token-1234",
    }
    
    response = await async_client.post("/api/v1/core-backends", json=backend_data)
    assert response.status_code == 201
    return response.json() 