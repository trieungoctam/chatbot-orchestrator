"""
Conversation Context Value Object
Manages conversation state, history, and contextual information
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from app.domain.exceptions import DomainError


class ContextType(Enum):
    """Types of context information"""
    EXTERNAL_USER = "external_user"      # External user info (from platform)
    CONVERSATION_HISTORY = "conversation_history"
    INTENT_RECOGNITION = "intent_recognition"
    ENTITY_EXTRACTION = "entity_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    SYSTEM_NOTES = "system_notes"


@dataclass(frozen=True)
class ConversationContext:
    """
    Conversation Context Value Object

    Manages all contextual information for a conversation including:
    - External user info (platform-specific user data)
    - Conversation history summary
    - Detected intents and entities
    - Sentiment analysis results
    - System notes and metadata
    """

    # External User Context (from platforms like Telegram, Facebook)
    external_user_id: Optional[str] = None
    platform: Optional[str] = None  # telegram, facebook, etc.
    external_user_data: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # Conversation Context
    intent_history: List[str] = field(default_factory=list)
    entity_storage: Dict[str, Any] = field(default_factory=dict)
    conversation_summary: Optional[str] = None

    # Sentiment & Analysis
    current_sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    confidence_levels: Dict[str, float] = field(default_factory=dict)

    # System Context
    system_notes: List[str] = field(default_factory=list)
    flags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate context data"""
        if self.sentiment_score is not None:
            if not (-1.0 <= self.sentiment_score <= 1.0):
                raise DomainError("Sentiment score must be between -1.0 and 1.0")

    @classmethod
    def create_empty(cls, external_user_id: Optional[str] = None, platform: Optional[str] = None) -> 'ConversationContext':
        """Create empty context for new conversation"""
        return cls(external_user_id=external_user_id, platform=platform)

    @classmethod
    def create_with_external_user(
        cls,
        external_user_id: str,
        platform: str,
        external_user_data: Dict[str, Any]
    ) -> 'ConversationContext':
        """Create context with external user information from platform"""
        return cls(
            external_user_id=external_user_id,
            platform=platform,
            external_user_data=external_user_data,
            user_preferences=external_user_data.get('preferences', {})
        )

    # === CONTEXT MANAGEMENT METHODS ===

    def add_intent(self, intent: str, confidence: float) -> 'ConversationContext':
        """Add detected intent to context"""
        if confidence < 0.0 or confidence > 1.0:
            raise DomainError("Intent confidence must be between 0.0 and 1.0")

        new_intent_history = self.intent_history + [intent]
        # Keep only last 10 intents
        if len(new_intent_history) > 10:
            new_intent_history = new_intent_history[-10:]

        new_confidence_levels = self.confidence_levels.copy()
        new_confidence_levels[f"intent_{intent}"] = confidence

        return self._update(
            intent_history=new_intent_history,
            confidence_levels=new_confidence_levels
        )

    def add_entity(self, entity_type: str, entity_value: Any, confidence: float = 1.0) -> 'ConversationContext':
        """Add extracted entity to context"""
        new_entity_storage = self.entity_storage.copy()
        new_entity_storage[entity_type] = {
            'value': entity_value,
            'confidence': confidence,
            'extracted_at': datetime.utcnow().isoformat()
        }

        return self._update(entity_storage=new_entity_storage)

    def update_sentiment(self, sentiment: str, score: float) -> 'ConversationContext':
        """Update conversation sentiment"""
        if not (-1.0 <= score <= 1.0):
            raise DomainError("Sentiment score must be between -1.0 and 1.0")

        return self._update(
            current_sentiment=sentiment,
            sentiment_score=score
        )

    def add_system_note(self, note: str) -> 'ConversationContext':
        """Add system note to context"""
        timestamp = datetime.utcnow().isoformat()
        formatted_note = f"[{timestamp}] {note}"

        new_system_notes = self.system_notes + [formatted_note]
        # Keep only last 20 system notes
        if len(new_system_notes) > 20:
            new_system_notes = new_system_notes[-20:]

        return self._update(system_notes=new_system_notes)

    def add_flag(self, flag: str) -> 'ConversationContext':
        """Add context flag"""
        new_flags = self.flags.copy()
        new_flags.add(flag)

        return self._update(flags=new_flags)

    def remove_flag(self, flag: str) -> 'ConversationContext':
        """Remove context flag"""
        new_flags = self.flags.copy()
        new_flags.discard(flag)

        return self._update(flags=new_flags)

    def update_conversation_summary(self, summary: str) -> 'ConversationContext':
        """Update conversation summary"""
        if len(summary) > 1000:
            raise DomainError("Conversation summary cannot exceed 1000 characters")

        return self._update(conversation_summary=summary)

    def add_message_context(self, message) -> 'ConversationContext':
        """Add context from a message"""
        # Extract context from message metadata
        message_metadata = getattr(message, 'metadata', {})

        context_updates = {}

        # Add intent if detected
        if 'intent' in message_metadata:
            intent = message_metadata['intent']
            confidence = message_metadata.get('intent_confidence', 0.8)
            return self.add_intent(intent, confidence)

        # Add entities if extracted
        if 'entities' in message_metadata:
            updated_context = self
            for entity in message_metadata['entities']:
                entity_type = entity.get('type')
                entity_value = entity.get('value')
                entity_confidence = entity.get('confidence', 1.0)

                if entity_type and entity_value:
                    updated_context = updated_context.add_entity(
                        entity_type, entity_value, entity_confidence
                    )
            return updated_context

        # Add sentiment if analyzed
        if 'sentiment' in message_metadata:
            sentiment = message_metadata['sentiment']
            sentiment_score = message_metadata.get('sentiment_score', 0.0)
            return self.update_sentiment(sentiment, sentiment_score)

        return self

    def update_external_user_data(self, user_data: Dict[str, Any]) -> 'ConversationContext':
        """Update external user data from platform"""
        new_external_user_data = self.external_user_data.copy()
        new_external_user_data.update(user_data)

        # Update preferences if provided
        new_preferences = self.user_preferences.copy()
        if 'preferences' in user_data:
            new_preferences.update(user_data['preferences'])

        return self._update(
            external_user_data=new_external_user_data,
            user_preferences=new_preferences
        )

    # === QUERY METHODS ===

    def get_current_intent(self) -> Optional[str]:
        """Get most recent intent"""
        return self.intent_history[-1] if self.intent_history else None

    def get_entity(self, entity_type: str) -> Optional[Any]:
        """Get entity value by type"""
        entity_data = self.entity_storage.get(entity_type)
        return entity_data['value'] if entity_data else None

    def get_entity_confidence(self, entity_type: str) -> Optional[float]:
        """Get entity confidence by type"""
        entity_data = self.entity_storage.get(entity_type)
        return entity_data['confidence'] if entity_data else None

    def has_flag(self, flag: str) -> bool:
        """Check if context has specific flag"""
        return flag in self.flags

    def has_error_indicators(self) -> bool:
        """Check if context contains error indicators"""
        error_flags = {'error', 'escalation_needed', 'confusion', 'negative_sentiment'}
        return bool(self.flags.intersection(error_flags))

    def get_intent_pattern(self) -> List[str]:
        """Get recent intent pattern"""
        return self.intent_history[-5:] if len(self.intent_history) >= 5 else self.intent_history

    def is_sentiment_negative(self) -> bool:
        """Check if current sentiment is negative"""
        return self.sentiment_score is not None and self.sentiment_score < -0.3

    def is_high_confidence_context(self) -> bool:
        """Check if context has high confidence across measurements"""
        if not self.confidence_levels:
            return False

        avg_confidence = sum(self.confidence_levels.values()) / len(self.confidence_levels)
        return avg_confidence >= 0.7

    def get_user_display_name(self) -> str:
        """Get user's display name from external data"""
        if not self.external_user_data:
            return f"User {self.external_user_id}" if self.external_user_id else "Anonymous"

        # Try to get name from external data
        first_name = self.external_user_data.get('first_name', '')
        last_name = self.external_user_data.get('last_name', '')
        username = self.external_user_data.get('username', '')

        if first_name and last_name:
            return f"{first_name} {last_name}".strip()
        elif first_name:
            return first_name
        elif username:
            return f"@{username}"
        else:
            return f"User {self.external_user_id}" if self.external_user_id else "Anonymous"

    def get_user_language(self) -> str:
        """Get user's language preference"""
        # Check user preferences first
        language = self.user_preferences.get('language')
        if language:
            return language

        # Check external user data
        language = self.external_user_data.get('language_code')
        if language:
            return language

        # Default language
        return 'vi'

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of context for AI processing"""
        return {
            'external_user_id': self.external_user_id,
            'platform': self.platform,
            'user_name': self.get_user_display_name(),
            'user_language': self.get_user_language(),
            'current_intent': self.get_current_intent(),
            'entities': {k: v['value'] for k, v in self.entity_storage.items()},
            'sentiment': {
                'current': self.current_sentiment,
                'score': self.sentiment_score
            },
            'flags': list(self.flags),
            'conversation_summary': self.conversation_summary,
            'has_errors': self.has_error_indicators()
        }

    def _update(self, **kwargs) -> 'ConversationContext':
        """Create updated context with new values"""
        current_values = {
            'external_user_id': self.external_user_id,
            'platform': self.platform,
            'external_user_data': self.external_user_data,
            'user_preferences': self.user_preferences,
            'intent_history': self.intent_history,
            'entity_storage': self.entity_storage,
            'conversation_summary': self.conversation_summary,
            'current_sentiment': self.current_sentiment,
            'sentiment_score': self.sentiment_score,
            'confidence_levels': self.confidence_levels,
            'system_notes': self.system_notes,
            'flags': self.flags,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }

        current_values.update(kwargs)
        return ConversationContext(**current_values)