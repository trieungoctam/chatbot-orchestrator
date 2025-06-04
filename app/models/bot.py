"""
Bot Models
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base

class Bot(Base):
    # Bot instance configuration and management
    __tablename__ = "bots"

    # Bot configuration
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    core_ai_id = Column(UUID(as_uuid=True), ForeignKey("core_ai.id"))
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"))
    language = Column(String(10), default="vi")
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, default={})

    # Relationships
    core_ai = relationship("CoreAI", back_populates="bots")
    platform = relationship("Platform", back_populates="bots")
    conversations = relationship("Conversation", back_populates="bot")