from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    BOT = "bot"
    SALE = "sale"

# =============================== CoreAI ===============================

class CreateCoreAIRequest(BaseModel):
    name: str = Field(..., description="Name of the CoreAI")
    api_endpoint: str = Field(..., description="API Endpoint of the CoreAI")
    auth_required: bool = Field(False, description="Whether authentication is required")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    timeout_seconds: Optional[int] = Field(default=30, description="Timeout in seconds")
    is_active: bool = Field(True, description="Whether the CoreAI is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class UpdateCoreAIRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Name of the CoreAI")
    api_endpoint: Optional[str] = Field(default=None, description="API Endpoint of the CoreAI")
    auth_required: Optional[bool] = Field(default=None, description="Whether authentication is required")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    timeout_seconds: Optional[int] = Field(default=None, description="Timeout in seconds")
    is_active: Optional[bool] = Field(default=None, description="Whether the CoreAI is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

# =============================== Platform ===============================

class CreatePlatformRequest(BaseModel):
    name: str = Field(..., description="Name of the Platform")
    description: str = Field(..., description="Description of the Platform")
    base_url: str = Field(..., description="Base URL of the Platform")
    rate_limit_per_minute: Optional[int] = Field(default=60, description="Rate limit per minute")
    auth_required: bool = Field(default=False, description="Whether authentication is required")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    is_active: bool = Field(default=True, description="Whether the Platform is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class UpdatePlatformRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Name of the Platform")
    description: Optional[str] = Field(default=None, description="Description of the Platform")
    base_url: Optional[str] = Field(default=None, description="Base URL of the Platform")
    rate_limit_per_minute: Optional[int] = Field(default=None, description="Rate limit per minute")
    auth_required: Optional[bool] = Field(default=None, description="Whether authentication is required")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    is_active: Optional[bool] = Field(default=None, description="Whether the Platform is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class CreatePlatformActionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform ID")
    name: str = Field(..., description="Name of the Platform Action")
    description: Optional[str] = Field(default=None, description="Description of the Platform Action")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE)")
    path: str = Field(..., description="API path for the action")
    is_active: bool = Field(default=True, description="Whether the action is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class UpdatePlatformActionRequest(BaseModel):
    platform_id: Optional[str] = Field(default=None, description="Platform ID")
    name: Optional[str] = Field(default=None, description="Name of the Platform Action")
    description: Optional[str] = Field(default=None, description="Description of the Platform Action")
    method: Optional[str] = Field(default=None, description="HTTP method (GET, POST, PUT, DELETE)")
    path: Optional[str] = Field(default=None, description="API path for the action")
    is_active: Optional[bool] = Field(default=None, description="Whether the action is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

# =============================== Bot ===============================

class CreateBotRequest(BaseModel):
    name: str = Field(..., description="Name of the Bot")
    description: Optional[str] = Field(default=None, description="Description of the Bot")
    core_ai_id: str = Field(..., description="CoreAI ID")
    platform_id: str = Field(..., description="Platform ID")
    language: str = Field(default="vi", description="Language of the Bot")
    is_active: bool = Field(default=True, description="Whether the Bot is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class UpdateBotRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Name of the Bot")
    description: Optional[str] = Field(default=None, description="Description of the Bot")
    core_ai_id: Optional[str] = Field(default=None, description="CoreAI ID")
    platform_id: Optional[str] = Field(default=None, description="Platform ID")
    language: Optional[str] = Field(default=None, description="Language of the Bot")
    is_active: Optional[bool] = Field(default=None, description="Whether the Bot is active")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

# =============================== Conversation ===============================

class CreateConversationRequest(BaseModel):
    bot_id: str = Field(..., description="Bot ID")
    status: str = Field(default="active", description="Conversation status")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")
    history: Optional[str] = Field(default="", description="Conversation history")
    message_count: Optional[int] = Field(default=0, description="Number of messages")

class UpdateConversationRequest(BaseModel):
    bot_id: Optional[str] = Field(default=None, description="Bot ID")
    status: Optional[str] = Field(default=None, description="Conversation status")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")
    history: Optional[str] = Field(default=None, description="Conversation history")
    message_count: Optional[int] = Field(default=None, description="Number of messages")

# =============================== Message ===============================

class CreateMessageRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    content: str = Field(..., description="Message content")
    message_role: MessageRole = Field(..., description="Message role (user, bot, sale)")
    content_type: str = Field(default="text/plain", description="Content type")

class UpdateMessageRequest(BaseModel):
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    content: Optional[str] = Field(default=None, description="Message content")
    message_role: Optional[MessageRole] = Field(default=None, description="Message role (user, bot, sale)")
    content_type: Optional[str] = Field(default=None, description="Content type")

class MessageRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    history: str = Field(..., description="History string")
    resources: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

# =============================== Chat/Pancake ===============================

class PancakeMessageRequest(BaseModel):
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID - will be auto-generated if not provided")
    history: str = Field(..., description="Conversation history string")
    resources: Optional[Dict[str, Any]] = Field(default=None, description="Additional context and resources")