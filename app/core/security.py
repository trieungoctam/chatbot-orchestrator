from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, status
from app.core.settings import settings


def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from header."""
    return x_api_key


def get_platform_token(x_platform_token: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Platform token from header."""
    return x_platform_token


async def verify_flexible_auth(
    api_key: Optional[str] = None,
    platform_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify flexible authentication - accepts either API key or Platform token.
    """
    # Try API key first
    if api_key and api_key in settings.admin_api_keys_set:
        return {
            "auth_type": "api_key",
            "auth_value": api_key,
            "is_admin": True,
            "is_platform": False
        }

    # Try Pancake token
    if platform_token and platform_token == settings.PLATFORM_ACCESS_TOKEN:
        return {
            "auth_type": "platform_token",
            "auth_value": platform_token,
            "is_admin": False,
            "is_platform": True
        }

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either X-API-KEY or X-Platform-Token",
        headers={"WWW-Authenticate": "ApiKey, PlatformToken"}
    )


async def verify_no_auth_required() -> Dict[str, Any]:
    """
    Verification function for endpoints that don't require authentication.
    """
    return {
        "auth_type": "none",
        "auth_value": None,
        "is_admin": False,
        "is_platform": False,
        "is_public": True
    }