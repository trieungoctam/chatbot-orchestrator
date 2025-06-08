"""
SQLAlchemy Database Models
Database schema for Chat Orchestrator entities
"""
from datetime import datetime
from typing import Dict, Any, List, Set
from uuid import UUID, uuid4
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float, JSON,
    ForeignKey, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# Enums
class BotTypeEnum(enum.Enum):
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"
    GENERAL = "general"


class BotStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class ConversationStatusEnum(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    TRANSFERRED = "transferred"


class ConversationPriorityEnum(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageRoleEnum(enum.Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class MessageStatusEnum(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class PlatformTypeEnum(enum.Enum):
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WEBCHAT = "webchat"


class AIProviderEnum(enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"


# Models
class PlatformModel(Base):
    """Platform model for external integrations"""
    __tablename__ = "platforms"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    platform_type = Column(Enum(PlatformTypeEnum), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Configuration
    config = Column(JSON, nullable=False, default=dict)
    api_credentials = Column(JSON, nullable=False, default=dict)
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=30)
    rate_limit_per_hour = Column(Integer, default=1000)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    bots = relationship("BotModel", back_populates="platform")

    # Indexes
    __table_args__ = (
        Index("idx_platforms_type", "platform_type"),
        Index("idx_platforms_active", "is_active"),
        UniqueConstraint("name", "platform_type", name="uq_platform_name_type"),
    )


class CoreAIModel(Base):
    """Core AI model for AI service configurations"""
    __tablename__ = "core_ai"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    provider = Column(Enum(AIProviderEnum), nullable=False)
    model_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Configuration
    config = Column(JSON, nullable=False, default=dict)
    api_credentials = Column(JSON, nullable=False, default=dict)

    # Model settings
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=1000)
    supports_streaming = Column(Boolean, default=False)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=3000)

    # Costs (per 1000 tokens)
    cost_per_input_token = Column(Float, default=0.0)
    cost_per_output_token = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    bots = relationship("BotModel", back_populates="core_ai")

    # Indexes
    __table_args__ = (
        Index("idx_core_ai_provider", "provider"),
        Index("idx_core_ai_active", "is_active"),
        UniqueConstraint("name", "provider", name="uq_core_ai_name_provider"),
        CheckConstraint("default_temperature >= 0 AND default_temperature <= 2", name="ck_temperature_range"),
        CheckConstraint("default_max_tokens > 0", name="ck_max_tokens_positive"),
    )


class BotModel(Base):
    """Bot model"""
    __tablename__ = "bots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    bot_type = Column(Enum(BotTypeEnum), nullable=False)
    language = Column(String(10), nullable=False, default="en")
    status = Column(Enum(BotStatusEnum), nullable=False, default=BotStatusEnum.ACTIVE)

    # Foreign keys
    core_ai_id = Column(PGUUID(as_uuid=True), ForeignKey("core_ai.id"), nullable=False)
    platform_id = Column(PGUUID(as_uuid=True), ForeignKey("platforms.id"), nullable=False)

    # Configuration
    config = Column(JSON, nullable=False, default=dict)

    # Statistics
    active_conversations = Column(Integer, default=0, nullable=False)
    total_conversations = Column(Integer, default=0, nullable=False)
    total_messages = Column(Integer, default=0, nullable=False)

    # Settings
    max_concurrent_conversations = Column(Integer, default=100)
    is_active = Column(Boolean, default=True, nullable=False)

    # Expiration
    expiration_date = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    core_ai = relationship("CoreAIModel", back_populates="bots")
    platform = relationship("PlatformModel", back_populates="bots")
    conversations = relationship("ConversationModel", back_populates="bot")

    # Validation
    @validates('active_conversations')
    def validate_active_conversations(self, key, value):
        assert value >= 0, "Active conversations cannot be negative"
        return value

    # Indexes
    __table_args__ = (
        Index("idx_bots_type", "bot_type"),
        Index("idx_bots_status", "status"),
        Index("idx_bots_active", "is_active"),
        Index("idx_bots_platform", "platform_id"),
        Index("idx_bots_core_ai", "core_ai_id"),
        Index("idx_bots_expiration", "expiration_date"),
        CheckConstraint("active_conversations >= 0", name="ck_active_conversations_positive"),
        CheckConstraint("total_conversations >= 0", name="ck_total_conversations_positive"),
    )


class ConversationModel(Base):
    """Conversation model"""
    __tablename__ = "conversations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(String(100), nullable=False, unique=True)  # External conversation ID

    # Foreign keys
    bot_id = Column(PGUUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)

    # Status and priority
    status = Column(Enum(ConversationStatusEnum), nullable=False, default=ConversationStatusEnum.ACTIVE)
    priority = Column(Enum(ConversationPriorityEnum), nullable=False, default=ConversationPriorityEnum.NORMAL)

    # Context and metadata
    context = Column(JSON, nullable=False, default=dict)
    participants = Column(JSON, nullable=False, default=list)  # List of external user IDs
    meta_data = Column(JSON, nullable=False, default=dict)

    # Limits and timeouts
    max_messages = Column(Integer, default=100, nullable=False)
    timeout_minutes = Column(Integer, default=60, nullable=False)
    max_idle_minutes = Column(Integer, default=30, nullable=False)

    # Statistics
    message_count = Column(Integer, default=0, nullable=False)
    escalation_count = Column(Integer, default=0, nullable=False)
    transfer_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bot = relationship("BotModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", order_by="MessageModel.created_at")

    # Validation
    @validates('message_count')
    def validate_message_count(self, key, value):
        assert value >= 0, "Message count cannot be negative"
        return value

    # Indexes
    __table_args__ = (
        Index("idx_conversations_bot", "bot_id"),
        Index("idx_conversations_status", "status"),
        Index("idx_conversations_priority", "priority"),
        Index("idx_conversations_started_at", "started_at"),
        Index("idx_conversations_last_activity", "last_activity_at"),
        Index("idx_conversations_external_id", "conversation_id"),
        CheckConstraint("message_count >= 0", name="ck_message_count_positive"),
        CheckConstraint("max_messages > 0", name="ck_max_messages_positive"),
        CheckConstraint("timeout_minutes > 0", name="ck_timeout_positive"),
    )


class MessageModel(Base):
    """Message model"""
    __tablename__ = "messages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)

    # Message content
    content = Column(Text, nullable=False)
    role = Column(Enum(MessageRoleEnum), nullable=False)
    status = Column(Enum(MessageStatusEnum), nullable=False, default=MessageStatusEnum.PENDING)

    # AI processing
    confidence_score = Column(Float)
    ai_model = Column(String(100))
    processing_time_ms = Column(Integer)

    # Error handling
    error_reason = Column(Text)
    retry_count = Column(Integer, default=0, nullable=False)

    # Metadata
    meta_data = Column(JSON, nullable=False, default=dict)

    # External references
    external_message_id = Column(String(100))  # Platform-specific message ID

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True))

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")

    # Validation
    @validates('confidence_score')
    def validate_confidence_score(self, key, value):
        if value is not None:
            assert 0.0 <= value <= 1.0, "Confidence score must be between 0.0 and 1.0"
        return value

    @validates('retry_count')
    def validate_retry_count(self, key, value):
        assert value >= 0, "Retry count cannot be negative"
        return value

    # Indexes
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_role", "role"),
        Index("idx_messages_status", "status"),
        Index("idx_messages_created_at", "created_at"),
        Index("idx_messages_external_id", "external_message_id"),
        Index("idx_messages_confidence", "confidence_score"),
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
                       name="ck_confidence_range"),
        CheckConstraint("retry_count >= 0", name="ck_retry_count_positive"),
        CheckConstraint("processing_time_ms IS NULL OR processing_time_ms >= 0",
                       name="ck_processing_time_positive"),
    )