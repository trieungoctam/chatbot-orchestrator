"""
SqlAlchemy Bot Repository Implementation
Concrete implementation of IBotRepository using SQLAlchemy
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
import structlog

from app.domain.entities.bot import Bot, BotType, BotStatus
from app.domain.value_objects.bot_config import BotConfig, AIProvider, PlatformType
from app.domain.repositories.bot_repository import IBotRepository
from app.domain.exceptions import EntityNotFoundError, RepositoryError

from app.infrastructure.database.models import (
    BotModel, CoreAIModel, PlatformModel,
    BotTypeEnum, BotStatusEnum, AIProviderEnum, PlatformTypeEnum
)
from app.infrastructure.database.session import get_db_session

logger = structlog.get_logger(__name__)


class SqlAlchemyBotRepository(IBotRepository):
    """SQLAlchemy implementation of Bot Repository"""

    async def create(self, bot: Bot) -> Bot:
        """Create new bot in database"""
        try:
            logger.info("Creating bot in database", name=bot.name)

            async with get_db_session() as db:
                # Convert domain entity to model
                bot_model = self._domain_to_model(bot)

                # Add to session
                db.session.add(bot_model)
                await db.commit()
                await db.refresh(bot_model)

                logger.info("Bot created successfully", bot_id=str(bot_model.id))
                return await self._model_to_domain(bot_model)

        except Exception as e:
            logger.error("Failed to create bot", error=str(e))
            raise RepositoryError(f"Failed to create bot: {str(e)}")

    async def get_by_id(self, bot_id: UUID) -> Optional[Bot]:
        """Get bot by ID"""
        try:
            async with get_db_session() as db:
                stmt = (
                    select(BotModel)
                    .options(
                        selectinload(BotModel.core_ai),
                        selectinload(BotModel.platform)
                    )
                    .where(BotModel.id == bot_id)
                )

                result = await db.execute(stmt)
                bot_model = result.scalar_one_or_none()

                if not bot_model:
                    return None

                return await self._model_to_domain(bot_model)

        except Exception as e:
            logger.error("Failed to get bot", bot_id=str(bot_id), error=str(e))
            raise RepositoryError(f"Failed to get bot: {str(e)}")

    async def get_by_name(self, name: str) -> Optional[Bot]:
        """Get bot by name"""
        try:
            async with get_db_session() as db:
                stmt = (
                    select(BotModel)
                    .options(
                        selectinload(BotModel.core_ai),
                        selectinload(BotModel.platform)
                    )
                    .where(BotModel.name == name)
                )

                result = await db.execute(stmt)
                bot_model = result.scalar_one_or_none()

                if not bot_model:
                    return None

                return await self._model_to_domain(bot_model)

        except Exception as e:
            logger.error("Failed to get bot by name", name=name, error=str(e))
            raise RepositoryError(f"Failed to get bot by name: {str(e)}")

    async def update(self, bot: Bot) -> Bot:
        """Update existing bot"""
        try:
            logger.info("Updating bot", bot_id=str(bot.id))

            async with get_db_session() as db:
                # Get existing bot
                existing_model = await db.scalar(
                    select(BotModel).where(BotModel.id == bot.id)
                )

                if not existing_model:
                    raise EntityNotFoundError("Bot", str(bot.id))

                # Update fields
                self._update_model_from_domain(existing_model, bot)

                await db.commit()
                await db.refresh(existing_model)

                logger.info("Bot updated successfully", bot_id=str(bot.id))
                return await self._model_to_domain(existing_model)

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update bot", bot_id=str(bot.id), error=str(e))
            raise RepositoryError(f"Failed to update bot: {str(e)}")

    async def delete(self, bot_id: UUID) -> bool:
        """Soft delete bot"""
        try:
            logger.info("Deleting bot", bot_id=str(bot_id))

            async with get_db_session() as db:
                # Soft delete by setting is_active to False
                stmt = (
                    update(BotModel)
                    .where(BotModel.id == bot_id)
                    .values(
                        is_active=False,
                        status=BotStatusEnum.INACTIVE,
                        updated_at=datetime.utcnow()
                    )
                )

                result = await db.execute(stmt)

                if result.rowcount == 0:
                    logger.warning("Bot not found for deletion", bot_id=str(bot_id))
                    return False

                await db.commit()
                logger.info("Bot deleted successfully", bot_id=str(bot_id))
                return True

        except Exception as e:
            logger.error("Failed to delete bot", bot_id=str(bot_id), error=str(e))
            raise RepositoryError(f"Failed to delete bot: {str(e)}")

    async def list_all(self, include_inactive: bool = False) -> List[Bot]:
        """List all bots"""
        try:
            async with get_db_session() as db:
                stmt = (
                    select(BotModel)
                    .options(
                        selectinload(BotModel.core_ai),
                        selectinload(BotModel.platform)
                    )
                )

                if not include_inactive:
                    stmt = stmt.where(BotModel.is_active == True)

                result = await db.execute(stmt)
                bot_models = result.scalars().all()

                bots = []
                for model in bot_models:
                    bot = await self._model_to_domain(model)
                    bots.append(bot)

                return bots

        except Exception as e:
            logger.error("Failed to list bots", error=str(e))
            raise RepositoryError(f"Failed to list bots: {str(e)}")

    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Bot], int]:
        """Search bots with filters and pagination"""
        try:
            logger.info("Searching bots", query=query, filters=filters)

            async with get_db_session() as db:
                # Base query
                stmt = (
                    select(BotModel)
                    .options(
                        selectinload(BotModel.core_ai),
                        selectinload(BotModel.platform)
                    )
                )

                # Count query
                count_stmt = select(func.count(BotModel.id))

                # Apply filters
                conditions = []

                if query:
                    search_condition = or_(
                        BotModel.name.ilike(f"%{query}%"),
                        BotModel.description.ilike(f"%{query}%")
                    )
                    conditions.append(search_condition)

                if filters:
                    if "bot_type" in filters:
                        conditions.append(BotModel.bot_type == self._domain_to_enum_type(filters["bot_type"]))

                    if "status" in filters:
                        conditions.append(BotModel.status == self._domain_to_enum_status(filters["status"]))

                    if "language" in filters:
                        conditions.append(BotModel.language == filters["language"])

                    if "platform_id" in filters:
                        conditions.append(BotModel.platform_id == filters["platform_id"])

                    if "is_active" in filters:
                        conditions.append(BotModel.is_active == filters["is_active"])

                if conditions:
                    stmt = stmt.where(and_(*conditions))
                    count_stmt = count_stmt.where(and_(*conditions))

                # Get total count
                total_count = await db.scalar(count_stmt)

                # Apply sorting
                if sort_order.lower() == "desc":
                    sort_column = getattr(BotModel, sort_by).desc()
                else:
                    sort_column = getattr(BotModel, sort_by)

                stmt = stmt.order_by(sort_column)

                # Apply pagination
                offset = (page - 1) * page_size
                stmt = stmt.offset(offset).limit(page_size)

                # Execute query
                result = await db.execute(stmt)
                bot_models = result.scalars().all()

                # Convert to domain entities
                bots = []
                for model in bot_models:
                    bot = await self._model_to_domain(model)
                    bots.append(bot)

                return bots, total_count

        except Exception as e:
            logger.error("Failed to search bots", error=str(e))
            raise RepositoryError(f"Failed to search bots: {str(e)}")

    async def get_statistics(self, bot_id: UUID) -> Optional[Dict[str, Any]]:
        """Get bot statistics"""
        try:
            async with get_db_session() as db:
                # Check if bot exists
                bot_exists = await db.scalar(
                    select(func.count(BotModel.id)).where(BotModel.id == bot_id)
                )

                if not bot_exists:
                    return None

                # Get bot with basic stats
                bot_model = await db.scalar(
                    select(BotModel).where(BotModel.id == bot_id)
                )

                # Calculate additional statistics
                from app.infrastructure.database.models import ConversationModel, MessageModel

                # Conversation statistics
                total_conversations = await db.scalar(
                    select(func.count(ConversationModel.id))
                    .where(ConversationModel.bot_id == bot_id)
                )

                active_conversations = await db.scalar(
                    select(func.count(ConversationModel.id))
                    .where(
                        and_(
                            ConversationModel.bot_id == bot_id,
                            ConversationModel.status.in_(["active", "paused"])
                        )
                    )
                )

                # Message statistics
                total_messages = await db.scalar(
                    select(func.count(MessageModel.id))
                    .join(ConversationModel)
                    .where(ConversationModel.bot_id == bot_id)
                )

                # Average response time
                avg_response_time = await db.scalar(
                    select(func.avg(MessageModel.processing_time_ms))
                    .join(ConversationModel)
                    .where(
                        and_(
                            ConversationModel.bot_id == bot_id,
                            MessageModel.role == "bot",
                            MessageModel.processing_time_ms.is_not(None)
                        )
                    )
                )

                # Success rate
                total_bot_messages = await db.scalar(
                    select(func.count(MessageModel.id))
                    .join(ConversationModel)
                    .where(
                        and_(
                            ConversationModel.bot_id == bot_id,
                            MessageModel.role == "bot"
                        )
                    )
                )

                successful_messages = await db.scalar(
                    select(func.count(MessageModel.id))
                    .join(ConversationModel)
                    .where(
                        and_(
                            ConversationModel.bot_id == bot_id,
                            MessageModel.role == "bot",
                            MessageModel.status == "sent"
                        )
                    )
                )

                success_rate = (successful_messages / total_bot_messages * 100) if total_bot_messages > 0 else 0

                return {
                    "bot_id": str(bot_id),
                    "total_conversations": total_conversations or 0,
                    "active_conversations": active_conversations or 0,
                    "total_messages": total_messages or 0,
                    "average_response_time_ms": float(avg_response_time) if avg_response_time else 0.0,
                    "success_rate": round(success_rate, 2),
                    "last_activity": bot_model.updated_at.isoformat() if bot_model.updated_at else None
                }

        except Exception as e:
            logger.error("Failed to get bot statistics", bot_id=str(bot_id), error=str(e))
            raise RepositoryError(f"Failed to get bot statistics: {str(e)}")

    # === PRIVATE HELPER METHODS ===

    def _domain_to_model(self, bot: Bot) -> BotModel:
        """Convert domain Bot to SQLAlchemy model"""
        return BotModel(
            id=bot.id,
            name=bot.name,
            description=bot.description,
            bot_type=self._domain_to_enum_type(bot.bot_type),
            language=bot.language,
            status=self._domain_to_enum_status(bot.status),
            core_ai_id=bot.core_ai_id,
            platform_id=bot.platform_id,
            config=self._config_to_dict(bot.config),
            active_conversations=bot.active_conversations,
            is_active=bot.is_active,
            expiration_date=bot.expiration_date,
            created_at=bot.created_at,
            updated_at=bot.updated_at
        )

    async def _model_to_domain(self, model: BotModel) -> Bot:
        """Convert SQLAlchemy model to domain Bot"""
        # Convert config dict to domain value object
        config = self._dict_to_config(model.config, model.core_ai, model.platform)

        return Bot(
            id=model.id,
            name=model.name,
            description=model.description,
            bot_type=BotType(model.bot_type.value),
            language=model.language,
            status=BotStatus(model.status.value),
            core_ai_id=model.core_ai_id,
            platform_id=model.platform_id,
            config=config,
            active_conversations=model.active_conversations,
            is_active=model.is_active,
            expiration_date=model.expiration_date,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _update_model_from_domain(self, model: BotModel, bot: Bot):
        """Update SQLAlchemy model from domain Bot"""
        model.name = bot.name
        model.description = bot.description
        model.bot_type = self._domain_to_enum_type(bot.bot_type)
        model.language = bot.language
        model.status = self._domain_to_enum_status(bot.status)
        model.core_ai_id = bot.core_ai_id
        model.platform_id = bot.platform_id
        model.config = self._config_to_dict(bot.config)
        model.active_conversations = bot.active_conversations
        model.is_active = bot.is_active
        model.expiration_date = bot.expiration_date
        model.updated_at = datetime.utcnow()

    def _config_to_dict(self, config: BotConfig) -> Dict[str, Any]:
        """Convert BotConfig to dict"""
        return {
            "ai_provider": config.ai_provider.value,
            "ai_model": config.ai_model,
            "ai_temperature": config.ai_temperature,
            "ai_max_tokens": config.ai_max_tokens,
            "platform_type": config.platform_type.value,
            "max_concurrent_users": config.max_concurrent_users,
            "max_conversation_length": config.max_conversation_length,
            "enable_sentiment_analysis": config.enable_sentiment_analysis,
            "enable_intent_recognition": config.enable_intent_recognition,
            "response_timeout_seconds": config.response_timeout_seconds,
            "supported_languages": config.supported_languages
        }

    def _dict_to_config(self, config_dict: Dict[str, Any], core_ai: CoreAIModel, platform: PlatformModel) -> BotConfig:
        """Convert dict to BotConfig"""
        return BotConfig(
            ai_provider=AIProvider(config_dict.get("ai_provider", core_ai.provider.value)),
            ai_model=config_dict.get("ai_model", core_ai.model_name),
            ai_temperature=config_dict.get("ai_temperature", core_ai.default_temperature),
            ai_max_tokens=config_dict.get("ai_max_tokens", core_ai.default_max_tokens),
            platform_type=PlatformType(config_dict.get("platform_type", platform.platform_type.value)),
            max_concurrent_users=config_dict.get("max_concurrent_users", 100),
            max_conversation_length=config_dict.get("max_conversation_length", 50),
            enable_sentiment_analysis=config_dict.get("enable_sentiment_analysis", True),
            enable_intent_recognition=config_dict.get("enable_intent_recognition", True),
            response_timeout_seconds=config_dict.get("response_timeout_seconds", 30),
            supported_languages=config_dict.get("supported_languages", ["en"])
        )

    def _domain_to_enum_type(self, bot_type: BotType) -> BotTypeEnum:
        """Convert domain BotType to enum"""
        return BotTypeEnum(bot_type.value)

    def _domain_to_enum_status(self, status: BotStatus) -> BotStatusEnum:
        """Convert domain BotStatus to enum"""
        return BotStatusEnum(status.value)