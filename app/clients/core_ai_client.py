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
            # Convert string to UUID if needed
            if isinstance(core_ai_id, str):
                core_ai_id = uuid.UUID(core_ai_id)

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
                    # Get first active AI configuration
                    active_ais = await ai_crud.get_active(limit=1)
                    core_ai = active_ais[0] if active_ais else None

                if not core_ai:
                    raise ValueError(f"No active CoreAI configuration found (ID: {core_ai_id})")

                if not core_ai.is_active:
                    raise ValueError(f"CoreAI configuration is inactive (ID: {core_ai.id})")

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
            raise

    def _prepare_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare headers for AI API request."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"ChatBot-Backend/{settings.API_VERSION}"
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

            logger.info("Processing messages with AI",
                       conversation_id=conversation_id,
                       ai_name=config["name"],
                       ai_id=config["id"],
                       message_count=len(messages))

            # Prepare request payload with array format
            payload = {
                "conversation_id": conversation_id,
                "messages": messages,  # Use array format instead of single message
                "context": context or {}
            }

            # Add AI-specific context from meta_data
            if config.get("meta_data"):
                payload["ai_config"] = config["meta_data"]

            # Prepare headers
            headers = self._prepare_headers(config)

            # Make API call
            timeout = config.get("timeout_seconds", self.default_timeout)

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    config["api_endpoint"],
                    json=payload,
                    headers=headers
                )

                processing_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    result = response.json()

                    logger.info("AI processing successful",
                               conversation_id=conversation_id,
                               ai_name=config["name"],
                               processing_time_ms=processing_time)

                    return {
                        "success": True,
                        "response": result.get("response", ""),
                        "actions": result.get("actions", []),
                        "intent": result.get("intent"),
                        "confidence": result.get("confidence"),
                        "processing_time_ms": processing_time,
                        "ai_provider": config["name"],
                        "ai_id": config["id"]
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
                        "response": "",
                        "actions": [],
                        "processing_time_ms": processing_time,
                        "ai_provider": config["name"],
                        "ai_id": config["id"]
                    }

        except httpx.TimeoutException:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("AI processing timeout",
                        conversation_id=conversation_id,
                        timeout=timeout)
            return {
                "success": False,
                "error": f"AI service timeout after {timeout}s",
                "response": "",
                "actions": [],
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
                "response": "",
                "actions": [],
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
            "message_count": len(messages)
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


class MockAIService:
    """Mock AI service for development and testing."""

    def __init__(self):
        self.processing_delay = 2.0  # Simulate processing time

    async def process_message(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        core_ai_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Dict[str, Any]:
        """Mock AI processing with simulated responses using message array."""
        await asyncio.sleep(self.processing_delay)

        # Get the last user message for response generation
        last_user_message = ""
        conversation_context = []

        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            conversation_context.append(f"{role}: {content}")

            if role == "user":
                last_user_message = content.lower()

        # Simple mock responses based on last user message content
        if "hello" in last_user_message or "hi" in last_user_message:
            response = "Hello! How can I help you today?"
            actions = []
            intent = "greeting"
            confidence = 0.95
        elif "appointment" in last_user_message or "book" in last_user_message:
            response = "I can help you book an appointment. What type of appointment do you need?"
            actions = [
                {
                    "type": "show_calendar",
                    "data": {"available_slots": ["2024-01-15 10:00", "2024-01-15 14:00"]}
                }
            ]
            intent = "book_appointment"
            confidence = 0.88
        elif "doctor" in last_user_message:
            response = "Here are our available doctors. Would you like to see their specializations?"
            actions = [
                {
                    "type": "list_doctors",
                    "data": {"doctors": ["Dr. Smith (Cardiology)", "Dr. Johnson (Neurology)"]}
                }
            ]
            intent = "find_doctor"
            confidence = 0.92
        elif "help" in last_user_message:
            response = "I can help you with appointments, finding doctors, or general health questions. What would you like to know?"
            actions = []
            intent = "help_request"
            confidence = 0.85
        elif "headache" in last_user_message or "pain" in last_user_message:
            response = "I understand you're experiencing discomfort. Can you describe your symptoms in more detail? When did they start?"
            actions = [
                {
                    "type": "symptom_assessment",
                    "data": {"symptoms": ["headache", "pain"], "follow_up_questions": ["duration", "severity", "location"]}
                }
            ]
            intent = "symptom_inquiry"
            confidence = 0.90
        elif "fever" in last_user_message or "temperature" in last_user_message:
            response = "Fever can be concerning. Have you measured your temperature? Any other symptoms accompanying the fever?"
            actions = [
                {
                    "type": "temperature_check",
                    "data": {"recommended_actions": ["measure_temperature", "monitor_symptoms", "stay_hydrated"]}
                }
            ]
            intent = "fever_assessment"
            confidence = 0.87
        else:
            response = f"Thank you for your message. As a healthcare assistant, I can help you with medical questions, appointment bookings, and finding doctors. How can I assist you today?"
            actions = []
            intent = "general_query"
            confidence = 0.70

        logger.info("Mock AI processing completed",
                   conversation_id=conversation_id,
                   message_count=len(messages),
                   intent=intent,
                   last_message_length=len(last_user_message))

        return {
            "success": True,
            "response": response,
            "actions": actions,
            "intent": intent,
            "confidence": confidence,
            "processing_time_ms": int(self.processing_delay * 1000),
            "ai_provider": "MockAI",
            "ai_id": "mock-ai-service",
            "conversation_turns": len(messages)
        }

    async def process_job(
        self,
        job_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        core_ai_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Dict[str, Any]:
        """Mock job processing using message array."""
        result = await self.process_message(conversation_id, messages, context, core_ai_id)
        result.update({
            "job_id": job_id,
            "job_status": "completed"
        })
        return result

    async def health_check(self, core_ai_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
        """Mock health check always returns True."""
        return True

    async def list_available_ais(self) -> List[Dict[str, Any]]:
        """Mock list of available AIs."""
        return [
            {
                "id": "mock-ai-service",
                "name": "Mock AI Service",
                "api_endpoint": "http://localhost:8001/mock",
                "timeout_seconds": 30,
                "auth_required": False,
                "meta_data": {"model": "mock-gpt", "version": "1.0"}
            }
        ]

    def clear_cache(self):
        """Mock cache clear."""
        pass


# Create global instances
database_ai_service = DatabaseAIService()
mock_ai_service = MockAIService()


def get_ai_service() -> Union[DatabaseAIService, MockAIService]:
    """Get AI service instance based on environment."""
    if settings.ENVIRONMENT == "development":
        logger.debug("Using Mock AI Service for development")
        return mock_ai_service
    else:
        logger.debug("Using Database AI Service for production")
        return database_ai_service


# Legacy support - keep old class names working
AIService = DatabaseAIService