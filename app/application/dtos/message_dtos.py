"""
Message Data Transfer Objects
DTOs for Message-related operations between Application and other layers
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from app.application.exceptions import ValidationError


class MessageRoleDTO(Enum):
    """Message role DTO"""
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class MessageStatusDTO(Enum):
    """Message status DTO"""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class MessageTypeDTO(Enum):
    """Message type DTO"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    SYSTEM = "system"


@dataclass
class CreateMessageDTO:
    """DTO for creating a new message"""
    conversation_id: UUID
    content: str
    role: MessageRoleDTO
    message_type: MessageTypeDTO = MessageTypeDTO.TEXT
    metadata: Optional[Dict[str, Any]] = None
    external_user_id: Optional[str] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.content or len(self.content.strip()) == 0:
            raise ValidationError("content", self.content, "Message content cannot be empty")

        if len(self.content) > 4000:
            raise ValidationError("content", self.content, "Message content exceeds maximum length")

        if self.metadata is None:
            self.metadata = {}


@dataclass
class UpdateMessageDTO:
    """DTO for updating message"""
    message_id: UUID
    status: Optional[MessageStatusDTO] = None
    confidence_score: Optional[float] = None
    ai_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    error_reason: Optional[str] = None
    retry_count: Optional[int] = None

    def __post_init__(self):
        """Validate DTO data"""
        if self.confidence_score is not None:
            if not (0.0 <= self.confidence_score <= 1.0):
                raise ValidationError("confidence_score", self.confidence_score, "Must be between 0.0 and 1.0")

        if self.processing_time_ms is not None and self.processing_time_ms < 0:
            raise ValidationError("processing_time_ms", self.processing_time_ms, "Must be non-negative")

        if self.retry_count is not None and self.retry_count < 0:
            raise ValidationError("retry_count", self.retry_count, "Must be non-negative")


@dataclass
class MessageDTO:
    """Message data transfer object"""
    id: UUID
    conversation_id: UUID
    content: str
    role: MessageRoleDTO
    message_type: MessageTypeDTO
    status: MessageStatusDTO
    confidence_score: Optional[float]
    ai_model: Optional[str]
    processing_time_ms: Optional[int]
    error_reason: Optional[str]
    retry_count: int
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None

    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message"""
        return self.role == MessageRoleDTO.USER

    @property
    def is_bot_message(self) -> bool:
        """Check if this is a bot message"""
        return self.role == MessageRoleDTO.BOT

    @property
    def is_processing(self) -> bool:
        """Check if message is being processed"""
        return self.status == MessageStatusDTO.PROCESSING

    @property
    def has_high_confidence(self) -> bool:
        """Check if message has high confidence (> 0.7)"""
        return self.confidence_score is not None and self.confidence_score > 0.7

    @property
    def has_failed(self) -> bool:
        """Check if message processing failed"""
        return self.status == MessageStatusDTO.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if message can be retried"""
        return self.status == MessageStatusDTO.FAILED and self.retry_count < 3


@dataclass
class MessageListDTO:
    """DTO for message list responses"""
    messages: List[MessageDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclass
class ProcessMessageDTO:
    """DTO for message processing workflow"""
    message_id: UUID
    ai_provider: str
    ai_model: str
    context_data: Dict[str, Any]
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_seconds: int = 30

    def __post_init__(self):
        """Validate DTO data"""
        if not (0.0 <= self.temperature <= 2.0):
            raise ValidationError("temperature", self.temperature, "Must be between 0.0 and 2.0")

        if self.max_tokens <= 0:
            raise ValidationError("max_tokens", self.max_tokens, "Must be positive")

        if self.timeout_seconds <= 0:
            raise ValidationError("timeout_seconds", self.timeout_seconds, "Must be positive")


@dataclass
class RetryMessageDTO:
    """DTO for retrying failed messages"""
    message_id: UUID
    retry_reason: str
    max_retries: int = 3

    def __post_init__(self):
        """Validate DTO data"""
        if not self.retry_reason or len(self.retry_reason.strip()) == 0:
            raise ValidationError("retry_reason", self.retry_reason, "Retry reason cannot be empty")

        if self.max_retries <= 0:
            raise ValidationError("max_retries", self.max_retries, "Must be positive")


@dataclass
class MessageStatsDTO:
    """Message statistics DTO"""
    total_messages: int
    user_messages: int
    bot_messages: int
    system_messages: int
    pending_messages: int
    processing_messages: int
    sent_messages: int
    failed_messages: int
    average_processing_time_ms: float
    average_confidence_score: Optional[float]
    retry_rate: float
    success_rate: float


@dataclass
class MessageSearchDTO:
    """DTO for message search requests"""
    conversation_id: Optional[UUID] = None
    role: Optional[MessageRoleDTO] = None
    status: Optional[MessageStatusDTO] = None
    message_type: Optional[MessageTypeDTO] = None
    content_query: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
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

        valid_sort_fields = {"created_at", "updated_at", "confidence_score", "processing_time_ms"}
        if self.sort_by not in valid_sort_fields:
            raise ValidationError("sort_by", self.sort_by, f"Must be one of {valid_sort_fields}")

        if self.sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order", self.sort_order, "Must be 'asc' or 'desc'")

        if self.min_confidence is not None:
            if not (0.0 <= self.min_confidence <= 1.0):
                raise ValidationError("min_confidence", self.min_confidence, "Must be between 0.0 and 1.0")

        if self.max_confidence is not None:
            if not (0.0 <= self.max_confidence <= 1.0):
                raise ValidationError("max_confidence", self.max_confidence, "Must be between 0.0 and 1.0")

        if (self.min_confidence is not None and self.max_confidence is not None and
            self.min_confidence > self.max_confidence):
            raise ValidationError("min_confidence", self.min_confidence, "Must be <= max_confidence")

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError("date_from", self.date_from, "Must be before date_to")


@dataclass
class BulkMessageOperationDTO:
    """DTO for bulk message operations"""
    message_ids: List[UUID]
    operation: str
    parameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate DTO data"""
        if not self.message_ids:
            raise ValidationError("message_ids", self.message_ids, "Message IDs list cannot be empty")

        if len(self.message_ids) > 100:
            raise ValidationError("message_ids", len(self.message_ids), "Cannot process more than 100 messages at once")

        valid_operations = {"retry", "mark_sent", "mark_failed", "delete"}
        if self.operation not in valid_operations:
            raise ValidationError("operation", self.operation, f"Must be one of {valid_operations}")

        if self.parameters is None:
            self.parameters = {}


@dataclass
class MessageAnalyticsDTO:
    """Message analytics DTO"""
    period_start: datetime
    period_end: datetime
    total_messages: int
    messages_by_role: Dict[str, int]
    messages_by_type: Dict[str, int]
    messages_by_status: Dict[str, int]
    average_processing_time: float
    confidence_distribution: Dict[str, int]  # ranges like "0.0-0.2", "0.2-0.4", etc.
    failure_reasons: Dict[str, int]
    peak_hour: int
    peak_day: str
    response_time_percentiles: Dict[str, float]  # p50, p90, p95, p99


@dataclass
class MessageExportDTO:
    """DTO for message export requests"""
    conversation_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    format: str = "json"
    include_metadata: bool = True
    include_context: bool = False

    def __post_init__(self):
        """Validate DTO data"""
        valid_formats = {"json", "csv", "excel"}
        if self.format not in valid_formats:
            raise ValidationError("format", self.format, f"Must be one of {valid_formats}")

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError("date_from", self.date_from, "Must be before date_to")