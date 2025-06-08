"""
OpenAI Service Implementation
Concrete implementation of IAIService using OpenAI API with centralized configuration
"""
import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
import structlog

from app.application.interfaces.ai_service_interface import (
    IAIService, AIRequest, AIResponse, AIError
)
from app.application.exceptions import ExternalServiceError
from app.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


class OpenAIService(IAIService):
    """OpenAI implementation of AI service using centralized configuration"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[int] = None,
        use_config: bool = True
    ):
        """
        Initialize OpenAI service

        Args:
            api_key: OpenAI API key (overrides config)
            base_url: OpenAI base URL (overrides config)
            organization: OpenAI organization (overrides config)
            timeout: Request timeout (overrides config)
            use_config: Whether to use centralized configuration
        """
        if use_config:
            settings = get_settings()
            ai_config = settings.ai_service

            self.api_key = api_key or ai_config.openai_api_key
            self.base_url = base_url or ai_config.openai_base_url
            self.organization = organization or ai_config.openai_organization
            self.timeout = timeout or ai_config.timeout_seconds
            self.max_retries = ai_config.max_retries
            self.retry_delay = ai_config.retry_delay
            self.enable_content_filtering = ai_config.enable_content_filtering
            self.content_filter_threshold = ai_config.content_filter_threshold
        else:
            # Fallback to environment variables for backward compatibility
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = base_url or "https://api.openai.com/v1"
            self.organization = organization or os.getenv("OPENAI_ORGANIZATION")
            self.timeout = timeout or 30
            self.max_retries = 3
            self.retry_delay = 1.0
            self.enable_content_filtering = True
            self.content_filter_threshold = 0.8

        if not self.api_key:
            raise ValueError("OpenAI API key is required but not configured")

        logger.info("OpenAI service initialized",
                   base_url=self.base_url,
                   has_organization=bool(self.organization),
                   timeout=self.timeout,
                   content_filtering=self.enable_content_filtering)

    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response for a message with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info("Generating AI response",
                           model=request.model,
                           temperature=request.temperature,
                           attempt=attempt + 1)

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                if self.organization:
                    headers["OpenAI-Organization"] = self.organization

                # Build messages for chat completion
                messages = [
                    {"role": "system", "content": self._build_system_prompt(request.context)},
                    {"role": "user", "content": request.message}
                ]

                payload = {
                    "model": request.model,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0
                }

                start_time = asyncio.get_event_loop().time()

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=request.timeout_seconds)) as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:

                        end_time = asyncio.get_event_loop().time()
                        processing_time_ms = int((end_time - start_time) * 1000)

                        if response.status != 200:
                            error_data = await response.json()
                            error_message = error_data.get("error", {}).get("message", "Unknown error")

                            logger.error("OpenAI API error",
                                       status=response.status,
                                       error=error_message,
                                       attempt=attempt + 1)

                            # Retry on certain errors
                            if attempt < self.max_retries and response.status in [429, 500, 502, 503, 504]:
                                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                                continue

                            raise ExternalServiceError(
                                service="OpenAI",
                                operation="generate_response",
                                message=error_message,
                                status_code=response.status
                            )

                        data = await response.json()

                # Extract response
                choice = data["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice["finish_reason"]

                usage = data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)

                # Content safety check if enabled
                if self.enable_content_filtering:
                    safety_result = await self.check_content_safety(content)
                    if not safety_result.get("safe", True):
                        logger.warning("Content filtered by safety check")
                        content = "I'm sorry, but I cannot provide that response."

                # Calculate confidence score based on finish reason and response quality
                confidence_score = self._calculate_confidence_score(content, finish_reason)

                return AIResponse(
                    content=content,
                    confidence_score=confidence_score,
                    model=request.model,
                    processing_time_ms=processing_time_ms,
                    tokens_used=tokens_used,
                    finish_reason=finish_reason,
                    metadata={
                        "usage": usage,
                        "system_fingerprint": data.get("system_fingerprint"),
                        "created": data.get("created"),
                        "content_filtered": self.enable_content_filtering,
                        "attempt": attempt + 1
                    }
                )

            except ExternalServiceError:
                raise
            except Exception as e:
                logger.error("Unexpected error in generate_response",
                           error=str(e),
                           attempt=attempt + 1)

                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue

                raise ExternalServiceError(
                    service="OpenAI",
                    operation="generate_response",
                    message=f"Unexpected error: {str(e)}"
                )

        # This should never be reached due to the loop structure
        raise ExternalServiceError(
            service="OpenAI",
            operation="generate_response",
            message="Max retries exceeded"
        )

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            messages = [
                {
                    "role": "system",
                    "content": "Analyze the sentiment of the given text. Respond with a JSON object containing 'sentiment' (positive/negative/neutral) and 'score' (float between -1 and 1)."
                },
                {"role": "user", "content": text}
            ]

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 100
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        logger.error("Sentiment analysis failed", status=response.status)
                        return {"sentiment": "neutral", "score": 0.0}

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON response (simplified)
                    try:
                        import json
                        result = json.loads(content)
                        return {
                            "sentiment": result.get("sentiment", "neutral"),
                            "score": float(result.get("score", 0.0))
                        }
                    except:
                        return {"sentiment": "neutral", "score": 0.0}

        except Exception as e:
            logger.error("Error in sentiment analysis", error=str(e))
            return {"sentiment": "neutral", "score": 0.0}

    async def extract_intent(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user intent from text"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Build context-aware prompt
            context_str = self._format_context_for_intent(context)

            messages = [
                {
                    "role": "system",
                    "content": f"Extract the user's intent from their message. Context: {context_str}. Respond with JSON containing 'intent' and 'confidence' (0-1)."
                },
                {"role": "user", "content": text}
            ]

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 150
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        return {"intent": "unknown", "confidence": 0.0}

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    try:
                        import json
                        result = json.loads(content)
                        return {
                            "intent": result.get("intent", "unknown"),
                            "confidence": float(result.get("confidence", 0.0))
                        }
                    except:
                        return {"intent": "unknown", "confidence": 0.0}

        except Exception as e:
            logger.error("Error in intent extraction", error=str(e))
            return {"intent": "unknown", "confidence": 0.0}

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            messages = [
                {
                    "role": "system",
                    "content": "Extract named entities from the text. Return JSON array with objects containing 'entity', 'type', and 'value'."
                },
                {"role": "user", "content": text}
            ]

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 200
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        return []

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    try:
                        import json
                        return json.loads(content) or []
                    except:
                        return []

        except Exception as e:
            logger.error("Error in entity extraction", error=str(e))
            return []

    async def summarize_conversation(self, messages: List[str], max_length: int = 200) -> str:
        """Summarize conversation history"""
        try:
            conversation_text = "\n".join(messages[-10:])  # Last 10 messages

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            prompt_messages = [
                {
                    "role": "system",
                    "content": f"Summarize this conversation in {max_length} characters or less."
                },
                {"role": "user", "content": conversation_text}
            ]

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": prompt_messages,
                "temperature": 0.3,
                "max_tokens": max_length // 3
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        return "Conversation summary unavailable"

                    data = await response.json()
                    summary = data["choices"][0]["message"]["content"]

                    return summary[:max_length] if len(summary) > max_length else summary

        except Exception as e:
            logger.error("Error in conversation summarization", error=str(e))
            return "Conversation summary unavailable"

    async def detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            # Simple heuristic for common languages
            if any(char in text for char in "àáâãäåæçèéêëìíîïñòóôõöøùúûüý"):
                return "fr"  # French indicators
            elif any(char in text for char in "äöüß"):
                return "de"  # German indicators
            elif any(char in text for char in "ñáéíóúü"):
                return "es"  # Spanish indicators
            else:
                return "en"  # Default to English

        except Exception as e:
            logger.error("Error in language detection", error=str(e))
            return "en"

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """Translate text to target language"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            source_lang = source_language or await self.detect_language(text)

            messages = [
                {
                    "role": "system",
                    "content": f"Translate the following text from {source_lang} to {target_language}. Return only the translation."
                },
                {"role": "user", "content": text}
            ]

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": len(text) * 2
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        return text  # Return original if translation fails

                    data = await response.json()
                    return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error("Error in translation", error=str(e))
            return text

    async def check_content_safety(self, text: str) -> Dict[str, Any]:
        """Check content for safety/moderation"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {"input": text}

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/moderations",
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status != 200:
                        return {"safe": True, "categories": {}}

                    data = await response.json()
                    result = data["results"][0]

                    return {
                        "safe": not result["flagged"],
                        "categories": result["categories"],
                        "category_scores": result["category_scores"]
                    }

        except Exception as e:
            logger.error("Error in content safety check", error=str(e))
            return {"safe": True, "categories": {}}

    async def get_available_models(self) -> List[str]:
        """Get list of available AI models"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers
                ) as response:

                    if response.status != 200:
                        return ["gpt-3.5-turbo", "gpt-4"]  # Fallback models

                    data = await response.json()
                    models = [model["id"] for model in data["data"] if "gpt" in model["id"]]
                    return sorted(models)

        except Exception as e:
            logger.error("Error getting available models", error=str(e))
            return ["gpt-3.5-turbo", "gpt-4"]

    async def health_check(self) -> bool:
        """Check if AI service is healthy"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

    # === PRIVATE HELPER METHODS ===

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt from context"""
        base_prompt = "You are a helpful AI assistant in a chat conversation."

        if context.get("bot_type"):
            base_prompt += f" You are a {context['bot_type']} bot."

        if context.get("user_preferences"):
            prefs = context["user_preferences"]
            if prefs.get("language"):
                base_prompt += f" Respond in {prefs['language']}."

        if context.get("conversation_summary"):
            base_prompt += f" Context: {context['conversation_summary']}"

        return base_prompt

    def _calculate_confidence_score(self, content: str, finish_reason: str) -> float:
        """Calculate confidence score based on response quality"""
        base_score = 0.8

        # Adjust based on finish reason
        if finish_reason == "stop":
            base_score += 0.1
        elif finish_reason == "length":
            base_score -= 0.1
        elif finish_reason == "content_filter":
            base_score -= 0.3

        # Adjust based on content length and quality
        if len(content.strip()) < 10:
            base_score -= 0.2
        elif len(content.strip()) > 100:
            base_score += 0.1

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_score))

    def _format_context_for_intent(self, context: Dict[str, Any]) -> str:
        """Format context for intent extraction"""
        context_parts = []

        if context.get("user_data"):
            context_parts.append(f"User: {context['user_data']}")

        if context.get("conversation_history"):
            context_parts.append(f"History: {context['conversation_history']}")

        return "; ".join(context_parts) if context_parts else "No context"