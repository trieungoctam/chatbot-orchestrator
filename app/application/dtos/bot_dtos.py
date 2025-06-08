"""
Bot Data Transfer Objects
DTOs for Bot-related operations between Application and other layers
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from app.application.exceptions import ValidationError


class BotStatusDTO(Enum):
    """Bot status DTO"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class BotTypeDTO(Enum):
    """Bot type DTO"""
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"
    GENERAL = "general"


@dataclass
class BotConfigDTO:
    """Bot configuration DTO"""
    ai_provider: str
    ai_model: str
    ai_temperature: float
    ai_max_tokens: int
    platform_type: str
    max_concurrent_users: int
    max_conversation_length: int
    enable_sentiment_analysis: bool
    enable_intent_recognition: bool
    response_timeout_seconds: int
    supported_languages: List[str]

    def __post_init__(self):
        """Validate DTO data"""
        if not (0.0 <= self.ai_temperature <= 2.0):
            raise ValidationError("ai_temperature", self.ai_temperature, "Must be between 0.0 and 2.0")

        if self.ai_max_tokens <= 0:
            raise ValidationError("ai_max_tokens", self.ai_max_tokens, "Must be positive")

        if self.max_concurrent_users <= 0:
            raise ValidationError("max_concurrent_users", self.max_concurrent_users, "Must be positive")

        if self.response_timeout_seconds <= 0:
            raise ValidationError("response_timeout_seconds", self.response_timeout_seconds, "Must be positive")


@dataclass
class CreateBotDTO:
    """DTO for creating a new bot"""
    name: str
    description: Optional[str]
    bot_type: BotTypeDTO
    language: str
    core_ai_id: UUID
    platform_id: UUID
    config: BotConfigDTO

    def __post_init__(self):
        """Validate DTO data"""
        if not self.name or len(self.name.strip()) == 0:
            raise ValidationError("name", self.name, "Bot name cannot be empty")

        if len(self.name) > 100:
            raise ValidationError("name", self.name, "Bot name cannot exceed 100 characters")

        if not self.language or len(self.language) != 2:
            raise ValidationError("language", self.language, "Language must be 2-character code")


@dataclass
class UpdateBotDTO:
    """DTO for updating bot configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    bot_type: Optional[BotTypeDTO] = None
    language: Optional[str] = None
    config: Optional[BotConfigDTO] = None

    def __post_init__(self):
        """Validate DTO data"""
        if self.name is not None:
            if not self.name or len(self.name.strip()) == 0:
                raise ValidationError("name", self.name, "Bot name cannot be empty")

            if len(self.name) > 100:
                raise ValidationError("name", self.name, "Bot name cannot exceed 100 characters")

        if self.language is not None:
            if not self.language or len(self.language) != 2:
                raise ValidationError("language", self.language, "Language must be 2-character code")


@dataclass
class BotDTO:
    """Bot data transfer object"""
    id: UUID
    name: str
    description: Optional[str]
    bot_type: BotTypeDTO
    language: str
    core_ai_id: UUID
    platform_id: UUID
    config: BotConfigDTO
    status: BotStatusDTO
    active_conversations: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expiration_date: Optional[datetime] = None

    @property
    def load_percentage(self) -> float:
        """Calculate current load percentage"""
        if self.config.max_concurrent_users == 0:
            return 0.0
        return (self.active_conversations / self.config.max_concurrent_users) * 100

    @property
    def is_overloaded(self) -> bool:
        """Check if bot is overloaded"""
        return self.load_percentage >= 90.0

    @property
    def can_accept_conversations(self) -> bool:
        """Check if bot can accept new conversations"""
        return (
            self.status == BotStatusDTO.ACTIVE and
            self.is_active and
            not self.is_overloaded and
            (self.expiration_date is None or self.expiration_date > datetime.utcnow())
        )


@dataclass
class BotListDTO:
    """DTO for bot list responses"""
    bots: List[BotDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclass
class BotStatsDTO:
    """Bot statistics DTO"""
    bot_id: UUID
    total_conversations: int
    active_conversations: int
    completed_conversations: int
    failed_conversations: int
    average_conversation_duration: float
    average_messages_per_conversation: float
    user_satisfaction_score: Optional[float]
    last_activity: Optional[datetime]
    uptime_percentage: float


@dataclass
class BotOperationDTO:
    """DTO for bot operations (activate, deactivate, etc.)"""
    bot_id: UUID
    operation: str
    reason: Optional[str] = None
    performed_by: Optional[str] = None

    def __post_init__(self):
        """Validate DTO data"""
        valid_operations = {"activate", "deactivate", "start_maintenance", "end_maintenance", "suspend"}
        if self.operation not in valid_operations:
            raise ValidationError("operation", self.operation, f"Must be one of {valid_operations}")


@dataclass
class BotSearchDTO:
    """DTO for bot search requests"""
    query: Optional[str] = None
    bot_type: Optional[BotTypeDTO] = None
    status: Optional[BotStatusDTO] = None
    language: Optional[str] = None
    platform_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

    def __post_init__(self):
        """Validate DTO data"""
        if self.page < 1:
            raise ValidationError("page", self.page, "Page must be >= 1")

        if not (1 <= self.page_size <= 100):
            raise ValidationError("page_size", self.page_size, "Page size must be between 1 and 100")

        valid_sort_fields = {"name", "created_at", "updated_at", "active_conversations"}
        if self.sort_by not in valid_sort_fields:
            raise ValidationError("sort_by", self.sort_by, f"Must be one of {valid_sort_fields}")

        if self.sort_order not in {"asc", "desc"}:
