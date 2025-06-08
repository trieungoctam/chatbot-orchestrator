"""
Message Domain Events
Events for message lifecycle and processing tracking
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class MessageEvent:
    """Base message event"""
    message_id: UUID
    conversation_id: str
    role: str  # user, bot, system
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class MessageCreatedEvent(MessageEvent):
    """Event fired when message is created"""
    content: str
    external_user_id: Optional[str]
    platform: str
    message_type: str

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        content: str,
        role: str,
        external_user_id: Optional[str] = None,
        platform: str = "unknown",
        message_type: str = "text"
    ) -> 'MessageCreatedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            content=content,
            role=role,
            external_user_id=external_user_id,
            platform=platform,
            message_type=message_type,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_created',
                'version': '1.0',
                'content_length': len(content),
                'requires_processing': role == 'user'
            }
        )


@dataclass(frozen=True)
class MessageProcessedEvent(MessageEvent):
    """Event fired when message is successfully processed"""
    ai_model: Optional[str]
    processing_time_ms: int
    confidence_score: Optional[float]
    response_content: Optional[str]

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        ai_model: Optional[str] = None,
        processing_time_ms: int = 0,
        confidence_score: Optional[float] = None,
        response_content: Optional[str] = None
    ) -> 'MessageProcessedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            ai_model=ai_model,
            processing_time_ms=processing_time_ms,
            confidence_score=confidence_score,
            response_content=response_content,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_processed',
                'version': '1.0',
                'performance': {
                    'processing_time_seconds': processing_time_ms / 1000,
                    'is_high_confidence': confidence_score and confidence_score > 0.7,
                    'response_length': len(response_content) if response_content else 0
                }
            }
        )


@dataclass(frozen=True)
class MessageFailedEvent(MessageEvent):
    """Event fired when message processing fails"""
    error_reason: str
    error_code: Optional[str]
    retry_count: int
    can_retry: bool
    ai_model: Optional[str]

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        error_reason: str,
        error_code: Optional[str] = None,
        retry_count: int = 0,
        can_retry: bool = True,
        ai_model: Optional[str] = None
    ) -> 'MessageFailedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            error_reason=error_reason,
            error_code=error_code,
            retry_count=retry_count,
            can_retry=can_retry,
            ai_model=ai_model,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_failed',
                'version': '1.0',
                'requires_attention': retry_count >= 2,
                'auto_retry': can_retry and retry_count < 3
            }
        )


@dataclass(frozen=True)
class MessageRetriedEvent(MessageEvent):
    """Event fired when message processing is retried"""
    retry_reason: str
    retry_count: int
    previous_error: str
    max_retries: int

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        retry_reason: str,
        retry_count: int,
        previous_error: str,
        max_retries: int = 3
    ) -> 'MessageRetriedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            retry_reason=retry_reason,
            retry_count=retry_count,
            previous_error=previous_error,
            max_retries=max_retries,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_retried',
                'version': '1.0',
                'is_final_retry': retry_count >= max_retries,
                'retry_chain': retry_count
            }
        )


@dataclass(frozen=True)
class MessageSentEvent(MessageEvent):
    """Event fired when message is sent to external platform"""
    external_message_id: Optional[str]
    platform: str
    external_user_id: str
    delivery_status: str
    send_time_ms: int

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        external_message_id: Optional[str],
        platform: str,
        external_user_id: str,
        delivery_status: str = "sent",
        send_time_ms: int = 0
    ) -> 'MessageSentEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            external_message_id=external_message_id,
            platform=platform,
            external_user_id=external_user_id,
            delivery_status=delivery_status,
            send_time_ms=send_time_ms,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_sent',
                'version': '1.0',
                'delivery': {
                    'platform_confirmed': bool(external_message_id),
                    'send_time_seconds': send_time_ms / 1000
                }
            }
        )


@dataclass(frozen=True)
class MessageAnalyzedEvent(MessageEvent):
    """Event fired when message analysis is completed"""
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    intent: Optional[str]
    intent_confidence: Optional[float]
    entities: Dict[str, Any]
    language: Optional[str]

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        sentiment: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        intent: Optional[str] = None,
        intent_confidence: Optional[float] = None,
        entities: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None
    ) -> 'MessageAnalyzedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities or {},
            language=language,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_analyzed',
                'version': '1.0',
                'analysis': {
                    'has_sentiment': sentiment is not None,
                    'has_intent': intent is not None,
                    'entity_count': len(entities or {}),
                    'high_intent_confidence': intent_confidence and intent_confidence > 0.8
                }
            }
        )


@dataclass(frozen=True)
class MessageTimeoutEvent(MessageEvent):
    """Event fired when message processing times out"""
    timeout_seconds: int
    processing_stage: str
    ai_model: Optional[str]

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        timeout_seconds: int,
        processing_stage: str,
        ai_model: Optional[str] = None
    ) -> 'MessageTimeoutEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            timeout_seconds=timeout_seconds,
            processing_stage=processing_stage,
            ai_model=ai_model,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_timeout',
                'version': '1.0',
                'requires_intervention': True,
                'auto_action': 'mark_failed'
            }
        )


@dataclass(frozen=True)
class MessageQueuedEvent(MessageEvent):
    """Event fired when message is queued for processing"""
    queue_name: str
    priority: str
    estimated_processing_time_ms: int
    queue_position: int

    @classmethod
    def create(
        cls,
        message_id: UUID,
        conversation_id: str,
        role: str,
        queue_name: str,
        priority: str = "normal",
        estimated_processing_time_ms: int = 1000,
        queue_position: int = 0
    ) -> 'MessageQueuedEvent':
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            queue_name=queue_name,
            priority=priority,
            estimated_processing_time_ms=estimated_processing_time_ms,
            queue_position=queue_position,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'message_queued',
                'version': '1.0',
                'queue_info': {
                    'estimated_wait_seconds': estimated_processing_time_ms / 1000,
                    'is_priority': priority in ['high', 'urgent']
                }
            }
        )