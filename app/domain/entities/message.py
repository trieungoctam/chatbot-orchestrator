# 📁 app/domain/entities/message.py
"""
Message Entity - Individual chat message business model
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum

from app.domain.exceptions import DomainError


class MessageRole(Enum):
    """Message sender role"""
    USER = "user"           # Human user
    BOT = "bot"            # AI bot response
    SYSTEM = "system"      # System message
    AGENT = "agent"        # Human agent


class MessageType(Enum):
    """Message content type"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    QUICK_REPLY = "quick_reply"
    TEMPLATE = "template"
    LOCATION = "location"


class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"      # Waiting to be processed
    PROCESSING = "processing" # Being processed by AI
    SENT = "sent"           # Successfully sent
    DELIVERED = "delivered"  # Delivered to platform
    READ = "read"           # Read by recipient
    FAILED = "failed"       # Failed to process/send
    RETRYING = "retrying"   # Retrying after failure


@dataclass(frozen=True)
class Message:
    """
    Message Entity

    Business Rules:
    1. Message content cannot be empty
    2. Content length limits based on type
    3. Metadata validation for special types
    4. Automatic language detection
    """

    # Identity
    id: UUID
    conversation_id: UUID

    # Content
    content: str
    role: MessageRole
    message_type: MessageType = MessageType.TEXT
    status: MessageStatus = MessageStatus.PENDING

    # Metadata
    metadata: Dict[str, Any] = None
    language: Optional[str] = None

    # Timestamps
    created_at: datetime = None
    processed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    # Processing info
    processing_time_ms: Optional[int] = None
    ai_model: Optional[str] = None
    confidence_score: Optional[float] = None

    def __post_init__(self):
        """Initialize and validate message"""
        # Set defaults
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.utcnow())

        # Validate business rules
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validate message business rules"""

        # Rule 1: Content validation
        if not self.content or not self.content.strip():
            raise DomainError("Message content cannot be empty")

        # Rule 2: Content length limits
        max_lengths = {
            MessageType.TEXT: 4000,
            MessageType.QUICK_REPLY: 2000,
            MessageType.TEMPLATE: 1000
        }

        max_length = max_lengths.get(self.message_type, 4000)
        if len(self.content) > max_length:
            raise DomainError(f"Message content exceeds maximum length: {max_length}")

        # Rule 3: Role-specific validation
        if self.role == MessageRole.SYSTEM and self.message_type != MessageType.TEXT:
            raise DomainError("System messages must be text type")

        # Rule 4: Confidence score validation
        if self.confidence_score is not None:
            if not (0.0 <= self.confidence_score <= 1.0):
                raise DomainError("Confidence score must be between 0.0 and 1.0")

    # === BUSINESS LOGIC METHODS ===

    def mark_as_processing(self, ai_model: str) -> 'Message':
        """Mark message as being processed"""
        if self.status != MessageStatus.PENDING:
            raise DomainError(f"Cannot process message in status: {self.status.value}")

        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            content=self.content,
            role=self.role,
            message_type=self.message_type,
            status=MessageStatus.PROCESSING,
            metadata=self.metadata,
            language=self.language,
            created_at=self.created_at,
            processed_at=datetime.utcnow(),
            sent_at=self.sent_at,
            processing_time_ms=self.processing_time_ms,
            ai_model=ai_model,
            confidence_score=self.confidence_score
        )

    def mark_as_sent(self, processing_time_ms: int, confidence_score: Optional[float] = None) -> 'Message':
        """Mark message as successfully sent"""
        if self.status not in [MessageStatus.PROCESSING, MessageStatus.RETRYING]:
            raise DomainError(f"Cannot mark as sent from status: {self.status.value}")

        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            content=self.content,
            role=self.role,
            message_type=self.message_type,
            status=MessageStatus.SENT,
            metadata=self.metadata,
            language=self.language,
            created_at=self.created_at,
            processed_at=self.processed_at,
            sent_at=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
            ai_model=self.ai_model,
            confidence_score=confidence_score
        )

    def mark_as_failed(self, error_reason: str) -> 'Message':
        """Mark message as failed"""
        metadata = self.metadata.copy()
        metadata['error_reason'] = error_reason
        metadata['failed_at'] = datetime.utcnow().isoformat()

        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            content=self.content,
            role=self.role,
            message_type=self.message_type,
            status=MessageStatus.FAILED,
            metadata=metadata,
            language=self.language,
            created_at=self.created_at,
            processed_at=self.processed_at,
            sent_at=self.sent_at,
            processing_time_ms=self.processing_time_ms,
            ai_model=self.ai_model,
            confidence_score=self.confidence_score
        )

    def retry(self) -> 'Message':
        """Retry failed message"""
        if self.status != MessageStatus.FAILED:
            raise DomainError("Can only retry failed messages")

        # Increment retry count
        metadata = self.metadata.copy()
        retry_count = metadata.get('retry_count', 0) + 1
        metadata['retry_count'] = retry_count
        metadata['retried_at'] = datetime.utcnow().isoformat()

        # Business rule: Max 3 retries
        if retry_count > 3:
            raise DomainError("Maximum retry attempts exceeded")

        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            content=self.content,
            role=self.role,
            message_type=self.message_type,
            status=MessageStatus.RETRYING,
            metadata=metadata,
            language=self.language,
            created_at=self.created_at,
            processed_at=self.processed_at,
            sent_at=self.sent_at,
            processing_time_ms=self.processing_time_ms,
            ai_model=self.ai_model,
            confidence_score=self.confidence_score
        )

    # === QUERY METHODS ===

    def is_user_message(self) -> bool:
        """Check if message is from user"""
        return self.role == MessageRole.USER

    def is_bot_message(self) -> bool:
        """Check if message is from bot"""
        return self.role == MessageRole.BOT

    def is_processing(self) -> bool:
        """Check if message is being processed"""
        return self.status in [MessageStatus.PROCESSING, MessageStatus.RETRYING]

    def is_completed(self) -> bool:
        """Check if message processing is completed"""
        return self.status in [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]

    def is_failed(self) -> bool:
        """Check if message failed"""
        return self.status == MessageStatus.FAILED

    def get_retry_count(self) -> int:
        """Get number of retry attempts"""
        return self.metadata.get('retry_count', 0)

    def get_processing_duration(self) -> Optional[int]:
        """Get processing duration in milliseconds"""
        if self.processing_time_ms:
            return self.processing_time_ms

        if self.processed_at and self.sent_at:
            duration = (self.sent_at - self.processed_at).total_seconds() * 1000
            return int(duration)

        return None

    def has_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if message has high confidence score"""
        return self.confidence_score is not None and self.confidence_score >= threshold

    def extract_intent(self) -> Optional[str]:
        """Extract intent from metadata"""
        return self.metadata.get('intent')

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract entities from metadata"""
        return self.metadata.get('entities', [])