"""
Conversation Data Transfer Objects
DTOs for Conversation-related operations between Application and other layers
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from uuid import UUID
from enum import Enum

from app.application.exceptions import ValidationError


class ConversationStatusDTO(Enum):
    """Conversation status DTO"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    TRANSFERRED = "transferred"


class ConversationPriorityDTO(Enum):
    """Conversation priority DTO"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ConversationContextDTO:
    """Conversation context DTO"""
    external_user_id: Optional[str] = None
    platform: Optional[str] = None
    external_user_data: Dict[str, Any] = None
    user_preferences: Dict[str, Any] = None
    intent_history: List[str] = None
    entity_storage: Dict[str, Any] = None
    conversation_summary: Optional[str] = None
    current_sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    confidence_levels: Dict[str, float] = None
    system_notes: List[str] = None
    flags: Set[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize empty collections and validate data"""
        if self.external_user_data is None:
            self.external_user_data = {}
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.intent_history is None:
            self.intent_history = []
        if self.entity_storage is None:
            self.entity_storage = {}
        if self.confidence_levels is None:
            self.confidence_levels = {}
        if self.system_notes is None:
            self.system_notes = []
        if self.flags is None:
            self.flags = set()
        if self.metadata is None:
            self.metadata = {}

        # Validate sentiment score
        if self.sentiment_score is not None:
            if not (-1.0 <= self.sentiment_score <= 1.0):
                raise ValidationError("sentiment_score", self.sentiment_score, "Must be between -1.0 and 1.0")


@dataclass
class StartConversationDTO:
    """DTO for starting a new conversation"""
    bot_id: UUID
    initial_message: str
    external_user_id: str
    platform: str
    external_user_data: Optional[Dict[str, Any]] = None
    platform_data: Optional[Dict[str, Any]] = None
    priority: ConversationPriorityDTO = ConversationPriorityDTO.NORMAL

    def __post_init__(self):
        """Validate DTO data"""
        if not self.initial_message or len(self.initial_message.strip()) == 0:
            raise ValidationError("initial_message", self.initial_message, "Initial message cannot be empty")

        if len(self.initial_message) > 4000:
            raise ValidationError("initial_message", self.initial_message, "Initial message too long")

        if not self.external_user_id or len(self.external_user_id.strip()) == 0:
            raise ValidationError("external_user_id", self.external_user_id, "External user ID cannot be empty")

        if not self.platform or len(self.platform.strip()) == 0:
            raise ValidationError("platform", self.platform, "Platform cannot be empty")


@dataclass
class ProcessMessageDTO:
    """DTO for processing user messages"""
    conversation_id: str
    message_content: str
    external_user_id: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")

        if not self.message_content or len(self.message_content.strip()) == 0:
            raise ValidationError("message_content", self.message_content, "Message content cannot be empty")

        if len(self.message_content) > 4000:
            raise ValidationError("message_content", self.message_content, "Message content too long")

        if not self.external_user_id or len(self.external_user_id.strip()) == 0:
            raise ValidationError("external_user_id", self.external_user_id, "External user ID cannot be empty")


@dataclass
class AddBotResponseDTO:
    """DTO for adding bot responses"""
    conversation_id: str
    response_content: str
    confidence_score: Optional[float] = None
    ai_model: Optional[str] = None
    processing_time_ms: Optional[int] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")

        if not self.response_content or len(self.response_content.strip()) == 0:
            raise ValidationError("response_content", self.response_content, "Response content cannot be empty")

        if self.confidence_score is not None:
            if not (0.0 <= self.confidence_score <= 1.0):
                raise ValidationError("confidence_score", self.confidence_score, "Must be between 0.0 and 1.0")

        if self.processing_time_ms is not None and self.processing_time_ms < 0:
            raise ValidationError("processing_time_ms", self.processing_time_ms, "Must be non-negative")


@dataclass
class ConversationDTO:
    """Conversation data transfer object"""
    id: UUID
    conversation_id: str
    bot_id: UUID
    status: ConversationStatusDTO
    priority: ConversationPriorityDTO
    context: ConversationContextDTO
    participants: Set[str]
    message_count: int
    max_messages: int
    timeout_minutes: int
    max_idle_minutes: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """Check if conversation is active"""
        return self.status == ConversationStatusDTO.ACTIVE

    @property
    def duration_minutes(self) -> Optional[float]:
        """Get conversation duration in minutes"""
        if not self.ended_at:
            duration = datetime.utcnow() - self.started_at
        else:
            duration = self.ended_at - self.started_at
        return duration.total_seconds() / 60

    @property
    def is_approaching_limit(self) -> bool:
        """Check if conversation is approaching message limit"""
        return self.message_count >= (self.max_messages * 0.8)


@dataclass
class ConversationListDTO:
    """DTO for conversation list responses"""
    conversations: List[ConversationDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclass
class EscalateConversationDTO:
    """DTO for escalating conversations"""
    conversation_id: str
    reason: str
    escalated_by: Optional[str] = None
    new_priority: ConversationPriorityDTO = ConversationPriorityDTO.HIGH

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")

        if not self.reason or len(self.reason.strip()) == 0:
            raise ValidationError("reason", self.reason, "Escalation reason cannot be empty")


@dataclass
class TransferConversationDTO:
    """DTO for transferring conversations"""
    conversation_id: str
    target_bot_id: UUID
    reason: str
    transferred_by: Optional[str] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")

        if not self.reason or len(self.reason.strip()) == 0:
            raise ValidationError("reason", self.reason, "Transfer reason cannot be empty")


@dataclass
class EndConversationDTO:
    """DTO for ending conversations"""
    conversation_id: str
    reason: Optional[str] = None
    ended_by: Optional[str] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")


@dataclass
class ConversationStatsDTO:
    """Conversation statistics DTO"""
    conversation_id: str
    total_messages: int
    user_messages: int
    bot_messages: int
    duration_minutes: float
    average_response_time_ms: float
    sentiment_score: Optional[float]
    escalation_count: int
    transfer_count: int
    error_count: int
    confidence_scores: List[float]
    last_activity: datetime


@dataclass
class ConversationSearchDTO:
    """DTO for conversation search requests"""
    query: Optional[str] = None
    bot_id: Optional[UUID] = None
    status: Optional[ConversationStatusDTO] = None
    priority: Optional[ConversationPriorityDTO] = None
    platform: Optional[str] = None
    external_user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

    def __post_init__(self):
        """Validate DTO data"""
        if self.page < 1:
            raise ValidationError("page", self.page, "Page must be >= 1")

        if not (1 <= self.page_size <= 100):
            raise ValidationError("page_size", self.page_size, "Page size must be between 1 and 100")

        valid_sort_fields = {"created_at", "updated_at", "message_count", "priority"}
        if self.sort_by not in valid_sort_fields:
            raise ValidationError("sort_by", self.sort_by, f"Must be one of {valid_sort_fields}")

        if self.sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order", self.sort_order, "Must be 'asc' or 'desc'")

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError("date_from", self.date_from, "Must be before date_to")


@dataclass
class UpdateContextDTO:
    """DTO for updating conversation context"""
    conversation_id: str
    external_user_data: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    entities: Optional[Dict[str, Any]] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    system_note: Optional[str] = None
    flags_to_add: Optional[Set[str]] = None
    flags_to_remove: Optional[Set[str]] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.conversation_id or len(self.conversation_id.strip()) == 0:
            raise ValidationError("conversation_id", self.conversation_id, "Conversation ID cannot be empty")

        if self.intent_confidence is not None:
            if not (0.0 <= self.intent_confidence <= 1.0):
                raise ValidationError("intent_confidence", self.intent_confidence, "Must be between 0.0 and 1.0")

        if self.sentiment_score is not None:
            if not (-1.0 <= self.sentiment_score <= 1.0):
                raise ValidationError("sentiment_score", self.sentiment_score, "Must be between -1.0 and 1.0")