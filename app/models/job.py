"""
Job Models for Background Processing
Updated to support the job processor requirements
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Enum, func, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

class JobStatus(str, enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Types of jobs that can be processed."""
    PROCESS_AI = "process_ai"

class Job(Base):
    """Job model for managing asynchronous processing tasks."""
    __tablename__ = "jobs"

    # Job configuration
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)

    # Priority and retry configuration
    priority = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Job data
    input_data = Column(JSON, default={})
    output_data = Column(JSON, default={})
    error_message = Column(Text)

    # Processing information
    processing_time_ms = Column(Integer)
    worker_id = Column(String(50))

    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    conversation = relationship("Conversation", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type={self.job_type}, status={self.status}, priority={self.priority})>"