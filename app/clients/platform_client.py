import aiohttp
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Union
import structlog
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlencode

from app.core.settings import settings
from app.core.database import async_session_factory
from app.crud.platform_crud import PlatformCRUD

logger = structlog.get_logger(__name__)

# Constants
CACHE_TIMEOUT_SECONDS = 300
DEFAULT_RATE_LIMIT = 60
DEFAULT_TIMEOUT = 30
RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass
class PlatformConfig:
    """Platform configuration data class."""
    id: str
    name: str
    base_url: str
    rate_limit_per_minute: int
    auth_token: Optional[str]
    meta_data: Dict[str, Any]
    cached_at: float = 0.0

    @classmethod
    def default(cls) -> 'PlatformConfig':
        """Create default platform configuration."""
        return cls(
            id="default",
            name="Default Platform",
            base_url="http://localhost:8000",
            rate_limit_per_minute=DEFAULT_RATE_LIMIT,
            auth_token=None,
            meta_data={},
            cached_at=time.time()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "auth_token": self.auth_token,
            "meta_data": self.meta_data,
            "_cached_at": self.cached_at
        }

    def is_cache_fresh(self) -> bool:
        """Check if cached configuration is still fresh."""
        return time.time() - self.cached_at < CACHE_TIMEOUT_SECONDS


class RateLimiter:
    """Handles rate limiting for platform instances."""

    def __init__(self):
        self.limiters: Dict[str, Dict[str, Any]] = {}

    def can_make_request(self, platform_id: str, rate_limit: int) -> bool:
        """Check if a request can be made within rate limits."""
        current_time = time.time()

        if platform_id not in self.limiters:
            self.limiters[platform_id] = {
                "requests": [],
                "limit": rate_limit
            }

        limiter = self.limiters[platform_id]

        # Remove requests older than the window
        limiter["requests"] = [
            req_time for req_time in limiter["requests"]
            if current_time - req_time < RATE_LIMIT_WINDOW_SECONDS
        ]

        # Check if we can make another request
        if len(limiter["requests"]) >= rate_limit:
            logger.warning("Rate limit exceeded for Platform",
                          platform_id=platform_id,
                          current_requests=len(limiter["requests"]),
                          limit=rate_limit)
            return False

        # Add current request
        limiter["requests"].append(current_time)
        return True


class PlatformConfigManager:
    """Manages platform configurations with caching."""

    def __init__(self):
        self.cache: Dict[str, PlatformConfig] = {}

    async def get_config(self, platform_id: Optional[Union[str, uuid.UUID]] = None) -> PlatformConfig:
        """Get platform configuration with caching."""
        try:
            # Convert string to UUID if needed
            if isinstance(platform_id, str) and platform_id != "default":
                platform_id = uuid.UUID(platform_id)

            # Check cache first
            cache_key = str(platform_id) if platform_id else "default"
            if cache_key in self.cache and self.cache[cache_key].is_cache_fresh():
                return self.cache[cache_key]

            # Fetch from database
            config = await self._fetch_config_from_db(platform_id)

            # Cache the configuration
            self.cache[cache_key] = config
            return config

        except Exception as e:
            logger.error("Failed to get Platform configuration",
                        platform_id=str(platform_id), error=str(e))
            return PlatformConfig.default()

    async def _fetch_config_from_db(self, platform_id: Optional[Union[str, uuid.UUID]]) -> PlatformConfig:
        """Fetch configuration from database."""
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            if platform_id and platform_id != "default":
                # Get specific Platform configuration
                platform_response = await platform_crud.get_by_id(platform_id)
                platform = platform_response.data if platform_response else None
            else:
                # Get first active Platform configuration
                active_platforms = await platform_crud.get_active(limit=1)
                platform = active_platforms.data[0] if active_platforms and active_platforms.data else None

            if not platform or not platform.is_active:
                if platform and not platform.is_active:
                    logger.warning("Platform configuration is inactive, using default",
                                 platform_id=str(platform.id))
                else:
                    logger.info("No Platform configuration found, using default",
                               requested_id=str(platform_id) if platform_id else "None")
                return PlatformConfig.default()

            # Build configuration
            return PlatformConfig(
                id=str(platform.id),
                name=platform.name,
                base_url=platform.base_url,
                rate_limit_per_minute=platform.rate_limit_per_minute,
                auth_token=platform.auth_token,
                meta_data=platform.meta_data or {},
                cached_at=time.time()
            )

    def clear_cache(self):
        """Clear the configuration cache."""
        self.cache.clear()
        logger.info("Platform configuration cache cleared")


class HTTPClient:
    """Handles HTTP operations for platform communication."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    def prepare_headers(self, config: PlatformConfig) -> Dict[str, str]:
        """Prepare headers for API request."""
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"

        return headers

    async def make_request(
        self,
        method: str,
        url: str,
        config: PlatformConfig,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with common error handling."""
        session = await self.get_session()
        headers = self.prepare_headers(config)

        # Add query parameters to URL if provided
        if params:
            url = f"{url}?{urlencode(params)}"

        request_kwargs = {
            "headers": headers,
            "json": json_data
        } if json_data else {"headers": headers}

        try:
            async with session.request(method, url, **request_kwargs) as response:
                response_data = await response.json() if response.content_type == 'application/json' else await response.text()

                return {
                    "success": response.status in [200, 201],
                    "status": response.status,
                    "data": response_data,
                    "error": None if response.status in [200, 201] else f"HTTP {response.status}: {response_data}"
                }
        except Exception as e:
            return {
                "success": False,
                "status": 0,
                "data": None,
                "error": str(e)
            }

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


class PlatformActionExecutor:
    """Handles execution of different platform actions."""

    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client

    async def execute_action(
        self,
        action_type: str,
        config: PlatformConfig,
        conversation_id: str,
        ai_response: Dict[str, Any],
        meta_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute platform action based on type."""
        action_handlers = {
            "CHAT": self._handle_chat_action,
            "CREATE_ORDER": self._handle_create_order_action,
            "NOTIFY": self._handle_notify_action
        }

        handler = action_handlers.get(action_type)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "conversation_id": conversation_id
            }

        return await handler(config, conversation_id, ai_response, meta_data)

    async def _handle_chat_action(
        self,
        config: PlatformConfig,
        conversation_id: str,
        ai_response: Dict[str, Any],
        meta_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle CHAT action."""
        url = f"{config.base_url.rstrip('/')}/send-message"

        # Normalize answers
        answer = ai_response.get("answer", [])
        answers = [str(ans) for ans in (answer if isinstance(answer, list) else [answer])]

        sub_answer = ai_response.get("sub_answer", [])
        sub_answers = [str(ans) for ans in (sub_answer if isinstance(sub_answer, list) else [sub_answer])]

        payload = {
            "conversation_id": conversation_id,
            "response": {
                "answers": answers,
                "images": ai_response.get("images", []),
                "sub_answers": sub_answers
            }
        }

        return await self._execute_with_logging(
            "POST", url, config, payload, conversation_id, "CHAT"
        )

    async def _handle_create_order_action(
        self,
        config: PlatformConfig,
        conversation_id: str,
        ai_response: Dict[str, Any],
        meta_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle CREATE_ORDER action."""
        # First send chat response
        chat_ai_response = {
            "answer": ai_response.get("answer", []),
            "images": ai_response.get("images", []),
            "sub_answer": ai_response.get("sub_answer", [])
        }

        await self._handle_chat_action(config, conversation_id, chat_ai_response, meta_data)

        # Then create order
        url = f"{config.base_url.rstrip('/')}/create-order"

        payload = {
            "conversation_id": conversation_id,
            "customer_info": {
                "name": ai_response.get("customer_info", {}).get("name", ""),
                "phone": ai_response.get("customer_info", {}).get("phone", ""),
                "weight": ai_response.get("customer_info", {}).get("weight", ""),
                "height": ai_response.get("customer_info", {}).get("height", ""),
                "full_address": ai_response.get("customer_info", {}).get("full_address", ""),
                "district_name": ai_response.get("customer_info", {}).get("district_name", ""),
                "province_name": ai_response.get("customer_info", {}).get("province_name", ""),
                "ward_name": ai_response.get("customer_info", {}).get("ward_name", "")
            },
            "products": [
                {
                    "product_code": str(product.get("product_id", "0")),
                    "product_id_mapping": int(product.get("product_id", "0")),
                    "product_name": product.get("product_name", ""),
                    "quantity": product.get("quantity", 0),
                    "price": product.get("price", 0)
                }
                for product in ai_response.get("products", [])
            ],
            "shipping_fee": ai_response.get("shipping_fee", 0),
            "traffic_source": ai_response.get("traffic_source", ""),
            "note": ai_response.get("note", "")
        }

        return await self._execute_with_logging(
            "POST", url, config, payload, conversation_id, "CREATE_ORDER"
        )

    async def _handle_notify_action(
        self,
        config: PlatformConfig,
        conversation_id: str,
        ai_response: Dict[str, Any],
        meta_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle NOTIFY action."""
        url = f"{config.base_url.rstrip('/')}/notify"

        payload = {
            "conversation_id": conversation_id,
            "phone": ai_response.get("phone", ""),
            "intent": ai_response.get("intent", "")
        }

        return await self._execute_with_logging(
            "POST", url, config, payload, conversation_id, "NOTIFY"
        )

    async def _execute_with_logging(
        self,
        method: str,
        url: str,
        config: PlatformConfig,
        payload: Dict[str, Any],
        conversation_id: str,
        action_type: str
    ) -> Dict[str, Any]:
        """Execute request with consistent logging."""
        logger.info("Executing Platform action",
                   conversation_id=conversation_id,
                   action_type=action_type,
                   platform_name=config.name)

        result = await self.http_client.make_request(method, url, config, payload)

        if result["success"]:
            print("======== PLATFORM PAYLOAD ===========")
            print(json.dumps(payload, indent=4))
            print("======== PLATFORM PAYLOAD ===========")

            print("======== PLATFORM RESPONSE ===========")
            print(json.dumps(result["data"], indent=4))
            print("======== PLATFORM RESPONSE ===========")

            logger.info("Successfully executed Platform action",
                       conversation_id=conversation_id,
                       action_type=action_type,
                       platform_name=config.name)

            print("Done action: ", action_type)

            return {
                "success": True,
                "conversation_id": conversation_id,
            }
        else:
            logger.error("Failed to execute Platform action",
                       conversation_id=conversation_id,
                       action_type=action_type,
                       platform_name=config.name,
                       error=result["error"])

            return {
                "success": False,
                "error": result["error"],
                "conversation_id": conversation_id,
            }


class PlatformClient:
    """Enhanced Platform client with database configuration support."""

    def __init__(self):
        self.config_manager = PlatformConfigManager()
        self.rate_limiter = RateLimiter()
        self.http_client = HTTPClient()
        self.action_executor = PlatformActionExecutor(self.http_client)

    async def get_platform_config(self, platform_id: Optional[Union[str, uuid.UUID]] = None) -> Dict[str, Any]:
        """Get Platform configuration from database."""
        config = await self.config_manager.get_config(platform_id)
        return config.to_dict()

    async def get_conversation_history(
        self,
        conversation_id: str,
        platform_config: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get conversation history from Platform service."""
        config = PlatformConfig(**{k: v for k, v in platform_config.items() if k != "_cached_at"})

        # Check rate limiting
        if not self.rate_limiter.can_make_request(config.id, config.rate_limit_per_minute):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "conversation_id": conversation_id,
                "history": "",
                "resources": {}
            }

        url = f"{config.base_url.rstrip('/')}/history-chat"
        params = {"conversation_id": conversation_id}

        logger.info("Fetching conversation history from Platform",
                   conversation_id=conversation_id,
                   platform_name=config.name,
                   url=url)

        result = await self.http_client.make_request("POST", url, config, params=params)

        if result["success"]:
            data = result["data"]
            logger.info("Successfully retrieved conversation history",
                       conversation_id=conversation_id,
                       platform_name=config.name,
                       message_count=len(data.get("messages", [])))

            return {
                "success": True,
                "conversation_id": conversation_id,
                "history": data.get("history", ""),
                "resources": data.get("resources", {})
            }
        else:
            logger.error("Failed to get conversation history",
                       conversation_id=conversation_id,
                       platform_name=config.name,
                       error=result["error"])

            return {
                "success": False,
                "error": result["error"],
                "conversation_id": conversation_id,
                "history": "",
                "resources": {}
            }

    async def send_bot_response(
        self,
        conversation_id: str,
        message_content: str,
        platform_config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send bot response to Platform service."""
        config = PlatformConfig(**{k: v for k, v in platform_config.items() if k != "_cached_at"})

        # Check rate limiting
        if not self.rate_limiter.can_make_request(config.id, config.rate_limit_per_minute):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "conversation_id": conversation_id,
                "status": "rate_limited"
            }

        url = f"{config.base_url.rstrip('/')}/send-message"

        payload = {
            "content": message_content,
            "sender_type": "bot",
            "content_type": "text/plain",
            "metadata": metadata or {},
            "source": "chat-orchestrator",
            "timestamp": time.time()
        }

        logger.info("Sending bot response to Platform",
                   conversation_id=conversation_id,
                   platform_name=config.name,
                   content_preview=message_content[:100])

        result = await self.http_client.make_request("POST", url, config, payload)

        if result["success"]:
            data = result["data"]
            logger.info("Successfully sent bot response",
                       conversation_id=conversation_id,
                       platform_name=config.name,
                       message_id=data.get("message_id"))

            return {
                "success": True,
                "conversation_id": conversation_id,
                "message_id": data.get("message_id"),
                "timestamp": data.get("timestamp"),
                "status": "sent",
            }
        else:
            logger.error("Failed to send bot response",
                       conversation_id=conversation_id,
                       platform_name=config.name,
                       error=result["error"])

            return {
                "success": False,
                "error": result["error"],
                "conversation_id": conversation_id,
                "status": "failed"
            }

    async def execute_platform_action(
        self,
        platform_config: Dict[str, Any],
        url: str,
        method: str,
        meta_data: Dict[str, Any],
        conversation_id: str,
        ai_response: Dict[str, Any],
        ai_action: str,
    ) -> Dict[str, Any]:
        """Execute a Platform action (e.g., CHAT, CREATE_ORDER, NOTIFY)."""
        config = PlatformConfig(**{k: v for k, v in platform_config.items() if k != "_cached_at"})

        # Check rate limiting
        if not self.rate_limiter.can_make_request(config.id, config.rate_limit_per_minute):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "action_type": ai_action,
                "conversation_id": conversation_id
            }

        try:
            return await self.action_executor.execute_action(
                ai_action, config, conversation_id, ai_response, meta_data
            )
        except Exception as e:
            logger.error("Exception while executing Platform action",
                        conversation_id=conversation_id,
                        error=str(e))

            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id,
            }

    async def health_check(self, platform_config: Dict[str, Any]) -> bool:
        """Check if Platform service is healthy."""
        try:
            config = PlatformConfig(**{k: v for k, v in platform_config.items() if k != "_cached_at"})
            url = f"{config.base_url.rstrip('/')}/health"

            result = await self.http_client.make_request("GET", url, config)
            is_healthy = result["success"]

            logger.debug("Platform health check",
                       platform_name=config.name,
                       healthy=is_healthy)

            return is_healthy
        except Exception as e:
            logger.error("Platform health check failed",
                        platform_id=platform_config["id"],
                        error=str(e))
            return False

    async def list_available_platforms(self) -> List[Dict[str, Any]]:
        """List all available Platform configurations."""
        try:
            async with async_session_factory() as session:
                platform_crud = PlatformCRUD(session)
                active_platforms = await platform_crud.get_active()

                return [
                    {
                        "id": str(platform.id),
                        "name": platform.name,
                        "base_url": platform.base_url,
                        "rate_limit_per_minute": platform.rate_limit_per_minute,
                        "meta_data": platform.meta_data
                    }
                    for platform in active_platforms.data if active_platforms and active_platforms.data
                ]
        except Exception as e:
            logger.error("Failed to list Platform configurations", error=str(e))
            return []

    def clear_cache(self):
        """Clear the Platform configuration cache."""
        self.config_manager.clear_cache()

    async def close(self):
        """Close the aiohttp session"""
        await self.http_client.close()


# Global instances
platform_client = PlatformClient()

def get_platform_client() -> PlatformClient:
    """Get the enhanced Platform client instance."""
    return platform_client