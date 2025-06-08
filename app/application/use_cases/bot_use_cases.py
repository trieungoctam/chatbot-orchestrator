"""
Bot Use Cases
Application services for Bot management operations
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

from app.domain.entities.bot import Bot
from app.domain.repositories.bot_repository import IBotRepository
from app.domain.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    InvalidOperationError
)
from app.application.dtos.bot_dtos import (
    CreateBotDTO,
    UpdateBotDTO,
    BotDTO,
    BotListDTO,
    BotStatsDTO,
    BotOperationDTO,
    BotSearchDTO,
    BotStatusDTO,
    BotTypeDTO,
    BotConfigDTO
)
from app.application.exceptions import (
    UseCaseError,
    ResourceNotFoundError,
    ValidationError
)

logger = structlog.get_logger(__name__)


class BotUseCases:
    """
    Application services for Bot management

    Orchestrates bot operations and coordinates between Domain and Infrastructure layers
    """

    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository

    async def create_bot(self, create_dto: CreateBotDTO) -> BotDTO:
        """
        Create new bot with business validation

        Args:
            create_dto: Bot creation data

        Returns:
            BotDTO: Created bot information

        Raises:
            UseCaseError: If bot creation fails
            ValidationError: If input data is invalid
        """
        try:
            logger.info("Creating new bot", name=create_dto.name)

            # Convert DTO to Domain Value Object
            bot_config = self._dto_to_domain_config(create_dto.config)

            # Create Domain Entity
            bot = Bot(
                id=UUID(int=0),  # Will be set by repository
                name=create_dto.name,
                description=create_dto.description,
                bot_type=self._dto_to_domain_type(create_dto.bot_type),
                language=create_dto.language,
                core_ai_id=create_dto.core_ai_id,
                platform_id=create_dto.platform_id,
                config=bot_config
            )

            # Apply business rules
            if not bot.is_operational():
                raise BusinessRuleViolationError(
                    "BOT_NOT_OPERATIONAL",
                    "Bot configuration is not valid for operation"
                )

            # Persist
            created_bot = await self.bot_repository.create(bot)

            logger.info("Bot created successfully", bot_id=str(created_bot.id))
            return self._domain_to_dto(created_bot)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during bot creation", error=str(e))
            raise UseCaseError("create_bot", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during bot creation", error=str(e))
            raise UseCaseError("create_bot", f"Failed to create bot: {str(e)}")

    async def get_bot_by_id(self, bot_id: UUID) -> BotDTO:
        """
        Get bot by ID

        Args:
            bot_id: Bot identifier

        Returns:
            BotDTO: Bot information

        Raises:
            ResourceNotFoundError: If bot not found
        """
        try:
            bot = await self.bot_repository.get_by_id(bot_id)
            if not bot:
                raise ResourceNotFoundError("Bot", str(bot_id))

            return self._domain_to_dto(bot)

        except Exception as e:
            logger.error("Error getting bot", bot_id=str(bot_id), error=str(e))
            raise UseCaseError("get_bot_by_id", f"Failed to get bot: {str(e)}")

    async def update_bot(self, bot_id: UUID, update_dto: UpdateBotDTO) -> BotDTO:
        """
        Update bot configuration

        Args:
            bot_id: Bot identifier
            update_dto: Update data

        Returns:
            BotDTO: Updated bot information

        Raises:
            ResourceNotFoundError: If bot not found
            UseCaseError: If update fails
        """
        try:
            logger.info("Updating bot", bot_id=str(bot_id))

            # Get existing bot
            existing_bot = await self.bot_repository.get_by_id(bot_id)
            if not existing_bot:
                raise ResourceNotFoundError("Bot", str(bot_id))

            # Apply updates
            updated_bot = existing_bot

            if update_dto.name is not None:
                updated_bot = updated_bot._replace(name=update_dto.name)

            if update_dto.description is not None:
                updated_bot = updated_bot._replace(description=update_dto.description)

            if update_dto.bot_type is not None:
                updated_bot = updated_bot._replace(
                    bot_type=self._dto_to_domain_type(update_dto.bot_type)
                )

            if update_dto.language is not None:
                updated_bot = updated_bot._replace(language=update_dto.language)

            if update_dto.config is not None:
                new_config = self._dto_to_domain_config(update_dto.config)
                updated_bot = updated_bot.update_config(new_config)

            # Validate business rules
            if not updated_bot.is_operational():
                raise BusinessRuleViolationError(
                    "BOT_NOT_OPERATIONAL",
                    "Updated bot configuration is not valid for operation"
                )

            # Persist
            saved_bot = await self.bot_repository.update(updated_bot)

            logger.info("Bot updated successfully", bot_id=str(bot_id))
            return self._domain_to_dto(saved_bot)

        except (BusinessRuleViolationError, EntityNotFoundError) as e:
            logger.error("Domain error during bot update", bot_id=str(bot_id), error=str(e))
            raise UseCaseError("update_bot", str(e), getattr(e, 'error_code', None))
        except Exception as e:
            logger.error("Unexpected error during bot update", bot_id=str(bot_id), error=str(e))
            raise UseCaseError("update_bot", f"Failed to update bot: {str(e)}")

    async def perform_bot_operation(self, operation_dto: BotOperationDTO) -> BotDTO:
        """
        Perform bot operation (activate, deactivate, etc.)

        Args:
            operation_dto: Operation details

        Returns:
            BotDTO: Updated bot information
        """
        try:
            logger.info("Performing bot operation",
                       bot_id=str(operation_dto.bot_id),
                       operation=operation_dto.operation)

            # Get bot
            bot = await self.bot_repository.get_by_id(operation_dto.bot_id)
            if not bot:
                raise ResourceNotFoundError("Bot", str(operation_dto.bot_id))

            # Perform operation
            if operation_dto.operation == "activate":
                updated_bot = bot.activate()
            elif operation_dto.operation == "deactivate":
                updated_bot = bot.deactivate()
            elif operation_dto.operation == "start_maintenance":
                updated_bot = bot.start_maintenance()
            elif operation_dto.operation == "end_maintenance":
                updated_bot = bot.end_maintenance()
            elif operation_dto.operation == "suspend":
                updated_bot = bot.suspend()
            else:
                raise ValidationError("operation", operation_dto.operation, "Invalid operation")

            # Persist
            saved_bot = await self.bot_repository.update(updated_bot)

            logger.info("Bot operation completed successfully",
                       bot_id=str(operation_dto.bot_id),
                       operation=operation_dto.operation)
            return self._domain_to_dto(saved_bot)

        except (BusinessRuleViolationError, InvalidOperationError) as e:
            logger.error("Domain error during bot operation",
                        bot_id=str(operation_dto.bot_id),
                        operation=operation_dto.operation,
                        error=str(e))
            raise UseCaseError("perform_bot_operation", str(e), getattr(e, 'error_code', None))
        except Exception as e:
            logger.error("Unexpected error during bot operation",
                        bot_id=str(operation_dto.bot_id),
                        error=str(e))
            raise UseCaseError("perform_bot_operation", f"Failed to perform operation: {str(e)}")

    async def search_bots(self, search_dto: BotSearchDTO) -> BotListDTO:
        """
        Search bots with filters

        Args:
            search_dto: Search criteria

        Returns:
            BotListDTO: List of matching bots
        """
        try:
            logger.info("Searching bots", query=search_dto.query)

            # Convert DTO filters to repository format
            filters = {}
            if search_dto.bot_type:
                filters['bot_type'] = self._dto_to_domain_type(search_dto.bot_type)
            if search_dto.status:
                filters['status'] = self._dto_to_domain_status(search_dto.status)
            if search_dto.language:
                filters['language'] = search_dto.language
            if search_dto.platform_id:
                filters['platform_id'] = search_dto.platform_id
            if search_dto.is_active is not None:
                filters['is_active'] = search_dto.is_active

            # Search
            bots, total_count = await self.bot_repository.search(
                query=search_dto.query,
                filters=filters,
                page=search_dto.page,
                page_size=search_dto.page_size,
                sort_by=search_dto.sort_by,
                sort_order=search_dto.sort_order
            )

            # Convert to DTOs
            bot_dtos = [self._domain_to_dto(bot) for bot in bots]

            return BotListDTO(
                bots=bot_dtos,
                total_count=total_count,
                page=search_dto.page,
                page_size=search_dto.page_size,
                has_next=(search_dto.page * search_dto.page_size) < total_count,
                has_previous=search_dto.page > 1
            )

        except Exception as e:
            logger.error("Error searching bots", error=str(e))
            raise UseCaseError("search_bots", f"Failed to search bots: {str(e)}")

    async def get_bot_statistics(self, bot_id: UUID) -> BotStatsDTO:
        """
        Get bot statistics

        Args:
            bot_id: Bot identifier

        Returns:
            BotStatsDTO: Bot statistics
        """
        try:
            stats = await self.bot_repository.get_statistics(bot_id)
            if not stats:
                raise ResourceNotFoundError("Bot", str(bot_id))

            return BotStatsDTO(**stats)

        except Exception as e:
            logger.error("Error getting bot statistics", bot_id=str(bot_id), error=str(e))
            raise UseCaseError("get_bot_statistics", f"Failed to get statistics: {str(e)}")

    async def delete_bot(self, bot_id: UUID) -> bool:
        """
        Delete bot (soft delete)

        Args:
            bot_id: Bot identifier

        Returns:
            True if deleted successfully
        """
        try:
            logger.info("Deleting bot", bot_id=str(bot_id))

            # Check if bot can be deleted
            bot = await self.bot_repository.get_by_id(bot_id)
            if not bot:
                raise ResourceNotFoundError("Bot", str(bot_id))

            # Check if bot has active conversations
            if bot.active_conversations > 0:
                raise BusinessRuleViolationError(
                    "BOT_HAS_ACTIVE_CONVERSATIONS",
                    f"Cannot delete bot with {bot.active_conversations} active conversations"
                )

            # Deactivate bot first
            deactivated_bot = bot.deactivate()
            await self.bot_repository.update(deactivated_bot)

            # Soft delete
            success = await self.bot_repository.delete(bot_id)

            if success:
                logger.info("Bot deleted successfully", bot_id=str(bot_id))
            return success

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during bot deletion",
                        bot_id=str(bot_id),
                        error=str(e))
            raise UseCaseError("delete_bot", str(e), e.error_code)
        except Exception as e:
            logger.error("Error deleting bot", bot_id=str(bot_id), error=str(e))
            raise UseCaseError("delete_bot", f"Failed to delete bot: {str(e)}")

    # === PRIVATE HELPER METHODS ===

    def _domain_to_dto(self, bot: Bot) -> BotDTO:
        """Convert Domain Bot to DTO"""
        return BotDTO(
            id=bot.id,
            name=bot.name,
            description=bot.description,
            bot_type=self._domain_to_dto_type(bot.bot_type),
            language=bot.language,
            core_ai_id=bot.core_ai_id,
            platform_id=bot.platform_id,
            config=self._domain_to_dto_config(bot.config),
            status=self._domain_to_dto_status(bot.status),
            active_conversations=bot.active_conversations,
            is_active=bot.is_active,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
            expiration_date=bot.expiration_date
        )

    def _dto_to_domain_config(self, config_dto: BotConfigDTO):
        """Convert DTO config to Domain config"""
        # This would import and use the actual Domain BotConfig
        from app.domain.value_objects.bot_config import BotConfig, AIProvider, PlatformType

        return BotConfig(
            ai_provider=AIProvider(config_dto.ai_provider),
            ai_model=config_dto.ai_model,
            ai_temperature=config_dto.ai_temperature,
            ai_max_tokens=config_dto.ai_max_tokens,
            platform_type=PlatformType(config_dto.platform_type),
            max_concurrent_users=config_dto.max_concurrent_users,
            max_conversation_length=config_dto.max_conversation_length,
            enable_sentiment_analysis=config_dto.enable_sentiment_analysis,
            enable_intent_recognition=config_dto.enable_intent_recognition,
            response_timeout_seconds=config_dto.response_timeout_seconds,
            supported_languages=config_dto.supported_languages
        )

    def _domain_to_dto_config(self, config) -> BotConfigDTO:
        """Convert Domain config to DTO config"""
        return BotConfigDTO(
            ai_provider=config.ai_provider.value,
            ai_model=config.ai_model,
            ai_temperature=config.ai_temperature,
            ai_max_tokens=config.ai_max_tokens,
            platform_type=config.platform_type.value,
            max_concurrent_users=config.max_concurrent_users,
            max_conversation_length=config.max_conversation_length,
            enable_sentiment_analysis=config.enable_sentiment_analysis,
            enable_intent_recognition=config.enable_intent_recognition,
            response_timeout_seconds=config.response_timeout_seconds,
            supported_languages=config.supported_languages
        )

    def _dto_to_domain_type(self, dto_type: BotTypeDTO):
        """Convert DTO type to Domain type"""
        from app.domain.entities.bot import BotType
        return BotType(dto_type.value)

    def _domain_to_dto_type(self, domain_type) -> BotTypeDTO:
        """Convert Domain type to DTO type"""
        return BotTypeDTO(domain_type.value)

    def _dto_to_domain_status(self, dto_status: BotStatusDTO):
        """Convert DTO status to Domain status"""
        from app.domain.entities.bot import BotStatus
        return BotStatus(dto_status.value)

    def _domain_to_dto_status(self, domain_status) -> BotStatusDTO:
        """Convert Domain status to DTO status"""
        return BotStatusDTO(domain_status.value)