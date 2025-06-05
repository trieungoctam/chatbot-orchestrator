# import aiohttp
# import asyncio
# import time
# import uuid
# from typing import Dict, Any, Optional, List, Union
# import structlog

# from app.core.settings import settings
# from app.core.database import async_session_factory
# from app.crud.pancake_crud import PancakeCRUD

# logger = structlog.get_logger(__name__)


# class EnhancedPancakeClient:
#     """Enhanced Pancake client with database configuration support"""

#     def __init__(self):
#         self.timeout = aiohttp.ClientTimeout(total=30)
#         self.session = None
#         self._pancake_configs_cache = {}  # Cache for Pancake configurations
#         self.rate_limiters = {}  # Rate limiting per Pancake instance

#     async def _get_session(self):
#         """Get or create aiohttp session"""
#         if self.session is None or self.session.closed:
#             self.session = aiohttp.ClientSession(timeout=self.timeout)
#         return self.session

#     async def get_pancake_config(self, pancake_id: Optional[Union[str, uuid.UUID]] = None) -> Dict[str, Any]:
#         """Get Pancake configuration from database."""
#         try:
#             # Convert string to UUID if needed
#             if isinstance(pancake_id, str):
#                 pancake_id = uuid.UUID(pancake_id)

#             # Check cache first
#             cache_key = str(pancake_id) if pancake_id else "default"
#             if cache_key in self._pancake_configs_cache:
#                 config = self._pancake_configs_cache[cache_key]
#                 # Check if config is still fresh (cache for 5 minutes)
#                 if time.time() - config.get("_cached_at", 0) < 300:
#                     return config

#             async with async_session_factory() as session:
#                 pancake_crud = PancakeCRUD(session)

#                 if pancake_id:
#                     # Get specific Pancake configuration
#                     pancake = await pancake_crud.get_by_id(pancake_id)
#                 else:
#                     # Get first active Pancake configuration
#                     active_pancakes = await pancake_crud.get_active(limit=1)
#                     pancake = active_pancakes[0] if active_pancakes else None

#                 if not pancake:
#                     raise ValueError(f"No active Pancake configuration found (ID: {pancake_id})")

#                 if not pancake.is_active:
#                     raise ValueError(f"Pancake configuration is inactive (ID: {pancake.id})")

#                 # Build configuration
#                 config = {
#                     "id": str(pancake.id),
#                     "name": pancake.name,
#                     "base_url": pancake.base_url,
#                     "rate_limit_per_minute": pancake.rate_limit_per_minute,
#                     "auth_token": pancake.auth_token,  # In production, decrypt this
#                     "meta_data": pancake.meta_data or {},
#                     "_cached_at": time.time()
#                 }

#                 # Cache the configuration
#                 self._pancake_configs_cache[cache_key] = config
#                 return config

#         except Exception as e:
#             logger.error("Failed to get Pancake configuration",
#                         pancake_id=str(pancake_id), error=str(e))
#             raise

#     def _prepare_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
#         """Prepare headers for Pancake API request."""
#         headers = {
#             "Content-Type": "application/json",
#             "User-Agent": f"ChatOrchestrator/{settings.API_VERSION}"
#         }

#         # Add authentication if available
#         if config.get("auth_token"):
#             headers["Authorization"] = f"Bearer {config['auth_token']}"

#         return headers

#     async def _check_rate_limit(self, config: Dict[str, Any]) -> bool:
#         """Check rate limiting for Pancake instance."""
#         pancake_id = config["id"]
#         rate_limit = config.get("rate_limit_per_minute", 60)

#         current_time = time.time()

#         if pancake_id not in self.rate_limiters:
#             self.rate_limiters[pancake_id] = {
#                 "requests": [],
#                 "limit": rate_limit
#             }

#         limiter = self.rate_limiters[pancake_id]

#         # Remove requests older than 1 minute
#         limiter["requests"] = [
#             req_time for req_time in limiter["requests"]
#             if current_time - req_time < 60
#         ]

#         # Check if we can make another request
#         if len(limiter["requests"]) >= rate_limit:
#             logger.warning("Rate limit exceeded for Pancake",
#                           pancake_id=pancake_id,
#                           current_requests=len(limiter["requests"]),
#                           limit=rate_limit)
#             return False

#         # Add current request
#         limiter["requests"].append(current_time)
#         return True

#     async def get_conversation_history(
#         self,
#         conversation_id: str,
#         pancake_id: Optional[Union[str, uuid.UUID]] = None,
#         limit: int = 20
#     ) -> Dict[str, Any]:
#         """Get conversation history from Pancake service with database config."""
#         try:
#             # Get Pancake configuration
#             config = await self.get_pancake_config(pancake_id)

#             # Check rate limiting
#             if not await self._check_rate_limit(config):
#                 return {
#                     "success": False,
#                     "error": "Rate limit exceeded",
#                     "conversation_id": conversation_id,
#                     "messages": []
#                 }

#             session = await self._get_session()

#             # Construct the URL for getting conversation history
#             base_url = config["base_url"]
#             url = f"{base_url.rstrip('/')}/api/v1/conversations/{conversation_id}/history"

#             # Prepare headers
#             headers = self._prepare_headers(config)

#             # Prepare query parameters
#             params = {
#                 "limit": limit,
#                 "order": "desc"  # Most recent first
#             }

#             logger.info("Fetching conversation history from Pancake",
#                        conversation_id=conversation_id,
#                        pancake_name=config["name"],
#                        url=url)

#             async with session.get(url, headers=headers, params=params) as response:
#                 if response.status == 200:
#                     data = await response.json()

#                     logger.info("Successfully retrieved conversation history",
#                                conversation_id=conversation_id,
#                                pancake_name=config["name"],
#                                message_count=len(data.get("messages", [])))

#                     return {
#                         "success": True,
#                         "conversation_id": conversation_id,
#                         "messages": data.get("messages", []),
#                         "total_count": data.get("total_count", 0),
#                         "metadata": data.get("metadata", {}),
#                         "pancake_provider": config["name"],
#                         "pancake_id": config["id"]
#                     }

#                 else:
#                     error_text = await response.text()
#                     logger.error("Failed to get conversation history",
#                                conversation_id=conversation_id,
#                                pancake_name=config["name"],
#                                status=response.status,
#                                error=error_text)

#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "conversation_id": conversation_id,
#                         "messages": [],
#                         "pancake_provider": config["name"]
#                     }

#         except Exception as e:
#             logger.error("Exception while getting conversation history",
#                         conversation_id=conversation_id,
#                         error=str(e))

#             return {
#                 "success": False,
#                 "error": str(e),
#                 "conversation_id": conversation_id,
#                 "messages": []
#             }

#     async def send_bot_response(
#         self,
#         conversation_id: str,
#         message_content: str,
#         pancake_id: Optional[Union[str, uuid.UUID]] = None,
#         metadata: Optional[Dict[str, Any]] = None
#     ) -> Dict[str, Any]:
#         """Send bot response to Pancake service with database config."""
#         try:
#             # Get Pancake configuration
#             config = await self.get_pancake_config(pancake_id)

#             # Check rate limiting
#             if not await self._check_rate_limit(config):
#                 return {
#                     "success": False,
#                     "error": "Rate limit exceeded",
#                     "conversation_id": conversation_id,
#                     "status": "rate_limited"
#                 }

#             session = await self._get_session()

#             # Construct the URL for sending message
#             base_url = config["base_url"]
#             url = f"{base_url.rstrip('/')}/api/v1/conversations/{conversation_id}/messages"

#             # Prepare headers
#             headers = self._prepare_headers(config)

#             # Prepare payload
#             payload = {
#                 "content": message_content,
#                 "sender_type": "bot",
#                 "content_type": "text/plain",
#                 "metadata": metadata or {},
#                 "source": "chat-orchestrator",
#                 "timestamp": time.time()
#             }

#             logger.info("Sending bot response to Pancake",
#                        conversation_id=conversation_id,
#                        pancake_name=config["name"],
#                        content_preview=message_content[:100])

#             async with session.post(url, headers=headers, json=payload) as response:
#                 if response.status in [200, 201]:
#                     data = await response.json()

#                     logger.info("Successfully sent bot response",
#                                conversation_id=conversation_id,
#                                pancake_name=config["name"],
#                                message_id=data.get("message_id"))

#                     return {
#                         "success": True,
#                         "conversation_id": conversation_id,
#                         "message_id": data.get("message_id"),
#                         "timestamp": data.get("timestamp"),
#                         "status": "sent",
#                         "pancake_provider": config["name"],
#                         "pancake_id": config["id"]
#                     }

#                 else:
#                     error_text = await response.text()
#                     logger.error("Failed to send bot response",
#                                conversation_id=conversation_id,
#                                pancake_name=config["name"],
#                                status=response.status,
#                                error=error_text)

#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "conversation_id": conversation_id,
#                         "status": "failed",
#                         "pancake_provider": config["name"]
#                     }

#         except Exception as e:
#             logger.error("Exception while sending bot response",
#                         conversation_id=conversation_id,
#                         error=str(e))

#             return {
#                 "success": False,
#                 "error": str(e),
#                 "conversation_id": conversation_id,
#                 "status": "failed"
#             }

#     async def notify_message_received(
#         self,
#         conversation_id: str,
#         message_id: str,
#         pancake_id: Optional[Union[str, uuid.UUID]] = None
#     ) -> Dict[str, Any]:
#         """Notify Pancake that message was received and processing started."""
#         try:
#             # Get Pancake configuration
#             config = await self.get_pancake_config(pancake_id)

#             # Check rate limiting
#             if not await self._check_rate_limit(config):
#                 return {
#                     "success": False,
#                     "error": "Rate limit exceeded",
#                     "conversation_id": conversation_id,
#                     "message_id": message_id
#                 }

#             session = await self._get_session()

#             # Construct the URL for notification
#             base_url = config["base_url"]
#             url = f"{base_url.rstrip('/')}/api/v1/conversations/{conversation_id}/status"

#             # Prepare headers
#             headers = self._prepare_headers(config)

#             # Prepare payload
#             payload = {
#                 "message_id": message_id,
#                 "status": "processing",
#                 "processor": "chat-orchestrator",
#                 "processor_version": settings.API_VERSION,
#                 "timestamp": time.time()
#             }

#             logger.info("Notifying Pancake of message processing",
#                        conversation_id=conversation_id,
#                        message_id=message_id,
#                        pancake_name=config["name"])

#             async with session.post(url, headers=headers, json=payload) as response:
#                 if response.status in [200, 201]:
#                     data = await response.json()

#                     logger.info("Successfully notified Pancake",
#                                conversation_id=conversation_id,
#                                message_id=message_id,
#                                pancake_name=config["name"])

#                     return {
#                         "success": True,
#                         "conversation_id": conversation_id,
#                         "message_id": message_id,
#                         "notification_id": data.get("notification_id"),
#                         "pancake_provider": config["name"]
#                     }

#                 else:
#                     error_text = await response.text()
#                     logger.warning("Failed to notify Pancake (non-critical)",
#                                  conversation_id=conversation_id,
#                                  message_id=message_id,
#                                  pancake_name=config["name"],
#                                  status=response.status,
#                                  error=error_text)

#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "conversation_id": conversation_id,
#                         "message_id": message_id,
#                         "pancake_provider": config["name"]
#                     }

#         except Exception as e:
#             logger.warning("Exception while notifying Pancake (non-critical)",
#                           conversation_id=conversation_id,
#                           message_id=message_id,
#                           error=str(e))

#             return {
#                 "success": False,
#                 "error": str(e),
#                 "conversation_id": conversation_id,
#                 "message_id": message_id
#             }

#     async def get_bot_configuration(
#         self,
#         bot_id: str,
#         pancake_id: Optional[Union[str, uuid.UUID]] = None
#     ) -> Dict[str, Any]:
#         """Get bot configuration from Pancake service."""
#         try:
#             # Get Pancake configuration
#             config = await self.get_pancake_config(pancake_id)

#             # Check rate limiting
#             if not await self._check_rate_limit(config):
#                 return {
#                     "success": False,
#                     "error": "Rate limit exceeded",
#                     "bot_id": bot_id,
#                     "config": {}
#                 }

#             session = await self._get_session()

#             # Construct the URL for getting bot config
#             base_url = config["base_url"]
#             url = f"{base_url.rstrip('/')}/api/v1/bots/{bot_id}/config"

#             # Prepare headers
#             headers = self._prepare_headers(config)

#             logger.info("Fetching bot configuration from Pancake",
#                        bot_id=bot_id,
#                        pancake_name=config["name"],
#                        url=url)

#             async with session.get(url, headers=headers) as response:
#                 if response.status == 200:
#                     data = await response.json()

#                     logger.info("Successfully retrieved bot configuration",
#                                bot_id=bot_id,
#                                pancake_name=config["name"])

#                     return {
#                         "success": True,
#                         "bot_id": bot_id,
#                         "config": data,
#                         "pancake_provider": config["name"],
#                         "pancake_id": config["id"]
#                     }

#                 else:
#                     error_text = await response.text()
#                     logger.error("Failed to get bot configuration",
#                                bot_id=bot_id,
#                                pancake_name=config["name"],
#                                status=response.status,
#                                error=error_text)

#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "bot_id": bot_id,
#                         "config": {},
#                         "pancake_provider": config["name"]
#                     }

#         except Exception as e:
#             logger.error("Exception while getting bot configuration",
#                         bot_id=bot_id,
#                         error=str(e))

#             return {
#                 "success": False,
#                 "error": str(e),
#                 "bot_id": bot_id,
#                 "config": {}
#             }

#     async def execute_pancake_action(
#         self,
#         action_type: str,
#         action_data: Dict[str, Any],
#         conversation_id: str,
#         pancake_id: Optional[Union[str, uuid.UUID]] = None
#     ) -> Dict[str, Any]:
#         """Execute a Pancake action (e.g., NEED_SUPPORT, NEED_SALE)."""
#         try:
#             # Get Pancake configuration
#             config = await self.get_pancake_config(pancake_id)

#             # Check rate limiting
#             if not await self._check_rate_limit(config):
#                 return {
#                     "success": False,
#                     "error": "Rate limit exceeded",
#                     "action_type": action_type,
#                     "conversation_id": conversation_id
#                 }

#             session = await self._get_session()

#             # Construct the URL for action execution
#             base_url = config["base_url"]
#             url = f"{base_url.rstrip('/')}/api/v1/conversations/{conversation_id}/actions"

#             # Prepare headers
#             headers = self._prepare_headers(config)

#             # Prepare payload
#             payload = {
#                 "action_type": action_type,
#                 "action_data": action_data,
#                 "conversation_id": conversation_id,
#                 "executed_by": "chat-orchestrator",
#                 "timestamp": time.time()
#             }

#             logger.info("Executing Pancake action",
#                        conversation_id=conversation_id,
#                        action_type=action_type,
#                        pancake_name=config["name"])

#             async with session.post(url, headers=headers, json=payload) as response:
#                 if response.status in [200, 201]:
#                     data = await response.json()

#                     logger.info("Successfully executed Pancake action",
#                                conversation_id=conversation_id,
#                                action_type=action_type,
#                                pancake_name=config["name"],
#                                action_id=data.get("action_id"))

#                     return {
#                         "success": True,
#                         "conversation_id": conversation_id,
#                         "action_type": action_type,
#                         "action_id": data.get("action_id"),
#                         "result": data.get("result"),
#                         "pancake_provider": config["name"],
#                         "pancake_id": config["id"]
#                     }

#                 else:
#                     error_text = await response.text()
#                     logger.error("Failed to execute Pancake action",
#                                conversation_id=conversation_id,
#                                action_type=action_type,
#                                pancake_name=config["name"],
#                                status=response.status,
#                                error=error_text)

#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "conversation_id": conversation_id,
#                         "action_type": action_type,
#                         "pancake_provider": config["name"]
#                     }

#         except Exception as e:
#             logger.error("Exception while executing Pancake action",
#                         conversation_id=conversation_id,
#                         action_type=action_type,
#                         error=str(e))

#             return {
#                 "success": False,
#                 "error": str(e),
#                 "conversation_id": conversation_id,
#                 "action_type": action_type
#             }

#     async def health_check(self, pancake_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
#         """Check if Pancake service is healthy."""
#         try:
#             config = await self.get_pancake_config(pancake_id)

#             # Create a simple health check endpoint
#             base_url = config["base_url"]
#             health_endpoint = f"{base_url.rstrip('/')}/health"

#             session = await self._get_session()
#             headers = self._prepare_headers(config)

#             async with session.get(health_endpoint, headers=headers) as response:
#                 is_healthy = response.status == 200

#                 logger.debug("Pancake health check",
#                            pancake_name=config["name"],
#                            healthy=is_healthy)

#                 return is_healthy

#         except Exception as e:
#             logger.error("Pancake health check failed",
#                         pancake_id=str(pancake_id),
#                         error=str(e))
#             return False

#     async def list_available_pancakes(self) -> List[Dict[str, Any]]:
#         """List all available Pancake configurations."""
#         try:
#             async with async_session_factory() as session:
#                 pancake_crud = PancakeCRUD(session)
#                 active_pancakes = await pancake_crud.get_active()

#                 return [
#                     {
#                         "id": str(pancake.id),
#                         "name": pancake.name,
#                         "base_url": pancake.base_url,
#                         "rate_limit_per_minute": pancake.rate_limit_per_minute,
#                         "meta_data": pancake.meta_data
#                     }
#                     for pancake in active_pancakes
#                 ]

#         except Exception as e:
#             logger.error("Failed to list Pancake configurations", error=str(e))
#             return []

#     def clear_cache(self):
#         """Clear the Pancake configuration cache."""
#         self._pancake_configs_cache.clear()
#         logger.info("Pancake configuration cache cleared")

#     async def close(self):
#         """Close the aiohttp session"""
#         if self.session and not self.session.closed:
#             await self.session.close()


# # Legacy PancakeClient for backward compatibility
# class PancakeClient(EnhancedPancakeClient):
#     """Legacy Pancake client - redirects to enhanced version"""

#     async def get_conversation_history(
#         self,
#         conversation_id: str,
#         base_url: str,
#         limit: int = 20,
#         auth_token: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Legacy method - converts to new format"""
#         logger.warning("Using legacy PancakeClient method. Consider migrating to EnhancedPancakeClient")

#         # For legacy calls, we'll try to find a matching Pancake config by base_url
#         try:
#             available_pancakes = await self.list_available_pancakes()
#             matching_pancake = None

#             for pancake in available_pancakes:
#                 if pancake["base_url"] == base_url:
#                     matching_pancake = pancake
#                     break

#             if matching_pancake:
#                 return await super().get_conversation_history(
#                     conversation_id=conversation_id,
#                     pancake_id=matching_pancake["id"],
#                     limit=limit
#                 )
#             else:
#                 # Fallback to direct call
#                 return await self._legacy_get_conversation_history(
#                     conversation_id, base_url, limit, auth_token
#                 )

#         except Exception as e:
#             logger.error("Legacy method fallback failed", error=str(e))
#             return await self._legacy_get_conversation_history(
#                 conversation_id, base_url, limit, auth_token
#             )

#     async def _legacy_get_conversation_history(
#         self,
#         conversation_id: str,
#         base_url: str,
#         limit: int = 20,
#         auth_token: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Original implementation for backward compatibility"""
#         try:
#             session = await self._get_session()

#             url = f"{base_url.rstrip('/')}/api/v1/conversations/{conversation_id}/history"

#             headers = {
#                 "Content-Type": "application/json",
#                 "User-Agent": "ChatOrchestrator/1.0"
#             }

#             if auth_token:
#                 headers["Authorization"] = f"Bearer {auth_token}"

#             params = {
#                 "limit": limit,
#                 "order": "desc"
#             }

#             async with session.get(url, headers=headers, params=params) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     return {
#                         "success": True,
#                         "conversation_id": conversation_id,
#                         "messages": data.get("messages", []),
#                         "total_count": data.get("total_count", 0),
#                         "metadata": data.get("metadata", {})
#                     }
#                 else:
#                     error_text = await response.text()
#                     return {
#                         "success": False,
#                         "error": f"HTTP {response.status}: {error_text}",
#                         "conversation_id": conversation_id,
#                         "messages": []
#                     }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "conversation_id": conversation_id,
#                 "messages": []
#             }


# # Global instances
# enhanced_pancake_client = EnhancedPancakeClient()
# pancake_client = PancakeClient()  # For backward compatibility


# def get_pancake_client() -> EnhancedPancakeClient:
#     """Get the enhanced Pancake client instance."""
#     return enhanced_pancake_client