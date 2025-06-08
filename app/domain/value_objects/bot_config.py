# 📁 app/domain/value_objects/bot_config.py
"""
Bot Configuration Value Object
Immutable configuration data với business validation
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum

from app.domain.exceptions import DomainError


class AIProvider(Enum):
    """AI Provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


class PlatformType(Enum):
    """Platform types"""
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    WEB = "web"
    API = "api"


@dataclass(frozen=True)
class BotConfig:
    """
    Bot Configuration Value Object

    Business Rules:
    1. AI model must be compatible with provider
    2. Platform type must be supported
    3. Response time limits must be reasonable
    4. Language settings must be valid
    5. Resource limits must be positive
    """

    # AI Configuration
    ai_provider: AIProvider
    ai_model: str
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1000
    ai_timeout_seconds: int = 30

    # Platform Configuration
    platform_type: PlatformType
    platform_webhook_url: Optional[str] = None
    platform_api_version: str = "v1"

    # Response Configuration
    max_response_time_ms: int = 5000
    max_conversation_length: int = 100
    supports_multilingual: bool = False
    supported_languages: Set[str] = None

    # Operational Configuration
    is_enabled: bool = True
    expires_at: Optional[datetime] = None
    max_concurrent_users: int = 100
    rate_limit_per_minute: int = 60

    # Features
    enable_context_memory: bool = True
    enable_sentiment_analysis: bool = False
    enable_auto_escalation: bool = True
    auto_escalation_threshold: float = 0.3

    def __post_init__(self):
        """Validate configuration on creation"""
        self._validate_configuration()

        # Set default supported languages
        if self.supported_languages is None:
            object.__setattr__(self, 'supported_languages', {'vi', 'en'})

    def _validate_configuration(self):
        """Validate configuration business rules"""

        # AI Configuration validation
        if self.ai_temperature < 0.0 or self.ai_temperature > 2.0:
            raise DomainError("AI temperature must be between 0.0 and 2.0")

        if self.ai_max_tokens < 1 or self.ai_max_tokens > 4000:
            raise DomainError("AI max tokens must be between 1 and 4000")

        if self.ai_timeout_seconds < 1 or self.ai_timeout_seconds > 300:
            raise DomainError("AI timeout must be between 1 and 300 seconds")

        # Platform configuration validation
        if self.platform_type == PlatformType.WEB and not self.platform_webhook_url:
            raise DomainError("Web platform requires webhook URL")

        # Response configuration validation
        if self.max_response_time_ms < 100 or self.max_response_time_ms > 30000:
            raise DomainError("Max response time must be between 100ms and 30s")

        if self.max_conversation_length < 1:
            raise DomainError("Max conversation length must be at least 1")

        # Resource limits validation
        if self.max_concurrent_users < 1:
            raise DomainError("Max concurrent users must be at least 1")

        if self.rate_limit_per_minute < 1:
            raise DomainError("Rate limit must be at least 1 request per minute")

        # Auto escalation validation
        if self.auto_escalation_threshold < 0.0 or self.auto_escalation_threshold > 1.0:
            raise DomainError("Auto escalation threshold must be between 0.0 and 1.0")

        # Expiry validation
        if self.expires_at and self.expires_at <= datetime.utcnow():
            raise DomainError("Expiry date must be in the future")

        # AI model compatibility validation
        self._validate_ai_model_compatibility()

    def _validate_ai_model_compatibility(self):
        """Validate AI model compatibility with provider"""

        compatible_models = {
            AIProvider.OPENAI: ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
            AIProvider.ANTHROPIC: ['claude-v1', 'claude-v2', 'claude-instant'],
            AIProvider.GOOGLE: ['bard', 'palm-2'],
            AIProvider.CUSTOM: []  # Any model allowed for custom provider
        }

        if self.ai_provider != AIProvider.CUSTOM:
            allowed_models = compatible_models.get(self.ai_provider, [])
            if self.ai_model not in allowed_models:
                raise DomainError(
                    f"AI model '{self.ai_model}' is not compatible with "
                    f"provider '{self.ai_provider.value}'"
                )

    # === BUSINESS LOGIC METHODS ===

    def is_valid(self) -> bool:
        """Check if configuration is valid for operation"""
        try:
            self._validate_configuration()
            return self.is_enabled and not self.is_expired()
        except DomainError:
            return False

    def is_operational(self) -> bool:
        """Check if bot can operate with this configuration"""
        return (
            self.is_valid() and
            self.ai_provider is not None and
            self.platform_type is not None
        )

    def is_expired(self) -> bool:
        """Check if configuration has expired"""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at

    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time until configuration expires"""
        if not self.expires_at:
            return None

        time_left = self.expires_at - datetime.utcnow()
        return time_left if time_left.total_seconds() > 0 else timedelta(0)

    def supports_language(self, language: str) -> bool:
        """Check if configuration supports specific language"""
        if not self.supports_multilingual:
            return language in {'vi', 'en'}  # Default languages

        return language in self.supported_languages

    def can_handle_concurrent_load(self, current_load: int) -> bool:
        """Check if can handle additional concurrent load"""
        return current_load < self.max_concurrent_users

    def should_escalate(self, confidence_score: float) -> bool:
        """Check if should auto-escalate based on confidence"""
        return (
            self.enable_auto_escalation and
            confidence_score < self.auto_escalation_threshold
        )

    def core_settings_changed(self, other: 'BotConfig') -> bool:
        """Check if core settings have changed (requires restart)"""
        core_fields = [
            'ai_provider', 'ai_model', 'platform_type',
            'max_concurrent_users', 'rate_limit_per_minute'
        ]

        for field in core_fields:
            if getattr(self, field) != getattr(other, field):
                return True

        return False

    def update_ai_settings(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> 'BotConfig':
        """Create new config with updated AI settings"""

        return BotConfig(
            ai_provider=self.ai_provider,
            ai_model=self.ai_model,
            ai_temperature=temperature if temperature is not None else self.ai_temperature,
            ai_max_tokens=max_tokens if max_tokens is not None else self.ai_max_tokens,
            ai_timeout_seconds=timeout_seconds if timeout_seconds is not None else self.ai_timeout_seconds,
            platform_type=self.platform_type,
            platform_webhook_url=self.platform_webhook_url,
            platform_api_version=self.platform_api_version,
            max_response_time_ms=self.max_response_time_ms,
            max_conversation_length=self.max_conversation_length,
            supports_multilingual=self.supports_multilingual,
            supported_languages=self.supported_languages,
            is_enabled=self.is_enabled,
            expires_at=self.expires_at,
            max_concurrent_users=self.max_concurrent_users,
            rate_limit_per_minute=self.rate_limit_per_minute,
            enable_context_memory=self.enable_context_memory,
            enable_sentiment_analysis=self.enable_sentiment_analysis,
            enable_auto_escalation=self.enable_auto_escalation,
            auto_escalation_threshold=self.auto_escalation_threshold
        )

    def enable_feature(self, feature: str, enabled: bool = True) -> 'BotConfig':
        """Create new config with feature enabled/disabled"""

        feature_mapping = {
            'multilingual': 'supports_multilingual',
            'context_memory': 'enable_context_memory',
            'sentiment': 'enable_sentiment_analysis',
            'auto_escalation': 'enable_auto_escalation'
        }

        if feature not in feature_mapping:
            raise DomainError(f"Unknown feature: {feature}")

        field_name = feature_mapping[feature]
        current_value = getattr(self, field_name)

        if current_value == enabled:
            return self  # No change needed

        # Create new config with updated feature
        kwargs = {field: getattr(self, field) for field in self.__dataclass_fields__}
        kwargs[field_name] = enabled

        return BotConfig(**kwargs)