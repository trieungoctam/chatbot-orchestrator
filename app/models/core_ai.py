"""
AI Core Models
"""

from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base

class CoreAI(Base):
    # Core AI processing engine configuration
    __tablename__ = "core_ai"

    # Core AI configuration
    name = Column(String(100), nullable=False, unique=True)
    api_endpoint = Column(String(255), nullable=False)
    auth_required = Column(Boolean, default=False)
    auth_token = Column(String(255), nullable=True)
    timeout_seconds = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, default={})

    # Relationships
    bots = relationship("Bot", back_populates="core_ai")