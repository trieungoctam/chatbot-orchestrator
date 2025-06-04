from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum
from sqlalchemy import Enum
from sqlalchemy.sql import func

from app.db.base import Base

class Conversation(Base):
    """Conversation model for persistent storage"""

    __tablename__ = "conversations"

    # Basic conversation info
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, ended, transferred

    # Conversation metadata
    context = Column(JSONB, default=dict)
    history = Column(Text, default="")
    message_count = Column(Integer, default=0)

    # Relationships
    bot = relationship("Bot", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, status={self.status})>"

class MessageRole(str, enum.Enum):
    """Message role."""
    USER = "user"
    BOT = "bot"
    SALE = "sale"

class Message(Base):
    """Message model for storing conversation messages"""

    __tablename__ = "messages"

    # Message identification
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)

    # Message content
    content = Column(Text, nullable=False)
    message_role = Column(Enum(MessageRole), nullable=False)
    content_type = Column(String(50), default="text/plain")

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.message_role})>"