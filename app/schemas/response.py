from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    BOT = "bot"
    SALE = "sale"

# =============================== CoreAI ===============================

class CoreAIResponse(BaseModel):
    id: str
    name: str
    api_endpoint: str
    auth_required: bool
    auth_token: Optional[str] = None
    timeout_seconds: Optional[int] = None
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class CoreAIListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[CoreAIResponse]] = None

class UpdateCoreAIResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[CoreAIResponse] = None

class CreateCoreAIResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[CoreAIResponse] = None

# =============================== Bot ===============================

class BotResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    core_ai_id: str
    platform_id: str
    language: str
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class CreateBotResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[BotResponse] = None

class UpdateBotResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[BotResponse] = None

class BotListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[BotResponse]] = None

# =============================== Conversation ===============================

class ConversationResponse(BaseModel):
    id: str
    bot_id: str
    status: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[str] = None
    message_count: int
    created_at: datetime
    updated_at: datetime

class CreateConversationResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[ConversationResponse] = None

class UpdateConversationResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[ConversationResponse] = None

class ConversationListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[ConversationResponse]] = None

# =============================== Message ===============================

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    content: str
    message_role: MessageRole
    content_type: str
    created_at: datetime
    updated_at: datetime

class CreateMessageResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[MessageResponse] = None

class UpdateMessageResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[MessageResponse] = None

class MessageListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[MessageResponse]] = None

# =============================== Platform ===============================

class PlatformResponse(BaseModel):
    id: str
    name: str
    description: str
    base_url: str
    rate_limit_per_minute: Optional[int] = None
    auth_required: bool
    auth_token: Optional[str] = None
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class CreatePlatformResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[PlatformResponse] = None

class UpdatePlatformResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[PlatformResponse] = None

class PlatformListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[PlatformResponse]] = None

# =============================== Platform Action ===============================

class PlatformActionResponse(BaseModel):
    id: str
    platform_id: str
    platform_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    method: str
    path: str
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class CreatePlatformActionResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[PlatformActionResponse] = None

class UpdatePlatformActionResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[PlatformActionResponse] = None

class PlatformActionListResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[List[PlatformActionResponse]] = None

# =============================== General ===============================

class ContextLimitInfo(BaseModel):
    max_messages: int = Field(..., description="Maximum number of messages kept in context")
    max_chars: int = Field(..., description="Maximum number of characters kept in context")
    actual_messages: int = Field(..., description="Actual number of messages in processed context")

class GeneralMessageResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None

# =============================== Chat/Pancake ===============================

class PancakeMessageResponse(BaseModel):
    success: bool = Field(..., description="Whether the message processing was successful")
    status: str = Field(..., description="Status of the message processing")
    message: Optional[str] = Field(default=None, description="Result message or description")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")

    # Additional fields for enhanced MessageHandler
    action: Optional[str] = Field(default=None, description="Action taken by the message handler")
    ai_job_id: Optional[str] = Field(default=None, description="AI processing job ID")
    lock_id: Optional[str] = Field(default=None, description="Message lock ID")
    consolidated_messages: Optional[int] = Field(default=None, description="Number of consolidated messages")
    bot_name: Optional[str] = Field(default=None, description="Name of the bot handling the message")

    # New fields for job cancellation and reprocessing
    consolidated_count: Optional[int] = Field(default=None, description="Total number of consolidated message batches")
    cancelled_previous_job: Optional[str] = Field(default=None, description="ID of cancelled previous AI job")
    reprocessing: Optional[bool] = Field(default=False, description="Whether this is a reprocessing request")
    lock_updated: Optional[bool] = Field(default=False, description="Whether an existing lock was updated")

    # New field for context chunking information
    context_limit: Optional[ContextLimitInfo] = Field(default=None, description="Information about context chunking limits and results")