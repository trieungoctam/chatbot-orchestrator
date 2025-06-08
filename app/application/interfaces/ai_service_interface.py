"""
AI Service Interface
Contract for AI/LLM service integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class AIRequest:
    """AI service request"""
    message: str
    context: Dict[str, Any]
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout_seconds: int = 30


@dataclass
class AIResponse:
    """AI service response"""
    content: str
    confidence_score: float
    model: str
    processing_time_ms: int
    tokens_used: int
    finish_reason: str
    metadata: Dict[str, Any]


@dataclass
class AIError:
    """AI service error"""
    error_code: str
    message: str
    retry_after_seconds: Optional[int] = None
    details: Dict[str, Any] = None


class IAIService(ABC):
    """Interface for AI service integrations"""

    @abstractmethod
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """
        Generate AI response for a message

        Args:
            request: AI request containing message and context

        Returns:
            AIResponse: Generated response with metadata

        Raises:
            ExternalServiceError: If AI service fails
        """
        pass

    @abstractmethod
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            Dict containing sentiment and score
        """
        pass

    @abstractmethod
    async def extract_intent(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user intent from text

        Args:
            text: User message
            context: Conversation context

        Returns:
            Dict containing intent and confidence
        """
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text

        Args:
            text: Text to analyze

        Returns:
            List of extracted entities
        """
        pass

    @abstractmethod
    async def summarize_conversation(
        self,
        messages: List[str],
        max_length: int = 200
    ) -> str:
        """
        Summarize conversation history

        Args:
            messages: List of conversation messages
            max_length: Maximum summary length

        Returns:
            Conversation summary
        """
        pass

    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """
        Detect language of text

        Args:
            text: Text to analyze

        Returns:
            Language code (e.g., 'en', 'vi')
        """
        pass

    @abstractmethod
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)

        Returns:
            Translated text
        """
        pass

    @abstractmethod
    async def check_content_safety(self, text: str) -> Dict[str, Any]:
        """
        Check content for safety/moderation

        Args:
            text: Content to check

        Returns:
            Dict containing safety assessment
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """
        Get list of available AI models

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if AI service is healthy

        Returns:
            True if service is healthy
        """
        pass