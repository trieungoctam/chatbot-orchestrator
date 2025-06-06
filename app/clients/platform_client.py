import aiohttp
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Union
import structlog
import json

from app.core.settings import settings
from app.core.database import async_session_factory
from app.crud.platform_crud import PlatformCRUD

logger = structlog.get_logger(__name__)


class PlatformClient:
    """Enhanced Platform client with database configuration support"""

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.session = None
        self._platform_configs_cache = {}  # Cache for Platform configurations
        self.rate_limiters = {}  # Rate limiting per Platform instance

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def get_platform_config(self, platform_id: Optional[Union[str, uuid.UUID]] = None) -> Dict[str, Any]:
        """Get Platform configuration from database."""
        try:
            # Convert string to UUID if needed
            if isinstance(platform_id, str) and platform_id != "default":
                platform_id = uuid.UUID(platform_id)

            # Check cache first
            cache_key = str(platform_id) if platform_id else "default"
            if cache_key in self._platform_configs_cache:
                config = self._platform_configs_cache[cache_key]
                # Check if config is still fresh (cache for 5 minutes)
                if time.time() - config.get("_cached_at", 0) < 300:
                    return config

            async with async_session_factory() as session:
                platform_crud = PlatformCRUD(session)

                if platform_id and platform_id != "default":
                    # Get specific Platform configuration
                    platform = await platform_crud.get_by_id(platform_id)
                    if platform:
                        platform = platform.data  # Extract the actual platform object from response
                else:
                    # Get first active Platform configuration
                    active_platforms = await platform_crud.get_active(limit=1)
                    if active_platforms and active_platforms.data:
                        platform = active_platforms.data[0]  # Get first platform from response
                    else:
                        platform = None

                if not platform:
                    # Return default configuration
                    logger.info("No Platform configuration found, using default",
                               requested_id=str(platform_id) if platform_id else "None")

                    default_config = {
                        "id": "default",
                        "name": "Default Platform",
                        "base_url": "http://localhost:8000",
                        "rate_limit_per_minute": 60,
                        "auth_token": None,
                        "meta_data": {},
                        "_cached_at": time.time()
                    }

                    # Cache the default configuration
                    self._platform_configs_cache[cache_key] = default_config
                    return default_config

                if not platform.is_active:
                    logger.warning("Platform configuration is inactive, using default",
                                 platform_id=str(platform.id))

                    default_config = {
                        "id": "default",
                        "name": "Default Platform",
                        "base_url": "http://localhost:8000",
                        "rate_limit_per_minute": 60,
                        "auth_token": None,
                        "meta_data": {},
                        "_cached_at": time.time()
                    }

                    # Cache the default configuration
                    self._platform_configs_cache["default"] = default_config
                    return default_config

                # Build configuration
                config = {
                    "id": str(platform.id),
                    "name": platform.name,
                    "base_url": platform.base_url,
                    "rate_limit_per_minute": platform.rate_limit_per_minute,
                    "auth_token": platform.auth_token,
                    "meta_data": platform.meta_data or {},
                    "_cached_at": time.time()
                }

                # Cache the configuration
                self._platform_configs_cache[cache_key] = config
                return config

        except Exception as e:
            logger.error("Failed to get Platform configuration",
                        platform_id=str(platform_id), error=str(e))

            # Return default configuration as fallback
            logger.info("Returning default Platform configuration as fallback")
            default_config = {
                "id": "default",
                "name": "Default Platform",
                "base_url": "http://localhost:8000",
                "rate_limit_per_minute": 60,
                "auth_token": None,
                "meta_data": {},
                "_cached_at": time.time()
            }
            return default_config

    def _prepare_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare headers for Platform API request."""
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        # Add authentication if available
        if config.get("auth_token"):
            headers["Authorization"] = f"Bearer {config['auth_token']}"

        return headers

    async def _check_rate_limit(self, config: Dict[str, Any]) -> bool:
        """Check rate limiting for Platform instance."""
        platform_id = config["platform_id"]
        rate_limit = config.get("rate_limit_per_minute", 60)

        current_time = time.time()

        if platform_id not in self.rate_limiters:
            self.rate_limiters[platform_id] = {
                "requests": [],
                "limit": rate_limit
            }

        limiter = self.rate_limiters[platform_id]

        # Remove requests older than 1 minute
        limiter["requests"] = [
            req_time for req_time in limiter["requests"]
            if current_time - req_time < 60
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

    async def get_conversation_history(
        self,
        conversation_id: str,
        platform_config: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get conversation history from Platform service with database config."""
        try:
            # Get Platform configuration
            config = platform_config

            # Check rate limiting
            if not await self._check_rate_limit(config):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "conversation_id": conversation_id,
                    "messages": []
                }

            session = await self._get_session()

            # Construct the URL for getting conversation history
            base_url = config["base_url"]
            url = f"{base_url.rstrip('/')}/history-chat"

            # Prepare headers
            headers = self._prepare_headers(config)

            # Prepare query parameters
            params = {
                "conversation_id": conversation_id
            }

            if params:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(params)}"

            logger.info("Fetching conversation history from Platform",
                       conversation_id=conversation_id,
                       platform_name=config["name"],
                       url=url)

            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    logger.info("Successfully retrieved conversation history",
                               conversation_id=conversation_id,
                               platform_name=config["name"],
                               message_count=len(data.get("messages", [])))

                    return {
                        "success": True,
                        "conversation_id": conversation_id,
                        "history": data.get("history", ""),
                        "resources": data.get("resources", {})
                    }

                else:
                    error_text = await response.text()
                    logger.error("Failed to get conversation history",
                               conversation_id=conversation_id,
                               platform_name=config["name"],
                               status=response.status,
                               error=error_text)

                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "conversation_id": conversation_id,
                        "history": "",
                        "resources": {}
                    }

        except Exception as e:
            logger.error("Exception while getting conversation history",
                        conversation_id=conversation_id,
                        error=str(e))

            return {
                "success": False,
                "error": str(e),
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
        """Send bot response to Platform service with database config."""
        try:
            # Get Platform configuration
            config = platform_config

            # Check rate limiting
            if not await self._check_rate_limit(config):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "conversation_id": conversation_id,
                    "status": "rate_limited"
                }

            session = await self._get_session()

            # Construct the URL for sending message
            base_url = config["base_url"]
            url = f"{base_url.rstrip('/')}/send-message"

            # Prepare headers
            headers = self._prepare_headers(config)

            # Prepare payload
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
                       platform_name=config["name"],
                       content_preview=message_content[:100])

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()

                    logger.info("Successfully sent bot response",
                               conversation_id=conversation_id,
                               platform_name=config["name"],
                               message_id=data.get("message_id"))

                    return {
                        "success": True,
                        "conversation_id": conversation_id,
                        "message_id": data.get("message_id"),
                        "timestamp": data.get("timestamp"),
                        "status": "sent",
                    }

                else:
                    error_text = await response.text()
                    logger.error("Failed to send bot response",
                               conversation_id=conversation_id,
                               platform_name=config["name"],
                               status=response.status,
                               error=error_text)

                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "conversation_id": conversation_id,
                        "status": "failed"
                    }

        except Exception as e:
            logger.error("Exception while sending bot response",
                        conversation_id=conversation_id,
                        error=str(e))

            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id,
                "status": "failed"
            }

    async def notify_message_received(
        self,
        conversation_id: str,
        message_id: str,
        platform_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Notify Platform that message was received and processing started."""
        try:
            # Get Platform configuration
            config = platform_config

            # Check rate limiting
            if not await self._check_rate_limit(config):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "conversation_id": conversation_id,
                    "message_id": message_id
                }

            session = await self._get_session()

            # Construct the URL for notification
            base_url = config["base_url"]
            url = f"{base_url.rstrip('/')}/update-message-status"

            # Prepare headers
            headers = self._prepare_headers(config)

            # Prepare payload
            payload = {
                "message_id": message_id,
                "status": "processing",
                "processor": "chat-orchestrator",
                "processor_version": settings.API_VERSION,
                "timestamp": time.time()
            }

            logger.info("Notifying Platform of message processing",
                       conversation_id=conversation_id,
                       message_id=message_id,
                       platform_name=config["name"])

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()

                    logger.info("Successfully notified Platform",
                               conversation_id=conversation_id,
                               message_id=message_id,
                               platform_name=config["name"])

                    return {
                        "success": True,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "notification_id": data.get("notification_id"),
                        "platform_provider": config["name"]
                    }

                else:
                    error_text = await response.text()
                    logger.warning("Failed to notify Platform (non-critical)",
                                 conversation_id=conversation_id,
                                 message_id=message_id,
                                 platform_name=config["name"],
                                 status=response.status,
                                 error=error_text)

                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "platform_provider": config["name"]
                    }

        except Exception as e:
            logger.warning("Exception while notifying Platform (non-critical)",
                          conversation_id=conversation_id,
                          message_id=message_id,
                          error=str(e))

            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id,
                "message_id": message_id
            }

    async def get_bot_configuration(
        self,
        bot_id: str,
        platform_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get bot configuration from Platform service."""
        try:
            # Get Platform configuration
            config = platform_config

            # Check rate limiting
            if not await self._check_rate_limit(config):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "bot_id": bot_id,
                    "config": {}
                }

            session = await self._get_session()

            # Construct the URL for getting bot config
            base_url = config["base_url"]
            url = f"{base_url.rstrip('/')}/get-bot-config"

            # Prepare headers
            headers = self._prepare_headers(config)

            logger.info("Fetching bot configuration from Platform",
                       bot_id=bot_id,
                       platform_name=config["name"],
                       url=url)

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    logger.info("Successfully retrieved bot configuration",
                               bot_id=bot_id,
                               platform_name=config["name"])

                    return {
                        "success": True,
                        "bot_id": bot_id,
                        "config": data,
                    }

                else:
                    error_text = await response.text()
                    logger.error("Failed to get bot configuration",
                               bot_id=bot_id,
                               platform_name=config["name"],
                               status=response.status,
                               error=error_text)

                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "bot_id": bot_id,
                        "config": {}
                    }

        except Exception as e:
            logger.error("Exception while getting bot configuration",
                        bot_id=bot_id,
                        error=str(e))

            return {
                "success": False,
                "error": str(e),
                "bot_id": bot_id,
                "config": {}
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
        """Execute a Platform action (e.g., NEED_SUPPORT, NEED_SALE)."""
        try:
            # Get Platform configuration
            config = platform_config

            # Check rate limiting
            if not await self._check_rate_limit(config):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "action_type": ai_action,
                    "conversation_id": conversation_id
                }

            session = await self._get_session()

            # Construct the URL for action execution
            url = f"{url.rstrip('/')}"

            # Prepare headers
            headers = self._prepare_headers(config)

            if ai_action == "CHAT":
                payload = {
                    "conversation_id": conversation_id,
                    "response": {
                        "answers": ai_response.get("answer", []),
                        "images": ai_response.get("images", []),
                        "sub_answers": ai_response.get("sub_answer", [])
                    }
                }
            elif ai_action == "CREATE_ORDER":
                chat_url = f"{config['base_url'].rstrip('/')}/send-message"
                chat_ai_response = {
                    "answer": [ai_response.get("answer", "")],
                    "images": ai_response.get("images", []),
                    "sub_answer": [ai_response.get("sub_answer", "")]
                }
                result = await self.execute_platform_action(
                    platform_config=config,
                    url=chat_url,
                    method="POST",
                    meta_data=meta_data,
                    conversation_id=conversation_id,
                    ai_response=chat_ai_response,
                    ai_action="CHAT"
                )

                product_id = ai_response.get("product_id", "")
                try:
                    product_id = int(product_id)
                except:
                    product_id = 0

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
                            "product_code": str(product_id),
                            "product_id_mapping": product_id,
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

            elif ai_action == "NOTIFY":
                payload = {
                    "conversation_id": conversation_id,
                    "phone": ai_response.get("phone", ""),
                    "intent": ai_response.get("intent", "")
                }

            print("=========== PAYLOAD PLATFORM CLIENT ===========")
            print(payload)
            print("=========== PAYLOAD PLATFORM CLIENT ===========")

            # TODO: Implement execute_map
            # execute_map = {
            #     "POST": session.post,
            #     "GET": session.get,
            #     "PUT": session.put,
            #     "DELETE": session.delete
            # }

            logger.info("Executing Platform action",
                       conversation_id=conversation_id,
                       action_type=ai_action,
                       platform_name=config["name"])

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()

                    logger.info("Successfully executed Platform action",
                               conversation_id=conversation_id,
                               action_type=ai_action,
                               platform_name=config["name"],
                               action_id=data.get("action_id"))

                    print("Done action: ", ai_action)

                    return {
                        "success": True,
                        "conversation_id": conversation_id,
                    }

                else:
                    error_text = await response.text()
                    logger.error("Failed to execute Platform action",
                               conversation_id=conversation_id,
                               action_type=ai_action,
                               platform_name=config["name"],
                               status=response.status,
                               error=error_text)

                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "conversation_id": conversation_id,
                    }

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
            config = platform_config

            # Create a simple health check endpoint
            base_url = config["base_url"]
            health_endpoint = f"{base_url.rstrip('/')}/health"

            session = await self._get_session()
            headers = self._prepare_headers(config)

            async with session.get(health_endpoint, headers=headers) as response:
                is_healthy = response.status == 200

                logger.debug("Platform health check",
                           platform_name=config["name"],
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
                    for platform in active_platforms
                ]

        except Exception as e:
            logger.error("Failed to list Platform configurations", error=str(e))
            return []

    def clear_cache(self):
        """Clear the Platform configuration cache."""
        self._platform_configs_cache.clear()
        logger.info("Platform configuration cache cleared")

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instances
platform_client = PlatformClient()

def get_platform_client() -> PlatformClient:
    """Get the enhanced Platform client instance."""
    return platform_client