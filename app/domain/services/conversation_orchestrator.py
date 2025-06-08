"""
Conversation Orchestrator Domain Service
Manages complex conversation business logic and coordination
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from app.domain.entities.conversation import Conversation, ConversationStatus, ConversationPriority
from app.domain.entities.message import Message, MessageRole, MessageStatus
from app.domain.entities.bot import Bot, BotStatus
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.exceptions import (
    DomainError,
    BusinessRuleViolationError,
    InvalidOperationError,
    ResourceLimitExceededError
)


class ConversationOrchestrator:
    """
    Domain Service for complex conversation orchestration

    Responsibilities:
    1. Conversation lifecycle management
    2. Message routing and validation
    3. Context management
    4. Escalation logic
    5. Load balancing between bots
    """

    def __init__(self):
        pass

    def start_conversation(
        self,
        bot: Bot,
        initial_message: str,
        external_user_id: str,
        platform: str,
        external_user_data: Optional[Dict[str, Any]] = None,
        platform_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Conversation, Message]:
        """
        Start new conversation with business rules validation

        Business Rules:
        1. Bot must be operational and can handle new conversations
        2. External user must have valid ID
        3. Platform must be supported
        4. Initial message must be valid
        """

        # Rule 1: Validate bot can handle conversation
        if not bot.can_handle_new_conversation():
            raise BusinessRuleViolationError(
                "BOT_CANNOT_HANDLE_CONVERSATION",
                f"Bot {bot.id} cannot handle new conversation",
                str(bot.id)
            )

        # Rule 2: Validate external user ID
        if not external_user_id or not external_user_id.strip():
            raise BusinessRuleViolationError(
                "INVALID_EXTERNAL_USER_ID",
                "External user ID cannot be empty",
                external_user_id
            )

        # Rule 3: Validate platform
        if not platform or not platform.strip():
            raise BusinessRuleViolationError(
                "INVALID_PLATFORM",
                "Platform cannot be empty",
                platform
            )

        # Rule 4: Check language compatibility if specified
        user_language = None
        if external_user_data:
            user_language = external_user_data.get('language_code') or external_user_data.get('language')

        if user_language and not bot.can_handle_language(user_language):
            raise BusinessRuleViolationError(
                "LANGUAGE_INCOMPATIBLE",
                f"Bot {bot.id} cannot handle language {user_language}",
                str(bot.id)
            )

        # Rule 5: Validate initial message
        if not initial_message or len(initial_message.strip()) == 0:
            raise BusinessRuleViolationError(
                "EMPTY_INITIAL_MESSAGE",
                "Initial message cannot be empty",
                external_user_id
            )

        # Create conversation context with external user data
        context = ConversationContext.create_with_external_user(
            external_user_id=external_user_id,
            platform=platform,
            external_user_data=external_user_data or {}
        )

        # Create conversation
        conversation = Conversation(
            id=UUID(int=0),  # Will be set by repository
            conversation_id=self._generate_conversation_id(external_user_id, platform, bot),
            bot_id=bot.id,
            status=ConversationStatus.ACTIVE,
            priority=self._determine_initial_priority(external_user_data, platform_data),
            context=context,
            max_messages=bot.config.max_conversation_length,
            timeout_minutes=30,  # Default timeout
            max_idle_minutes=15  # Default idle timeout
        )

        # Add initial message
        initial_msg = conversation.add_message(
            content=initial_message.strip(),
            role=MessageRole.USER,
            metadata={
                **(platform_data or {}),
                'external_user_id': external_user_id,
                'platform': platform
            }
        )

        return conversation, initial_msg

    def process_user_message(
        self,
        conversation: Conversation,
        message_content: str,
        external_user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Conversation, Message]:
        """
        Process incoming user message with validation

        Business Rules:
        1. Conversation must be active
        2. External user must match conversation context
        3. Message content validation
        4. Rate limiting check
        5. Context updates
        """

        # Rule 1: Validate conversation status
        if not conversation.can_accept_messages():
            raise InvalidOperationError(
                "ADD_MESSAGE",
                conversation.status.value,
                "Conversation cannot accept new messages"
            )

        # Rule 2: Check for timeout
        if conversation.is_timed_out():
            # Auto-handle timeout
            conversation.handle_timeout()
            raise InvalidOperationError(
                "ADD_MESSAGE",
                "TIMED_OUT",
                "Conversation has timed out"
            )

        # Rule 3: Validate external user matches conversation
        if (conversation.context.external_user_id and
            conversation.context.external_user_id != external_user_id):
            raise BusinessRuleViolationError(
                "USER_MISMATCH",
                f"External user ID {external_user_id} does not match conversation",
                external_user_id
            )

        # Rule 4: Validate message content
        if not message_content or len(message_content.strip()) == 0:
            raise BusinessRuleViolationError(
                "EMPTY_MESSAGE",
                "Message content cannot be empty",
                external_user_id
            )

        if len(message_content) > 4000:
            raise BusinessRuleViolationError(
                "MESSAGE_TOO_LONG",
                "Message content exceeds maximum length",
                external_user_id
            )

        # Rule 5: Check conversation limits
        if len(conversation.messages) >= conversation.max_messages:
            raise ResourceLimitExceededError(
                "CONVERSATION_MESSAGES",
                conversation.max_messages,
                len(conversation.messages)
            )

        # Add external user to participants if not already
        if external_user_id not in conversation.participants:
            conversation.participants.add(external_user_id)

        # Add message to conversation
        message = conversation.add_message(
            content=message_content.strip(),
            role=MessageRole.USER,
            metadata={
                **(metadata or {}),
                'external_user_id': external_user_id,
                'platform': conversation.context.platform
            }
        )

        return conversation, message

    def add_bot_response(
        self,
        conversation: Conversation,
        response_content: str,
        confidence_score: Optional[float] = None,
        ai_model: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> Tuple[Conversation, Message]:
        """
        Add bot response to conversation

        Business Rules:
        1. Response content validation
        2. Confidence score evaluation
        3. Auto-escalation logic
        4. Context updates
        """

        # Rule 1: Validate response content
        if not response_content or len(response_content.strip()) == 0:
            raise BusinessRuleViolationError(
                "EMPTY_BOT_RESPONSE",
                "Bot response cannot be empty"
            )

        # Create bot message metadata
        metadata = {
            'ai_model': ai_model,
            'confidence_score': confidence_score,
            'processing_time_ms': processing_time_ms,
            'generated_at': datetime.utcnow().isoformat(),
            'platform': conversation.context.platform
        }

        # Add message to conversation
        message = conversation.add_message(
            content=response_content.strip(),
            role=MessageRole.BOT,
            metadata=metadata
        )

        # Update message with AI processing info
        if confidence_score is not None:
            message = message._replace(confidence_score=confidence_score)
        if ai_model:
            message = message._replace(ai_model=ai_model)
        if processing_time_ms:
            message = message._replace(processing_time_ms=processing_time_ms)

        # Check for auto-escalation
        updated_conversation = self._check_auto_escalation(conversation, confidence_score)

        return updated_conversation, message

    def escalate_conversation(
        self,
        conversation: Conversation,
        reason: str,
        escalated_by: Optional[str] = None
    ) -> Conversation:
        """
        Escalate conversation to human agent

        Business Rules:
        1. Conversation must be active
        2. Valid escalation reason
        3. Update priority and context
        """

        if conversation.status != ConversationStatus.ACTIVE:
            raise InvalidOperationError(
                "ESCALATE_CONVERSATION",
                conversation.status.value,
                "Can only escalate active conversations"
            )

        if not reason or len(reason.strip()) == 0:
            raise BusinessRuleViolationError(
                "EMPTY_ESCALATION_REASON",
                "Escalation reason is required"
            )

        # Escalate priority if not already high
        if conversation.priority in [ConversationPriority.LOW, ConversationPriority.NORMAL]:
            conversation.escalate_priority(ConversationPriority.HIGH, reason)

        # Add escalation context
        escalation_note = f"Escalated: {reason}"
        if escalated_by:
            escalation_note += f" (by {escalated_by})"

        conversation.context = conversation.context.add_system_note(escalation_note)
        conversation.context = conversation.context.add_flag("escalated")

        return conversation

    def end_conversation(
        self,
        conversation: Conversation,
        reason: Optional[str] = None,
        ended_by: Optional[str] = None
    ) -> Conversation:
        """
        End conversation with proper cleanup

        Business Rules:
        1. Update conversation status
        2. Add system notes
        3. Calculate conversation metrics
        """

        # End conversation
        conversation.end(reason)

        # Add system note
        end_note = "Conversation ended"
        if reason:
            end_note += f": {reason}"
        if ended_by:
            end_note += f" (by {ended_by})"

        conversation.context = conversation.context.add_system_note(end_note)

        # Add conversation metrics to context
        duration = conversation.get_conversation_duration()
        message_counts = conversation.get_message_count_by_role()

        conversation.context = conversation.context._update(
            metadata={
                **conversation.context.metadata,
                'conversation_metrics': {
                    'duration_seconds': duration.total_seconds(),
                    'total_messages': len(conversation.messages),
                    'user_messages': message_counts.get('user', 0),
                    'bot_messages': message_counts.get('bot', 0),
                    'ended_at': datetime.utcnow().isoformat()
                }
            }
        )

        return conversation

    def transfer_conversation(
        self,
        conversation: Conversation,
        target_bot: Bot,
        reason: str,
        transferred_by: Optional[str] = None
    ) -> Conversation:
        """
        Transfer conversation to different bot

        Business Rules:
        1. Target bot must be operational
        2. Language compatibility check
        3. Capacity check
        4. Context preservation
        """

        # Validate target bot
        if not target_bot.is_operational():
            raise BusinessRuleViolationError(
                "TARGET_BOT_NOT_OPERATIONAL",
                f"Target bot {target_bot.id} is not operational"
            )

        if not target_bot.can_handle_new_conversation():
            raise BusinessRuleViolationError(
                "TARGET_BOT_OVERLOADED",
                f"Target bot {target_bot.id} cannot handle new conversations"
            )

        # Check language compatibility
        user_language = conversation.context.get_user_language()
        if user_language and not target_bot.can_handle_language(user_language):
            raise BusinessRuleViolationError(
                "LANGUAGE_INCOMPATIBLE",
                f"Target bot {target_bot.id} cannot handle language {user_language}"
            )

        # Update conversation
        conversation = conversation._replace(bot_id=target_bot.id)

        # Add transfer note
        transfer_note = f"Transferred to bot {target_bot.name}: {reason}"
        if transferred_by:
            transfer_note += f" (by {transferred_by})"

        conversation.context = conversation.context.add_system_note(transfer_note)
        conversation.context = conversation.context.add_flag("transferred")

        return conversation

    def update_external_user_data(
        self,
        conversation: Conversation,
        external_user_data: Dict[str, Any]
    ) -> Conversation:
        """
        Update external user data in conversation context

        Business Rules:
        1. External user data must be valid
        2. Context must be updated atomically
        """

        if not external_user_data:
            raise BusinessRuleViolationError(
                "EMPTY_USER_DATA",
                "External user data cannot be empty"
            )

        # Update context with new user data
        conversation.context = conversation.context.update_external_user_data(external_user_data)

        return conversation

    # === PRIVATE HELPER METHODS ===

    def _generate_conversation_id(self, external_user_id: str, platform: str, bot: Bot) -> str:
        """Generate unique conversation ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{platform}_{external_user_id}_{bot.id.hex[:8]}_{timestamp}"

    def _determine_initial_priority(
        self,
        external_user_data: Optional[Dict[str, Any]],
        platform_data: Optional[Dict[str, Any]]
    ) -> ConversationPriority:
        """Determine initial conversation priority"""

        # Check external user data for priority indicators
        if external_user_data:
            # Check if user has VIP status in external data
            if external_user_data.get('is_premium') or external_user_data.get('is_vip'):
                return ConversationPriority.HIGH

            # Check user type/role
            user_type = external_user_data.get('user_type', '').lower()
            if user_type in ['admin', 'premium', 'vip', 'moderator']:
                return ConversationPriority.HIGH

        # Check platform data for urgency indicators
        if platform_data:
            if platform_data.get("urgent") or platform_data.get("priority") == "high":
                return ConversationPriority.HIGH

        return ConversationPriority.NORMAL

    def _check_auto_escalation(
        self,
        conversation: Conversation,
        confidence_score: Optional[float]
    ) -> Conversation:
        """Check if conversation should be auto-escalated"""

        # Check confidence score threshold
        if confidence_score is not None and confidence_score < 0.3:
            conversation.context = conversation.context.add_flag("low_confidence")

            # Auto-escalate if multiple low confidence responses
            low_confidence_count = conversation.context.metadata.get('low_confidence_count', 0) + 1
            conversation.context = conversation.context._update(
                metadata={
                    **conversation.context.metadata,
                    'low_confidence_count': low_confidence_count
                }
            )

            if low_confidence_count >= 3:
                conversation = self.escalate_conversation(
                    conversation,
                    f"Auto-escalated: {low_confidence_count} low confidence responses",
                    "system"
                )

        # Check for negative sentiment
        if conversation.context.is_sentiment_negative():
            conversation.context = conversation.context.add_flag("negative_sentiment")

        # Check conversation length
        if len(conversation.messages) > 20:
            conversation.context = conversation.context.add_flag("long_conversation")

        return conversation

    def get_conversation_health_score(self, conversation: Conversation) -> float:
        """
        Calculate conversation health score (0.0 to 1.0)

        Factors:
        - Message flow consistency
        - Response confidence
        - User sentiment
        - Conversation progress
        """
        score = 1.0

        # Check message flow
        if len(conversation.messages) == 0:
            return 0.0

        # Penalty for low confidence
        if conversation.context.has_flag("low_confidence"):
            score -= 0.3

        # Penalty for negative sentiment
        if conversation.context.is_sentiment_negative():
            score -= 0.2

        # Penalty for long conversations without resolution
        if len(conversation.messages) > 30:
            score -= 0.2

        # Penalty for flags indicating issues
        error_flags = conversation.context.flags.intersection({
            'error', 'escalation_needed', 'confusion'
        })
        score -= len(error_flags) * 0.1

        # Bonus for high confidence context
        if conversation.context.is_high_confidence_context():
            score += 0.1

        return max(0.0, min(1.0, score))