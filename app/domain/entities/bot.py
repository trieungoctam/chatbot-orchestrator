# 📁 app/domain/entities/bot.py
"""
Bot Entity - Core business model của chatbot system
Chứa tất cả business rules và logic liên quan đến Bot
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum

from app.domain.exceptions import DomainError
from app.domain.value_objects.bot_config import BotConfig


class BotStatus(Enum):
    """Bot status enumeration"""
    DRAFT = "draft"           # Bot đang được tạo
    ACTIVE = "active"         # Bot hoạt động bình thường
    INACTIVE = "inactive"     # Bot tạm dừng
    MAINTENANCE = "maintenance"  # Bot đang bảo trì
    ARCHIVED = "archived"     # Bot đã lưu trữ


class BotType(Enum):
    """Bot type classification"""
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"
    GENERAL = "general"


@dataclass(frozen=True)  # Immutable - Thread safe, predictable
class Bot:
    """
    Bot Domain Entity

    Business Rules:
    1. Bot name must be unique và không empty
    2. Bot phải có CoreAI và Platform valid
    3. Bot chỉ xử lý message khi status = ACTIVE
    4. Bot có giới hạn conversation đồng thời
    5. Bot có expiration date (optional)
    """

    # Identity
    id: UUID
    name: str

    # Basic Info
    description: Optional[str]
    bot_type: BotType
    language: str

    # Dependencies
    core_ai_id: UUID
    platform_id: UUID

    # Configuration
    config: BotConfig
    status: BotStatus

    # Metadata
    created_at: datetime
    updated_at: datetime
    version: int = 1

    # Business metrics
    total_conversations: int = 0
    active_conversations: int = 0
    max_concurrent_conversations: int = 100

    def __post_init__(self):
        """Validate business rules khi tạo entity"""
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Core business rules validation"""

        # Rule 1: Name validation
        if not self.name or len(self.name.strip()) < 2:
            raise DomainError("Bot name must be at least 2 characters")

        if len(self.name) > 100:
            raise DomainError("Bot name cannot exceed 100 characters")

        # Rule 2: Language validation
        if self.language not in ['vi', 'en', 'ja', 'ko', 'zh']:
            raise DomainError(f"Unsupported language: {self.language}")

        # Rule 3: Dependencies validation
        if not self.core_ai_id:
            raise DomainError("Bot must have a Core AI configuration")

        if not self.platform_id:
            raise DomainError("Bot must have a Platform configuration")

        # Rule 4: Configuration validation
        if not self.config.is_valid():
            raise DomainError("Bot configuration is invalid")

        # Rule 5: Concurrent conversations limit
        if self.max_concurrent_conversations < 1:
            raise DomainError("Max concurrent conversations must be at least 1")

        if self.active_conversations > self.max_concurrent_conversations:
            raise DomainError("Active conversations exceed maximum limit")

    # === BUSINESS LOGIC METHODS ===

    def can_handle_new_conversation(self) -> bool:
        """
        Business Logic: Check if bot can accept new conversation

        Rules:
        - Status must be ACTIVE
        - Not exceed max concurrent conversations
        - Not expired (if has expiration)
        - Configuration must be valid
        """
        if self.status != BotStatus.ACTIVE:
            return False

        if self.active_conversations >= self.max_concurrent_conversations:
            return False

        if self.config.expires_at and datetime.utcnow() > self.config.expires_at:
            return False

        return self.config.is_operational()

    def can_handle_language(self, language: str) -> bool:
        """Business Logic: Check if bot supports specific language"""
        if self.language == language:
            return True

        # Multi-language support check
        return self.config.supports_multilingual and language in self.config.supported_languages

    def start_conversation(self) -> 'Bot':
        """
        Business Logic: Start new conversation
        Returns new Bot instance (immutable pattern)
        """
        if not self.can_handle_new_conversation():
            raise DomainError("Bot cannot handle new conversation at this time")

        return Bot(
            id=self.id,
            name=self.name,
            description=self.description,
            bot_type=self.bot_type,
            language=self.language,
            core_ai_id=self.core_ai_id,
            platform_id=self.platform_id,
            config=self.config,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            version=self.version,
            total_conversations=self.total_conversations + 1,
            active_conversations=self.active_conversations + 1,
            max_concurrent_conversations=self.max_concurrent_conversations
        )

    def end_conversation(self) -> 'Bot':
        """Business Logic: End conversation"""
        if self.active_conversations <= 0:
            raise DomainError("No active conversations to end")

        return Bot(
            id=self.id,
            name=self.name,
            description=self.description,
            bot_type=self.bot_type,
            language=self.language,
            core_ai_id=self.core_ai_id,
            platform_id=self.platform_id,
            config=self.config,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            version=self.version,
            total_conversations=self.total_conversations,
            active_conversations=self.active_conversations - 1,
            max_concurrent_conversations=self.max_concurrent_conversations
        )

    def activate(self) -> 'Bot':
        """Business Logic: Activate bot"""
        if self.status == BotStatus.ARCHIVED:
            raise DomainError("Cannot activate archived bot")

        # Validate configuration before activation
        if not self.config.is_valid():
            raise DomainError("Cannot activate bot with invalid configuration")

        return self._update_status(BotStatus.ACTIVE)

    def deactivate(self) -> 'Bot':
        """Business Logic: Deactivate bot"""
        if self.active_conversations > 0:
            raise DomainError("Cannot deactivate bot with active conversations")

        return self._update_status(BotStatus.INACTIVE)

    def start_maintenance(self) -> 'Bot':
        """Business Logic: Put bot in maintenance mode"""
        return self._update_status(BotStatus.MAINTENANCE)

    def update_config(self, new_config: BotConfig) -> 'Bot':
        """Business Logic: Update bot configuration"""
        if not new_config.is_valid():
            raise DomainError("New configuration is invalid")

        # Business rule: Cannot change core config while having active conversations
        if (self.active_conversations > 0 and
            self.config.core_settings_changed(new_config)):
            raise DomainError("Cannot change core settings while having active conversations")

        return Bot(
            id=self.id,
            name=self.name,
            description=self.description,
            bot_type=self.bot_type,
            language=self.language,
            core_ai_id=self.core_ai_id,
            platform_id=self.platform_id,
            config=new_config,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            version=self.version + 1,  # Increment version for config changes
            total_conversations=self.total_conversations,
            active_conversations=self.active_conversations,
            max_concurrent_conversations=self.max_concurrent_conversations
        )

    def _update_status(self, new_status: BotStatus) -> 'Bot':
        """Helper method to update status"""
        return Bot(
            id=self.id,
            name=self.name,
            description=self.description,
            bot_type=self.bot_type,
            language=self.language,
            core_ai_id=self.core_ai_id,
            platform_id=self.platform_id,
            config=self.config,
            status=new_status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            version=self.version,
            total_conversations=self.total_conversations,
            active_conversations=self.active_conversations,
            max_concurrent_conversations=self.max_concurrent_conversations
        )

    # === QUERY METHODS ===

    def is_operational(self) -> bool:
        """Check if bot is fully operational"""
        return (
            self.status == BotStatus.ACTIVE and
            self.config.is_operational() and
            (not self.config.expires_at or datetime.utcnow() < self.config.expires_at)
        )

    def get_load_percentage(self) -> float:
        """Get current load percentage"""
        if self.max_concurrent_conversations == 0:
            return 0.0
        return (self.active_conversations / self.max_concurrent_conversations) * 100

    def is_overloaded(self, threshold: float = 90.0) -> bool:
        """Check if bot is overloaded"""
        return self.get_load_percentage() >= threshold

    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time until bot expires"""
        if not self.config.expires_at:
            return None

        time_left = self.config.expires_at - datetime.utcnow()
        return time_left if time_left.total_seconds() > 0 else timedelta(0)