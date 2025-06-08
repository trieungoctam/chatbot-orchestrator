# 📁 app/domain/entities/conversation.py
"""
Conversation Entity - Chat session business model
Aggregate Root - manages conversation lifecycle và messages
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum

from app.domain.entities.message import Message, MessageRole
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.exceptions import DomainError


class ConversationStatus(Enum):
    """Conversation lifecycle status"""
    ACTIVE = "active"           # Đang hoạt động
    PAUSED = "paused"          # Tạm dừng
    ENDED = "ended"            # Kết thúc bình thường
    TRANSFERRED = "transferred" # Chuyển cho human agent
    TIMEOUT = "timeout"        # Hết thời gian
    ERROR = "error"            # Lỗi hệ thống


class ConversationPriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Conversation:
    """
    Conversation Aggregate Root

    Business Rules:
    1. Conversation có unique external ID
    2. Chỉ accept message khi status = ACTIVE
    3. Auto timeout sau idle time
    4. Giới hạn message count
    5. Track conversation context
    """

    # Identity
    id: UUID
    conversation_id: str  # External ID for clients
    bot_id: UUID

    # Status & Priority
    status: ConversationStatus
    priority: ConversationPriority = ConversationPriority.NORMAL

    # Content
    messages: List[Message] = field(default_factory=list)
    context: ConversationContext = field(default_factory=ConversationContext.create_empty)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)

    # Business rules configuration
    max_messages: int = 1000
    timeout_minutes: int = 30
    max_idle_minutes: int = 15

    # Participants
    participants: Set[str] = field(default_factory=set)  # User IDs involved

    def __post_init__(self):
        """Validate business rules"""
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validate conversation business rules"""
        if not self.conversation_id:
            raise DomainError("Conversation must have external ID")

        if not self.bot_id:
            raise DomainError("Conversation must be assigned to a bot")

        if self.max_messages < 1:
            raise DomainError("Max messages must be at least 1")

        if len(self.messages) > self.max_messages:
            raise DomainError(f"Conversation exceeds maximum message limit: {self.max_messages}")

    # === CORE BUSINESS LOGIC ===

    def add_message(self, content: str, role: MessageRole, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Business Logic: Add message to conversation

        Rules:
        - Only accept if status is ACTIVE
        - Check message limits
        - Update last activity
        - Auto-detect language và context
        """
        if not self.can_accept_messages():
            raise DomainError(f"Conversation in status {self.status.value} cannot accept messages")

        if len(self.messages) >= self.max_messages:
            raise DomainError(f"Conversation has reached maximum message limit: {self.max_messages}")

        # Create message
        message = Message(
            id=uuid4(),
            conversation_id=self.id,
            content=content.strip(),
            role=role,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )

        # Add to conversation
        self.messages.append(message)
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Update context
        self.context = self.context.add_message_context(message)

        return message

    def can_accept_messages(self) -> bool:
        """Business Logic: Check if conversation can accept new messages"""
        if self.status != ConversationStatus.ACTIVE:
            return False

        # Check timeout
        if self.is_timed_out():
            return False

        # Check if reached message limit
        if len(self.messages) >= self.max_messages:
            return False

        return True

    def is_timed_out(self) -> bool:
        """Business Logic: Check if conversation has timed out"""
        if self.status in [ConversationStatus.ENDED, ConversationStatus.TIMEOUT]:
            return True

        # Check total timeout
        total_time = datetime.utcnow() - self.created_at
        if total_time.total_seconds() > (self.timeout_minutes * 60):
            return True

        # Check idle timeout
        idle_time = datetime.utcnow() - self.last_activity_at
        if idle_time.total_seconds() > (self.max_idle_minutes * 60):
            return True

        return False

    def pause(self, reason: Optional[str] = None) -> None:
        """Business Logic: Pause conversation"""
        if self.status == ConversationStatus.ENDED:
            raise DomainError("Cannot pause ended conversation")

        if self.status == ConversationStatus.TIMEOUT:
            raise DomainError("Cannot pause timed out conversation")

        self.status = ConversationStatus.PAUSED
        self.updated_at = datetime.utcnow()

        if reason:
            self.context = self.context.add_system_note(f"Paused: {reason}")

    def resume(self) -> None:
        """Business Logic: Resume paused conversation"""
        if self.status != ConversationStatus.PAUSED:
            raise DomainError("Can only resume paused conversations")

        if self.is_timed_out():
            raise DomainError("Cannot resume timed out conversation")

        self.status = ConversationStatus.ACTIVE
        self.updated_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()

        self.context = self.context.add_system_note("Conversation resumed")

    def end(self, reason: Optional[str] = None) -> None:
        """Business Logic: End conversation"""
        if self.status == ConversationStatus.ENDED:
            return  # Already ended

        self.status = ConversationStatus.ENDED
        self.updated_at = datetime.utcnow()

        if reason:
            self.context = self.context.add_system_note(f"Ended: {reason}")

    def transfer_to_human(self, agent_id: str, reason: Optional[str] = None) -> None:
        """Business Logic: Transfer to human agent"""
        if self.status == ConversationStatus.ENDED:
            raise DomainError("Cannot transfer ended conversation")

        self.status = ConversationStatus.TRANSFERRED
        self.updated_at = datetime.utcnow()
        self.participants.add(agent_id)

        transfer_note = f"Transferred to human agent {agent_id}"
        if reason:
            transfer_note += f". Reason: {reason}"

        self.context = self.context.add_system_note(transfer_note)

    def handle_timeout(self) -> None:
        """Business Logic: Handle conversation timeout"""
        if self.status in [ConversationStatus.ENDED, ConversationStatus.TIMEOUT]:
            return

        self.status = ConversationStatus.TIMEOUT
        self.updated_at = datetime.utcnow()
        self.context = self.context.add_system_note("Conversation timed out due to inactivity")

    def escalate_priority(self, new_priority: ConversationPriority, reason: str) -> None:
        """Business Logic: Escalate conversation priority"""
        if new_priority.value <= self.priority.value:
            raise DomainError("Can only escalate to higher priority")

        old_priority = self.priority
        self.priority = new_priority
        self.updated_at = datetime.utcnow()

        self.context = self.context.add_system_note(
            f"Priority escalated from {old_priority.value} to {new_priority.value}. Reason: {reason}"
        )

    # === QUERY METHODS ===

    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent messages for context"""
        return sorted(self.messages, key=lambda m: m.created_at, reverse=True)[:limit]

    def get_user_messages(self) -> List[Message]:
        """Get only user messages"""
        return [msg for msg in self.messages if msg.role == MessageRole.USER]

    def get_bot_messages(self) -> List[Message]:
        """Get only bot messages"""
        return [msg for msg in self.messages if msg.role == MessageRole.BOT]

    def get_conversation_duration(self) -> timedelta:
        """Get total conversation duration"""
        return datetime.utcnow() - self.created_at

    def get_idle_time(self) -> timedelta:
        """Get current idle time"""
        return datetime.utcnow() - self.last_activity_at

    def get_message_count_by_role(self) -> Dict[str, int]:
        """Get message count by role"""
        counts = {}
        for message in self.messages:
            role = message.role.value
            counts[role] = counts.get(role, 0) + 1
        return counts

    def is_active(self) -> bool:
        """Check if conversation is active and can receive messages"""
        return self.status == ConversationStatus.ACTIVE and not self.is_timed_out()

    def needs_attention(self) -> bool:
        """Business Logic: Check if conversation needs human attention"""
        # High priority conversations
        if self.priority in [ConversationPriority.HIGH, ConversationPriority.URGENT]:
            return True

        # Long conversations might need attention
        if len(self.messages) > 50:
            return True

        # Check for error indicators in context
        if self.context.has_error_indicators():
            return True

        return False