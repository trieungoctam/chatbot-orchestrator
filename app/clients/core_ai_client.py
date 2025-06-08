import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
import httpx
import structlog

from app.core.settings import settings
from app.core.database import async_session_factory
from app.crud.core_ai_crud import CoreAICRUD

logger = structlog.get_logger(__name__)

# Constants
CACHE_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2
HEALTH_CHECK_TIMEOUT = 5


@dataclass
class CoreAIConfig:
    """Core AI configuration data class."""
    id: str
    name: str
    api_endpoint: str
    timeout_seconds: int
    auth_required: bool
    auth_token: Optional[str]
    meta_data: Dict[str, Any]
    cached_at: float = 0.0

    @classmethod
    def default(cls) -> 'CoreAIConfig':
        """Create default AI configuration."""
        return cls(
            id="default",
            name="Default AI Service",
            api_endpoint="http://localhost:8000",
            timeout_seconds=DEFAULT_TIMEOUT,
            auth_required=False,
            auth_token=None,
            meta_data={},
            cached_at=time.time()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "api_endpoint": self.api_endpoint,
            "timeout_seconds": self.timeout_seconds,
            "auth_required": self.auth_required,
            "auth_token": self.auth_token,
            "meta_data": self.meta_data,
            "_cached_at": self.cached_at
        }

    def is_cache_fresh(self) -> bool:
        """Check if cached configuration is still fresh."""
        return time.time() - self.cached_at < CACHE_TIMEOUT_SECONDS

    def get_endpoint_with_session(self, conversation_id: str) -> str:
        """Get API endpoint with session ID replacement."""
        return self.api_endpoint.replace("{session_id}", conversation_id)


class CoreAIConfigManager:
    """Manages Core AI configurations with caching."""

    def __init__(self):
        self.cache: Dict[str, CoreAIConfig] = {}

    async def get_config(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> CoreAIConfig:
        """Get Core AI configuration with caching."""
        try:
            # Handle default case
            if core_ai_id == "default" or not core_ai_id:
                core_ai_id = None
            elif isinstance(core_ai_id, str):
                try:
                    core_ai_id = uuid.UUID(core_ai_id)
                except ValueError:
                    logger.warning("Invalid UUID format for core_ai_id, using default",
                                 core_ai_id=core_ai_id)
                    core_ai_id = None

            # Check cache first
            cache_key = str(core_ai_id) if core_ai_id else "default"
            if cache_key in self.cache and self.cache[cache_key].is_cache_fresh():
                return self.cache[cache_key]

            # Fetch from database
            config = await self._fetch_config_from_db(core_ai_id)

            # Cache the configuration
            self.cache[cache_key] = config
            return config

        except Exception as e:
            logger.error("Failed to get AI configuration",
                        core_ai_id=str(core_ai_id), error=str(e))
            return CoreAIConfig.default()

    async def _fetch_config_from_db(self, core_ai_id: Optional[Union[str, uuid.UUID]]) -> CoreAIConfig:
        """Fetch configuration from database."""
        async with async_session_factory() as session:
            ai_crud = CoreAICRUD(session)

            if core_ai_id:
                # Get specific AI configuration
                core_ai = await ai_crud.get_by_id(core_ai_id)
            else:
                # Get first active AI configuration
                active_ais = await ai_crud.get_active(limit=1)
                if active_ais and len(active_ais) > 0:
                    first_ai_response = active_ais[0]
                    core_ai = await ai_crud.get_by_id(uuid.UUID(first_ai_response.id))
                else:
                    core_ai = None

            if not core_ai or not core_ai.is_active:
                if core_ai and not core_ai.is_active:
                    logger.warning("CoreAI configuration is inactive, using default",
                                 core_ai_id=str(core_ai.id))
                else:
                    logger.info("No CoreAI configuration found, using default",
                               requested_id=str(core_ai_id) if core_ai_id else "None")
                return CoreAIConfig.default()

            # Build configuration
            return CoreAIConfig(
                id=str(core_ai.id),
                name=core_ai.name,
                api_endpoint=core_ai.api_endpoint,
                timeout_seconds=core_ai.timeout_seconds or DEFAULT_TIMEOUT,
                auth_required=core_ai.auth_required,
                auth_token=core_ai.auth_token,
                meta_data=core_ai.meta_data or {},
                cached_at=time.time()
            )

    def clear_cache(self):
        """Clear the configuration cache."""
        self.cache.clear()
        logger.info("AI configuration cache cleared")


class AIHTTPClient:
    """Handles HTTP operations for AI communication."""

    def prepare_headers(self, config: CoreAIConfig) -> Dict[str, str]:
        """Prepare headers for AI API request."""
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        if config.auth_required and config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
            logger.debug("Auth added for AI service", ai_name=config.name)

        return headers

    async def make_request_with_retry(
        self,
        config: CoreAIConfig,
        payload: Dict[str, Any],
        conversation_id: str
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        api_endpoint = config.get_endpoint_with_session(conversation_id)
        headers = self.prepare_headers(config)

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            start_time = time.time()
            retries = 0

            while retries <= MAX_RETRIES:
                try:
                    response = await client.post(
                        api_endpoint,
                        json=payload,
                        headers=headers
                    )

                    processing_time = int((time.time() - start_time) * 1000)

                    if response.status_code == 200:
                        result = response.json()

                        logger.info("AI processing successful",
                                   conversation_id=conversation_id,
                                   ai_name=config.name,
                                   processing_time_ms=processing_time)

                        self._log_request_response(payload, result)

                        return {
                            "success": True,
                            "action": result.get("action", ""),
                            "data": result.get("data", {}),
                            "processing_time_ms": processing_time,
                        }
                    else:
                        retries += 1
                        if retries <= MAX_RETRIES:
                            logger.warning("AI processing failed, retrying...",
                                          conversation_id=conversation_id,
                                          ai_name=config.name,
                                          status_code=response.status_code,
                                          attempt=retries,
                                          response_text=response.text[:200])
                            await asyncio.sleep(RETRY_DELAY_SECONDS)
                            continue

                        logger.error("AI processing failed after all retries",
                                    conversation_id=conversation_id,
                                    ai_name=config.name,
                                    status_code=response.status_code,
                                    response_text=response.text[:200])

                        return {
                            "success": False,
                            "error": f"AI service returned {response.status_code}: {response.text[:100]} (after {retries} retries)",
                            "action": "",
                            "data": {},
                            "processing_time_ms": processing_time,
                        }

                except Exception as e:
                    retries += 1
                    if retries <= MAX_RETRIES:
                        logger.warning("AI request failed with exception, retrying...",
                                      conversation_id=conversation_id,
                                      ai_name=config.name,
                                      error=str(e),
                                      attempt=retries)
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                        continue

                    logger.error("AI request failed with exception after all retries",
                                conversation_id=conversation_id,
                                ai_name=config.name,
                                error=str(e))

                    return {
                        "success": False,
                        "error": f"AI request failed: {str(e)} (after {retries} retries)",
                        "action": "",
                        "data": {},
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                    }

    async def health_check(self, config: CoreAIConfig) -> bool:
        """Check if AI service is healthy."""
        try:
            health_endpoint = config.api_endpoint.rstrip("/") + "/health"

            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                response = await client.get(health_endpoint)
                is_healthy = response.status_code == 200

                logger.debug("AI health check",
                           ai_name=config.name,
                           healthy=is_healthy)

                return is_healthy
        except Exception as e:
            logger.error("AI health check failed",
                        ai_name=config.name,
                        error=str(e))
            return False

    def _log_request_response(self, payload: Dict[str, Any], result: Dict[str, Any]):
        """Log request and response for debugging."""
        print("======== AI PAYLOAD ===========")
        print(json.dumps(payload, indent=4))
        print("======== AI PAYLOAD ===========")
        print("======== AI RESPONSE ===========")
        print(json.dumps(result, indent=4))
        print("======== AI RESPONSE ===========")


class PayloadBuilder:
    """Builds payloads for AI requests."""

    @staticmethod
    def build_message_payload(
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build payload for message processing."""
        resources = context.get("resources", {}) if context else {}
        lock_id = context.get("lock_id") if context else None

        # Handle lock_id validation and conversion
        if lock_id is None:
            logger.error("Lock ID is required", conversation_id=conversation_id)
            raise ValueError("Lock ID is required")

        # Ensure lock_id is an integer (it should already be from LockData.generate_lock_id())
        if isinstance(lock_id, str):
            try:
                lock_id = int(lock_id)
            except ValueError:
                logger.warning("Invalid lock_id format, generating new one",
                             conversation_id=conversation_id,
                             invalid_lock_id=lock_id)
                lock_id = int(time.time() * 1000)  # Use millisecond timestamp
        elif not isinstance(lock_id, int):
            logger.warning("Lock ID is not integer, generating new one",
                         conversation_id=conversation_id,
                         lock_id_type=type(lock_id).__name__)
            lock_id = int(time.time() * 1000)  # Use millisecond timestamp

        return {
            "index": lock_id,
            "messages": messages,
            "resource": resources or {}
        }

    @staticmethod
    def build_job_payload(
        job_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build payload for job processing."""
        job_context = context or {}
        job_context.update({
            "job_id": job_id,
            "processing_type": "background_job",
            "started_at": time.time(),
            "message_count": len(messages),
            "lock_id": context.get("lock_id") if context else None  # Keep original lock_id
        })

        return PayloadBuilder.build_message_payload(conversation_id, messages, job_context)


class DatabaseAIService:
    """Enhanced AI Service that uses CoreAI configuration from database."""

    def __init__(self):
        self.config_manager = CoreAIConfigManager()
        self.http_client = AIHTTPClient()
        self.payload_builder = PayloadBuilder()

    async def get_ai_config(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> Dict[str, Any]:
        """Get AI configuration from database."""
        config = await self.config_manager.get_config(core_ai_id)
        return config.to_dict()

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
            # Get AI configuration
            config = await self.config_manager.get_config(core_ai_id)

            logger.info("Processing messages with AI",
                       conversation_id=conversation_id,
                       ai_name=config.name,
                       ai_id=config.id,
                       message_count=len(messages))

            # Build payload
            try:
                payload = self.payload_builder.build_message_payload(
                    conversation_id, messages, context
                )
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": "",
                    "data": {},
                    "processing_time_ms": 0
                }

            # Make request with retry logic
            return await self.http_client.make_request_with_retry(
                config, payload, conversation_id
            )

        except httpx.TimeoutException:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("AI processing timeout",
                        conversation_id=conversation_id,
                        timeout=config.timeout_seconds if 'config' in locals() else DEFAULT_TIMEOUT)
            return {
                "success": False,
                "error": f"AI service timeout after {config.timeout_seconds if 'config' in locals() else DEFAULT_TIMEOUT}s",
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

        try:
            # Get AI configuration
            config = await self.config_manager.get_config(core_ai_id)

            # Build job payload
            try:
                payload = self.payload_builder.build_job_payload(
                    job_id, conversation_id, messages, context
                )
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": "",
                    "data": {},
                    "processing_time_ms": 0,
                    "job_id": job_id,
                    "job_status": "failed"
                }

            # Process the job
            result = await self.http_client.make_request_with_retry(
                config, payload, conversation_id
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

        except Exception as e:
            logger.error("AI job processing error",
                        job_id=job_id,
                        conversation_id=conversation_id,
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "action": "",
                "data": {},
                "processing_time_ms": 0,
                "job_id": job_id,
                "job_status": "failed"
            }

    async def health_check(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
        """Check if AI service is healthy."""
        try:
            config = await self.config_manager.get_config(core_ai_id)
            return await self.http_client.health_check(config)
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
        self.config_manager.clear_cache()


# Create global instances
database_ai_service = DatabaseAIService()

def get_ai_service() -> DatabaseAIService:
    """Get AI service instance based on environment."""
    return database_ai_service