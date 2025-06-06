import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, Union, List
import httpx
import structlog

from app.core.settings import settings
from app.core.database import async_session_factory
from app.crud.core_ai_crud import CoreAICRUD

logger = structlog.get_logger(__name__)


class DatabaseAIService:
    """Enhanced AI Service that uses CoreAI configuration from database"""

    def __init__(self):
        self.default_timeout = 30
        self._ai_configs_cache = {}  # Simple cache for AI configurations

    async def get_ai_config(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> Dict[str, Any]:
        """Get AI configuration from database."""
        try:
            # Handle default case
            if core_ai_id == "default" or not core_ai_id:
                core_ai_id = None
            # Convert string to UUID if needed (but not for "default")
            elif isinstance(core_ai_id, str):
                try:
                    core_ai_id = uuid.UUID(core_ai_id)
                except ValueError:
                    # If it's not a valid UUID string, treat it as None (use default)
                    logger.warning("Invalid UUID format for core_ai_id, using default",
                                 core_ai_id=core_ai_id)
                    core_ai_id = None

            # Check cache first
            cache_key = str(core_ai_id) if core_ai_id else "default"
            if cache_key in self._ai_configs_cache:
                config = self._ai_configs_cache[cache_key]
                # Check if config is still fresh (cache for 5 minutes)
                if time.time() - config.get("_cached_at", 0) < 300:
                    return config

            async with async_session_factory() as session:
                ai_crud = CoreAICRUD(session)

                if core_ai_id:
                    # Get specific AI configuration
                    core_ai = await ai_crud.get_by_id(core_ai_id)
                else:
                    # Get first active AI configuration or return default config
                    active_ais = await ai_crud.get_active(limit=1)
                    # Extract the actual entity from the response list
                    if active_ais and len(active_ais) > 0:
                        # active_ais is a list of response objects, get the first one
                        first_ai_response = active_ais[0]
                        # Get the actual entity by ID
                        core_ai = await ai_crud.get_by_id(uuid.UUID(first_ai_response.id))
                    else:
                        core_ai = None

                if not core_ai:
                    # Return default configuration instead of raising error
                    logger.info("No CoreAI configuration found, using default",
                               requested_id=str(core_ai_id) if core_ai_id else "None")

                    default_config = {
                        "id": "default",
                        "name": "Default AI Service",
                        "api_endpoint": "http://localhost:8000",
                        "timeout_seconds": self.default_timeout,
                        "auth_required": False,
                        "auth_token": None,
                        "meta_data": {},
                        "_cached_at": time.time()
                    }

                    # Cache the default configuration
                    self._ai_configs_cache[cache_key] = default_config
                    return default_config

                if not core_ai.is_active:
                    logger.warning("CoreAI configuration is inactive, using default",
                                 core_ai_id=str(core_ai.id))

                    default_config = {
                        "id": "default",
                        "name": "Default AI Service",
                        "api_endpoint": "http://localhost:8000",
                        "timeout_seconds": self.default_timeout,
                        "auth_required": False,
                        "auth_token": None,
                        "meta_data": {},
                        "_cached_at": time.time()
                    }

                    # Cache the default configuration
                    self._ai_configs_cache["default"] = default_config
                    return default_config

                # Build configuration
                config = {
                    "id": str(core_ai.id),
                    "name": core_ai.name,
                    "api_endpoint": core_ai.api_endpoint,
                    "timeout_seconds": core_ai.timeout_seconds or self.default_timeout,
                    "auth_required": core_ai.auth_required,
                    "auth_token": core_ai.auth_token,
                    "meta_data": core_ai.meta_data or {},
                    "_cached_at": time.time()
                }

                # Cache the configuration
                self._ai_configs_cache[cache_key] = config
                return config

        except Exception as e:
            logger.error("Failed to get AI configuration",
                        core_ai_id=str(core_ai_id), error=str(e))

            # Return default configuration as fallback
            logger.info("Returning default AI configuration as fallback")
            default_config = {
                "id": "default",
                "name": "Default AI Service",
                "api_endpoint": "http://localhost:8000",
                "timeout_seconds": self.default_timeout,
                "auth_required": False,
                "auth_token": None,
                "meta_data": {},
                "_cached_at": time.time()
            }
            return default_config

    def _prepare_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare headers for AI API request."""
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        # Add authentication if required
        if config.get("auth_required") and config.get("auth_token"):
            headers["Authorization"] = f"Bearer {config['auth_token']}"
            logger.debug("Auth added for AI service", ai_name=config.get("name"))

        return headers

    async def process_message(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        core_ai_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Dict[str, Any]:
        """Process messages through database-configured AI service."""
        start_time = time.time()

        try:
            # Get AI configuration from database
            config = await self.get_ai_config(core_ai_id)
            api_endpoint = config.get("api_endpoint")
            api_endpoint = api_endpoint.replace("{session_id}", conversation_id)

            logger.info("Processing messages with AI",
                       conversation_id=conversation_id,
                       ai_name=config["name"],
                       ai_id=config["id"],
                       message_count=len(messages))

            resources = context.get("resources", {})
            lock_id = context.get("lock_id", "")

            if not lock_id:
                logger.error("Lock ID is required",
                             conversation_id=conversation_id,
                             ai_name=config["name"],
                             ai_id=config["id"])
                return {
                    "success": False,
                    "error": "Lock ID is required"
                }

            try:
                lock_id = int(lock_id)
            except ValueError:
                # TODO: Implement this
                # logger.error("Invalid lock ID",
                #              conversation_id=conversation_id,
                #              ai_name=config["name"],
                #              ai_id=config["id"])
                # return {
                #     "success": False,
                #     "error": "Invalid lock ID"
                # }
                lock_id = int(time.time())

            # Prepare request payload with array format
            payload = {
                "index": lock_id,
                "messages": messages,  # Use array format instead of single message
                "resource": resources or {}
            }

            print("=========== PAYLOAD ===========")
            print(payload)
            print("=========== PAYLOAD ===========")

            # Add AI-specific context from meta_data
            # if config.get("meta_data"):
            #     payload["ai_config"] = config["meta_data"]

            # Prepare headers
            headers = self._prepare_headers(config)

            # Make API call
            timeout = config.get("timeout_seconds", self.default_timeout)

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    api_endpoint,
                    json=payload,
                    headers=headers
                )

                processing_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    result = response.json()
                    action = result.get("action", "")
                    data = result.get("data", {})

                    logger.info("AI processing successful",
                               conversation_id=conversation_id,
                               ai_name=config["name"],
                               processing_time_ms=processing_time)

                    return {
                        "success": True,
                        "action": action,
                        "data": data,
                        "processing_time_ms": processing_time,
                    }
                else:
                    logger.error("AI processing failed",
                               conversation_id=conversation_id,
                               ai_name=config["name"],
                               status_code=response.status_code,
                               response_text=response.text[:200])

                    return {
                        "success": False,
                        "error": f"AI service returned {response.status_code}: {response.text[:100]}",
                        "action": "",
                        "data": {},
                        "processing_time_ms": processing_time,
                    }

        except httpx.TimeoutException:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("AI processing timeout",
                        conversation_id=conversation_id,
                        timeout=timeout)
            return {
                "success": False,
                "error": f"AI service timeout after {timeout}s",
                "action": "",
                "data": {},
                "processing_time_ms": processing_time
            }

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("AI processing error",
                        conversation_id=conversation_id,
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "action": "",
                "data": {},
                "processing_time_ms": processing_time
            }

    async def process_job(
        self,
        job_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        core_ai_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Dict[str, Any]:
        """Process a job through AI service with job tracking."""
        logger.info("Starting AI job processing",
                   job_id=job_id,
                   conversation_id=conversation_id,
                   message_count=len(messages))

        # Add job context
        job_context = context or {}
        job_context.update({
            "job_id": job_id,
            "processing_type": "background_job",
            "started_at": time.time(),
            "message_count": len(messages),
            "lock_id": context.get("lock_id", "")
        })

        # Process the messages using array format
        result = await self.process_message(
            conversation_id=conversation_id,
            messages=messages,  # Pass messages array directly
            context=job_context,
            core_ai_id=core_ai_id
        )

        # Add job-specific fields
        result.update({
            "job_id": job_id,
            "job_status": "completed" if result["success"] else "failed"
        })

        logger.info("AI job processing completed",
                   job_id=job_id,
                   success=result["success"],
                   processing_time_ms=result.get("processing_time_ms"))

        return result

    async def health_check(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
        """Check if AI service is healthy."""
        try:
            config = await self.get_ai_config(core_ai_id)

            # Create a simple health check endpoint (adjust based on your AI API)
            health_endpoint = config["api_endpoint"].rstrip("/") + "/health"

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(health_endpoint)
                is_healthy = response.status_code == 200

                logger.debug("AI health check",
                           ai_name=config["name"],
                           healthy=is_healthy)

                return is_healthy

        except Exception as e:
            logger.error("AI health check failed",
                        core_ai_id=str(core_ai_id),
                        error=str(e))
            return False

    async def list_available_ais(self) -> List[Dict[str, Any]]:
        """List all available AI configurations."""
        try:
            async with async_session_factory() as session:
                ai_crud = CoreAICRUD(session)
                active_ais = await ai_crud.get_active()

                return [
                    {
                        "id": str(ai.id),
                        "name": ai.name,
                        "api_endpoint": ai.api_endpoint,
                        "timeout_seconds": ai.timeout_seconds,
                        "auth_required": ai.auth_required,
                        "meta_data": ai.meta_data
                    }
                    for ai in active_ais
                ]

        except Exception as e:
            logger.error("Failed to list AI configurations", error=str(e))
            return []

    def clear_cache(self):
        """Clear the AI configuration cache."""
        self._ai_configs_cache.clear()
        logger.info("AI configuration cache cleared")


# Create global instances
database_ai_service = DatabaseAIService()

def get_ai_service() -> DatabaseAIService:
    """Get AI service instance based on environment."""
    return database_ai_service