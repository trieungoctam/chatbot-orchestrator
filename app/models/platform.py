from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base

class Platform(Base):
    # Platform layer for API routing and webhook management
    __tablename__ = "platforms"

    # Platform configuration
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    base_url = Column(String(255), nullable=False)
    rate_limit_per_minute = Column(Integer, default=60)
    auth_required = Column(Boolean, default=False)
    auth_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, default={})

    # Relationships
    bots = relationship("Bot", back_populates="platform")
    actions = relationship("PlatformAction", back_populates="platform")

class PlatformAction(Base):
    # Platform action model
    __tablename__ = "platform_actions"

    # Platform action configuration
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, default={})

    # Relationships
    platform = relationship("Platform", back_populates="actions")