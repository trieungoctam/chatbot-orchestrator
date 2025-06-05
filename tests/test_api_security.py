import pytest
from httpx import AsyncClient
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.settings import settings
from conftest import async_client, test_backend


@pytest.mark.asyncio
async def test_unauthorized_access_to_bots(async_client: AsyncClient):
    """Test that unauthorized access to bots endpoint returns 401."""
    # Try to access the bots endpoint without an API key
    response = await async_client.get("/api/v1/bots")
    assert response.status_code == HTTP_401_UNAUTHORIZED
    
    # Try with an invalid API key
    response = await async_client.get(
        "/api/v1/bots",
        headers={"X-API-KEY": "invalid-key"}
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_unauthorized_access_to_core_backends(async_client: AsyncClient):
    """Test that unauthorized access to core-backends endpoint returns 401."""
    # Try to access the core-backends endpoint without an API key
    response = await async_client.get("/api/v1/core-backends")
    assert response.status_code == HTTP_401_UNAUTHORIZED
    
    # Try with an invalid API key
    response = await async_client.get(
        "/api/v1/core-backends",
        headers={"X-API-KEY": "invalid-key"}
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_unauthorized_access_to_logs(async_client: AsyncClient):
    """Test that unauthorized access to logs endpoint returns 401."""
    # Create a valid UUID to test with
    import uuid
    test_uuid = uuid.uuid4()
    
    # Try to access the logs endpoint without an API key
    response = await async_client.get(f"/api/v1/logs/{test_uuid}")
    assert response.status_code == HTTP_401_UNAUTHORIZED
    
    # Try with an invalid API key
    response = await async_client.get(
        f"/api/v1/logs/{test_uuid}",
        headers={"X-API-KEY": "invalid-key"}
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_authorized_access(async_client: AsyncClient):
    """Test that authorized access to endpoints works."""
    # Get a valid API key from settings
    valid_api_key = next(iter(settings.ADMIN_API_KEYS))
    
    # Try to access the bots endpoint with a valid API key
    response = await async_client.get(
        "/api/v1/bots",
        headers={"X-API-KEY": valid_api_key}
    )
    assert response.status_code == 200
    
    # Try to access the core-backends endpoint with a valid API key
    response = await async_client.get(
        "/api/v1/core-backends",
        headers={"X-API-KEY": valid_api_key}
    )
    assert response.status_code == 200 