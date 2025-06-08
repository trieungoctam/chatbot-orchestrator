"""
Conversation Domain Events
Events for conversation lifecycle and state changes
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class ConversationEvent:
    """Base conversation event"""
    conversation_id: str
    bot_id: UUID
    external_user_id: str
    platform: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ConversationStartedEvent(ConversationEvent):
    """Event fired when conversation is started"""
    initial_message: str
    user_data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        conversation_id: str,
        bot_id: UUID,
        external_user_id: str,
        platform: str,
        initial_message: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> 'ConversationStartedEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=bot_id,
            external_user_id=external_user_id,
            platform=platform,
            initial_message=initial_message,
            user_data=user_data or {},
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_started',
                'version': '1.0'
            }
        )


@dataclass(frozen=True)
class ConversationEndedEvent(ConversationEvent):
    """Event fired when conversation is ended"""
    reason: Optional[str]
    ended_by: Optional[str]
    duration_seconds: float
    message_count: int
    final_status: str

    @classmethod
    def create(
        cls,
        conversation_id: str,
        bot_id: UUID,
        external_user_id: str,
        platform: str,
        reason: Optional[str] = None,
        ended_by: Optional[str] = None,
        duration_seconds: float = 0.0,
        message_count: int = 0,
        final_status: str = "completed"
    ) -> 'ConversationEndedEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=bot_id,
            external_user_id=external_user_id,
            platform=platform,
            reason=reason,
            ended_by=ended_by,
            duration_seconds=duration_seconds,
            message_count=message_count,
            final_status=final_status,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_ended',
                'version': '1.0',
                'analytics': {
                    'duration_minutes': duration_seconds / 60,
                    'messages_per_minute': message_count / (duration_seconds / 60) if duration_seconds > 0 else 0
                }
            }
        )


@dataclass(frozen=True)
class ConversationEscalatedEvent(ConversationEvent):
    """Event fired when conversation is escalated"""
    escalation_reason: str
    escalated_by: Optional[str]
    previous_priority: str
    new_priority: str
    escalation_triggers: Dict[str, Any]

    @classmethod
    def create(
        cls,
        conversation_id: str,
        bot_id: UUID,
        external_user_id: str,
        platform: str,
        escalation_reason: str,
        escalated_by: Optional[str] = None,
        previous_priority: str = "normal",
        new_priority: str = "high",
        escalation_triggers: Optional[Dict[str, Any]] = None
    ) -> 'ConversationEscalatedEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=bot_id,
            external_user_id=external_user_id,
            platform=platform,
            escalation_reason=escalation_reason,
            escalated_by=escalated_by,
            previous_priority=previous_priority,
            new_priority=new_priority,
            escalation_triggers=escalation_triggers or {},
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_escalated',
                'version': '1.0',
                'requires_attention': True
            }
        )


@dataclass(frozen=True)
class ConversationTransferredEvent(ConversationEvent):
    """Event fired when conversation is transferred to different bot"""
    source_bot_id: UUID
    target_bot_id: UUID
    transfer_reason: str
    transferred_by: Optional[str]
    context_preserved: bool

    @classmethod
    def create(
        cls,
        conversation_id: str,
        external_user_id: str,
        platform: str,
        source_bot_id: UUID,
        target_bot_id: UUID,
        transfer_reason: str,
        transferred_by: Optional[str] = None,
        context_preserved: bool = True
    ) -> 'ConversationTransferredEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=target_bot_id,  # Current bot after transfer
            external_user_id=external_user_id,
            platform=platform,
            source_bot_id=source_bot_id,
            target_bot_id=target_bot_id,
            transfer_reason=transfer_reason,
            transferred_by=transferred_by,
            context_preserved=context_preserved,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_transferred',
                'version': '1.0',
                'transfer_chain': [str(source_bot_id), str(target_bot_id)]
            }
        )


@dataclass(frozen=True)
class ConversationTimeoutEvent(ConversationEvent):
    """Event fired when conversation times out"""
    timeout_type: str  # idle, max_duration, etc.
    last_activity: datetime
    timeout_threshold_minutes: int

    @classmethod
    def create(
        cls,
        conversation_id: str,
        bot_id: UUID,
        external_user_id: str,
        platform: str,
        timeout_type: str,
        last_activity: datetime,
        timeout_threshold_minutes: int
    ) -> 'ConversationTimeoutEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=bot_id,
            external_user_id=external_user_id,
            platform=platform,
            timeout_type=timeout_type,
            last_activity=last_activity,
            timeout_threshold_minutes=timeout_threshold_minutes,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_timeout',
                'version': '1.0',
                'auto_action': 'end_conversation'
            }
        )


@dataclass(frozen=True)
class ConversationHealthCheckEvent(ConversationEvent):
    """Event fired for conversation health monitoring"""
    health_score: float
    confidence_scores: list[float]
    sentiment_score: Optional[float]
    flags: list[str]
    requires_intervention: bool

    @classmethod
    def create(
        cls,
        conversation_id: str,
        bot_id: UUID,
        external_user_id: str,
        platform: str,
        health_score: float,
        confidence_scores: list[float],
        sentiment_score: Optional[float] = None,
        flags: Optional[list[str]] = None,
        requires_intervention: bool = False
    ) -> 'ConversationHealthCheckEvent':
        return cls(
            conversation_id=conversation_id,
            bot_id=bot_id,
            external_user_id=external_user_id,
            platform=platform,
            health_score=health_score,
            confidence_scores=confidence_scores,
            sentiment_score=sentiment_score,
            flags=flags or [],
            requires_intervention=requires_intervention,
            timestamp=datetime.utcnow(),
            metadata={
                'event_type': 'conversation_health_check',
                'version': '1.0',
                'monitoring': {
                    'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                    'low_confidence_count': len([s for s in confidence_scores if s < 0.5]),
                    'critical_flags': [f for f in flags or [] if f in ['error', 'escalation_needed']]
                }
            }
        )