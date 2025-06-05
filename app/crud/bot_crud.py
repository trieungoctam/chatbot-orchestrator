"""
Bot CRUD Operations Module

This module provides comprehensive CRUD (Create, Read, Update, Delete) operations
for the Bot model, which manages bot configurations in the chatbot
orchestrator system.

The BotCRUD class handles:
- Basic CRUD operations (create, read, update, delete)
- Advanced querying (search, filtering by status, core_ai, platform)
- Bulk operations and statistics
- Soft delete functionality (activate/deactivate)
- Foreign key validation with dependent models

Dependencies:
- SQLAlchemy with async support for database operations
- Bot, CoreAI, Platform models from app.models
- Conversation model for dependency checking

Author: Generated for Chatbot System Microservice Architecture
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
import uuid
import structlog

from app.models import Bot, CoreAI, Platform, Conversation
from app.schemas.request import CreateBotRequest, UpdateBotRequest
from app.schemas.response import (
    BotResponse, CreateBotResponse, UpdateBotResponse, BotListResponse
)

logger = structlog.get_logger(__name__)


class BotCRUD:
    """
    CRUD operations for Bot model.

    This class provides a comprehensive interface for managing Bot configurations
    in the database. Each Bot represents a chatbot instance with
    associated CoreAI and Platform configurations.

    Attributes:
        db (AsyncSession): Async SQLAlchemy database session
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize CRUD operations with database session.

        Args:
            db (AsyncSession): Async SQLAlchemy database session
        """
        self.db = db

    def _to_response(self, bot: Bot, core_ai_name: str = None, platform_name: str = None) -> BotResponse:
        """
        Convert Bot model to response schema.

        Args:
            bot (Bot): Bot model instance
            core_ai_name (str, optional): CoreAI name to include in response
            platform_name (str, optional): Platform name to include in response

        Returns:
            BotResponse: Converted response schema
        """
        return BotResponse(
            id=str(bot.id),
            name=bot.name,
            description=bot.description,
            core_ai_id=str(bot.core_ai_id),
            core_ai_name=core_ai_name,
            platform_id=str(bot.platform_id),
            platform_name=platform_name,
            language=bot.language,
            is_active=bot.is_active,
            meta_data=bot.meta_data or {},
            created_at=bot.created_at.isoformat() if bot.created_at else None,
            updated_at=bot.updated_at.isoformat() if bot.updated_at else None
        )

    async def create(self, bot_data: CreateBotRequest) -> CreateBotResponse:
        """
        Create a new Bot configuration.

        Args:
            bot_data (CreateBotRequest): Request containing Bot fields and values

        Returns:
            CreateBotResponse: The newly created Bot instance wrapped in response schema

        Raises:
            ValueError: If CoreAI or Platform is invalid or inactive
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate required foreign keys exist and are active
            core_ai = await self.db.get(CoreAI, uuid.UUID(bot_data.core_ai_id))
            if not core_ai or not core_ai.is_active:
                raise ValueError("Invalid or inactive core_ai_id")

            platform = await self.db.get(Platform, uuid.UUID(bot_data.platform_id))
            if not platform or not platform.is_active:
                raise ValueError("Invalid or inactive platform_id")

            data = bot_data.model_dump()
            # Convert string IDs to UUIDs
            data['core_ai_id'] = uuid.UUID(data['core_ai_id'])
            data['platform_id'] = uuid.UUID(data['platform_id'])

            bot = Bot(**data)
            self.db.add(bot)
            await self.db.commit()
            await self.db.refresh(bot)

            response_data = self._to_response(bot, core_ai.name, platform.name)

            logger.info("Bot created successfully", bot_id=str(bot.id))
            return CreateBotResponse(
                success=True,
                status="success",
                message="Bot created successfully",
                data=response_data
            )
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating Bot", error=str(e))
            raise

    async def get_by_id(self, bot_id: uuid.UUID) -> Optional[BotResponse]:
        """
        Get Bot by ID with eager loading of related entities.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot

        Returns:
            Optional[BotResponse]: Bot response if found, None otherwise
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.id == bot_id)
            )
            result = await self.db.execute(stmt)
            row = result.first()

            if row:
                bot, core_ai_name, platform_name = row
                return self._to_response(bot, core_ai_name, platform_name)
            return None
        except Exception as e:
            logger.error("Error getting Bot by ID", bot_id=str(bot_id), error=str(e))
            raise

    async def get_by_name(self, name: str) -> Optional[BotResponse]:
        """
        Get Bot by name with eager loading of related entities.

        Args:
            name (str): The name of the Bot

        Returns:
            Optional[BotResponse]: Bot response if found, None otherwise
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.name == name)
            )
            result = await self.db.execute(stmt)
            row = result.first()

            if row:
                bot, core_ai_name, platform_name = row
                return self._to_response(bot, core_ai_name, platform_name)
            return None
        except Exception as e:
            logger.error("Error getting Bot by name", name=name, error=str(e))
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> BotListResponse:
        """
        Get all Bot configurations with pagination and eager loading.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            BotListResponse: List of Bot instances wrapped in response schema
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .order_by(Bot.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Bot list retrieved", count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message="Bot list retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting all Bots", error=str(e))
            raise

    async def get_active(self, skip: int = 0, limit: int = 100) -> BotListResponse:
        """
        Get all active Bot configurations with pagination.

        Only returns Bot instances where is_active=True, useful for
        filtering out deactivated/disabled bots.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            BotListResponse: List of active Bot instances wrapped in response schema
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.is_active == True)
                .order_by(Bot.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Active Bot list retrieved", count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message="Active Bot list retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting active Bots", error=str(e))
            raise

    async def get_by_core_ai(self, core_ai_id: uuid.UUID) -> BotListResponse:
        """
        Get all Bots using a specific CoreAI.

        Args:
            core_ai_id (uuid.UUID): The CoreAI identifier

        Returns:
            BotListResponse: List of Bot instances using the specified CoreAI
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.core_ai_id == core_ai_id)
                .order_by(Bot.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Bots by CoreAI retrieved", core_ai_id=str(core_ai_id), count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message=f"Bots for CoreAI '{core_ai_id}' retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting Bots by CoreAI", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def get_by_platform(self, platform_id: uuid.UUID) -> BotListResponse:
        """
        Get all Bots using a specific Platform.

        Args:
            platform_id (uuid.UUID): The Platform identifier

        Returns:
            BotListResponse: List of Bot instances using the specified Platform
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.platform_id == platform_id)
                .order_by(Bot.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Bots by Platform retrieved", platform_id=str(platform_id), count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message=f"Bots for Platform '{platform_id}' retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting Bots by Platform", platform_id=str(platform_id), error=str(e))
            raise

    async def get_by_language(self, language: str) -> BotListResponse:
        """
        Get Bots by language.

        Args:
            language (str): The language code (e.g., 'vi', 'en')

        Returns:
            BotListResponse: List of Bot instances with the specified language
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.language == language)
                .order_by(Bot.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Bots by language retrieved", language=language, count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message=f"Bots with language '{language}' retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting Bots by language", language=language, error=str(e))
            raise

    async def get_ready_bots(self, skip: int = 0, limit: int = 100) -> BotListResponse:
        """
        Get Bots that are active and have both active CoreAI and Platform.

        Returns:
            BotListResponse: List of fully operational Bot instances
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(and_(
                    Bot.is_active == True,
                    CoreAI.is_active == True,
                    Platform.is_active == True
                ))
                .order_by(Bot.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Ready Bots retrieved", count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message="Ready Bots retrieved successfully",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error getting ready Bots", error=str(e))
            raise

    async def update(self, bot_id: uuid.UUID, bot_data: UpdateBotRequest) -> Optional[UpdateBotResponse]:
        """
        Update Bot configuration with provided data.

        Automatically filters out protected fields (id, timestamps) to prevent
        accidental modification of system-managed fields.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot to update
            bot_data (UpdateBotRequest): Request containing fields to update

        Returns:
            Optional[UpdateBotResponse]: Updated Bot response if found, None otherwise

        Raises:
            ValueError: If CoreAI or Platform is invalid or inactive
        """
        try:
            # Convert request to dict and remove None values
            update_data = {
                k: v for k, v in bot_data.model_dump(exclude_unset=True).items()
                if v is not None and k not in ['id', 'created_at', 'updated_at']
            }

            # Validate foreign keys if they're being updated
            if 'core_ai_id' in update_data:
                core_ai = await self.db.get(CoreAI, uuid.UUID(update_data["core_ai_id"]))
                if not core_ai or not core_ai.is_active:
                    raise ValueError("Invalid or inactive core_ai_id")
                update_data['core_ai_id'] = uuid.UUID(update_data['core_ai_id'])

            if 'platform_id' in update_data:
                platform = await self.db.get(Platform, uuid.UUID(update_data["platform_id"]))
                if not platform or not platform.is_active:
                    raise ValueError("Invalid or inactive platform_id")
                update_data['platform_id'] = uuid.UUID(update_data['platform_id'])

            if not update_data:
                # No valid fields to update, return current data
                current_bot = await self.get_by_id(bot_id)
                if current_bot:
                    return UpdateBotResponse(
                        success=True,
                        status="success",
                        message="No changes to update",
                        data=current_bot
                    )
                return None

            stmt = (
                update(Bot)
                .where(Bot.id == bot_id)
                .values(**update_data)
                .returning(Bot)
            )
            result = await self.db.execute(stmt)
            updated_bot = result.scalar_one_or_none()

            if updated_bot:
                await self.db.commit()
                await self.db.refresh(updated_bot)

                # Get related entity names for response
                core_ai = await self.db.get(CoreAI, updated_bot.core_ai_id)
                platform = await self.db.get(Platform, updated_bot.platform_id)

                response_data = self._to_response(
                    updated_bot,
                    core_ai.name if core_ai else None,
                    platform.name if platform else None
                )

                logger.info("Bot updated successfully", bot_id=str(bot_id))
                return UpdateBotResponse(
                    success=True,
                    status="success",
                    message="Bot updated successfully",
                    data=response_data
                )
            return None
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating Bot", bot_id=str(bot_id), error=str(e))
            raise

    async def delete(self, bot_id: uuid.UUID) -> bool:
        """
        Hard delete Bot configuration from database.

        Checks for dependent conversations before deletion to prevent orphaned records.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot to delete

        Returns:
            bool: True if record was deleted, False if not found

        Raises:
            ValueError: If bot is being used in conversations
        """
        try:
            # Check if bot is being used in conversations
            conv_count_stmt = select(func.count(Conversation.id)).where(Conversation.bot_id == bot_id)
            conv_count_result = await self.db.execute(conv_count_stmt)
            conv_count = conv_count_result.scalar()

            if conv_count > 0:
                raise ValueError(f"Cannot delete Bot: it's being used in {conv_count} conversation(s)")

            stmt = delete(Bot).where(Bot.id == bot_id)
            result = await self.db.execute(stmt)

            if result.rowcount > 0:
                await self.db.commit()
                logger.info("Bot deleted successfully", bot_id=str(bot_id))
                return True
            return False
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error deleting Bot", bot_id=str(bot_id), error=str(e))
            raise

    async def activate(self, bot_id: uuid.UUID) -> bool:
        """
        Reactivate a previously deactivated Bot configuration.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot to activate

        Returns:
            bool: True if successfully activated, False if not found
        """
        try:
            activate_request = UpdateBotRequest(is_active=True)
            result = await self.update(bot_id, activate_request)
            return result is not None
        except Exception as e:
            logger.error("Error activating Bot", bot_id=str(bot_id), error=str(e))
            raise

    async def deactivate(self, bot_id: uuid.UUID) -> bool:
        """
        Soft delete Bot configuration by setting is_active=False.

        Preferred over hard delete as it preserves data for audit trails
        and potential reactivation.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot to deactivate

        Returns:
            bool: True if successfully deactivated, False if not found
        """
        try:
            deactivate_request = UpdateBotRequest(is_active=False)
            result = await self.update(bot_id, deactivate_request)
            return result is not None
        except Exception as e:
            logger.error("Error deactivating Bot", bot_id=str(bot_id), error=str(e))
            raise

    async def search_by_name(self, name_pattern: str) -> BotListResponse:
        """
        Search Bot configurations by name pattern.

        Performs case-insensitive partial matching on the name field.
        Useful for finding bots by name fragments.

        Args:
            name_pattern (str): Pattern to search for in Bot names

        Returns:
            BotListResponse: List of matching Bot instances wrapped in response schema
        """
        try:
            stmt = (
                select(Bot, CoreAI.name, Platform.name)
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(Bot.name.ilike(f"%{name_pattern}%"))
                .order_by(Bot.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            bot_list = [self._to_response(bot, core_ai_name, platform_name)
                       for bot, core_ai_name, platform_name in rows]

            logger.info("Bot search by name completed", pattern=name_pattern, count=len(bot_list))
            return BotListResponse(
                success=True,
                status="success",
                message=f"Bot search by name pattern '{name_pattern}' completed",
                data=bot_list
            )
        except Exception as e:
            logger.error("Error searching Bots by name", pattern=name_pattern, error=str(e))
            raise

    async def count_total(self) -> int:
        """
        Count total number of Bot configurations in the database.

        Returns:
            int: Total count of all Bot records
        """
        try:
            stmt = select(func.count(Bot.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting total Bots", error=str(e))
            raise

    async def count_active(self) -> int:
        """
        Count total number of active Bot configurations.

        Returns:
            int: Count of active Bot records (is_active=True)
        """
        try:
            stmt = select(func.count(Bot.id)).where(Bot.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting active Bots", error=str(e))
            raise

    async def count_ready(self) -> int:
        """
        Count Bots that are ready (active with active CoreAI and Platform).

        Returns:
            int: Count of ready Bot records
        """
        try:
            stmt = (
                select(func.count(Bot.id))
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .where(and_(
                    Bot.is_active == True,
                    CoreAI.is_active == True,
                    Platform.is_active == True
                ))
            )
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting ready Bots", error=str(e))
            raise

    async def count_conversations(self, bot_id: uuid.UUID) -> int:
        """
        Count conversations for a specific Bot.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot

        Returns:
            int: Count of conversations for the bot
        """
        try:
            stmt = select(func.count(Conversation.id)).where(Conversation.bot_id == bot_id)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting Bot conversations", bot_id=str(bot_id), error=str(e))
            raise

    async def get_stats_by_core_ai(self) -> List[Dict[str, Any]]:
        """
        Get Bot statistics grouped by CoreAI.

        Returns:
            List[Dict[str, Any]]: List of CoreAI with their bot counts
        """
        try:
            stmt = (
                select(
                    CoreAI.id,
                    CoreAI.name,
                    CoreAI.is_active,
                    func.count(Bot.id).label('bot_count'),
                    func.count(
                        func.case((Bot.is_active == True, Bot.id))
                    ).label('active_bot_count')
                )
                .outerjoin(Bot, CoreAI.id == Bot.core_ai_id)
                .group_by(CoreAI.id)
                .order_by(func.count(Bot.id).desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "core_ai_id": str(row.id),
                    "core_ai_name": row.name,
                    "core_ai_active": row.is_active,
                    "total_bots": row.bot_count,
                    "active_bots": row.active_bot_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting Bot stats by CoreAI", error=str(e))
            raise

    async def get_stats_by_platform(self) -> List[Dict[str, Any]]:
        """
        Get Bot statistics grouped by Platform.

        Returns:
            List[Dict[str, Any]]: List of Platform with their bot counts
        """
        try:
            stmt = (
                select(
                    Platform.id,
                    Platform.name,
                    Platform.is_active,
                    func.count(Bot.id).label('bot_count'),
                    func.count(
                        func.case((Bot.is_active == True, Bot.id))
                    ).label('active_bot_count')
                )
                .outerjoin(Bot, Platform.id == Bot.platform_id)
                .group_by(Platform.id)
                .order_by(func.count(Bot.id).desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "platform_id": str(row.id),
                    "platform_name": row.name,
                    "platform_active": row.is_active,
                    "total_bots": row.bot_count,
                    "active_bots": row.active_bot_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting Bot stats by Platform", error=str(e))
            raise

    async def get_stats_by_language(self) -> List[Dict[str, Any]]:
        """
        Get Bot statistics grouped by language.

        Returns:
            List[Dict[str, Any]]: List of languages with their bot counts
        """
        try:
            stmt = (
                select(
                    Bot.language,
                    func.count(Bot.id).label('bot_count'),
                    func.count(
                        func.case((Bot.is_active == True, Bot.id))
                    ).label('active_bot_count')
                )
                .group_by(Bot.language)
                .order_by(func.count(Bot.id).desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "language": row.language,
                    "total_bots": row.bot_count,
                    "active_bots": row.active_bot_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting Bot stats by language", error=str(e))
            raise

    async def get_usage_stats(self, bot_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get usage statistics for a specific Bot.

        Args:
            bot_id (uuid.UUID): The unique identifier of the Bot

        Returns:
            Dict[str, Any]: Usage statistics including conversation counts
        """
        try:
            # Count total conversations
            total_conv_stmt = select(func.count(Conversation.id)).where(Conversation.bot_id == bot_id)
            total_conv_result = await self.db.execute(total_conv_stmt)
            total_conversations = total_conv_result.scalar() or 0

            # Count active conversations
            active_conv_stmt = select(func.count(Conversation.id)).where(
                and_(Conversation.bot_id == bot_id, Conversation.status == "active")
            )
            active_conv_result = await self.db.execute(active_conv_stmt)
            active_conversations = active_conv_result.scalar() or 0

            # Count completed conversations
            completed_conv_stmt = select(func.count(Conversation.id)).where(
                and_(Conversation.bot_id == bot_id, Conversation.status == "ended")
            )
            completed_conv_result = await self.db.execute(completed_conv_stmt)
            completed_conversations = completed_conv_result.scalar() or 0

            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "completed_conversations": completed_conversations,
                "other_conversations": total_conversations - active_conversations - completed_conversations
            }
        except Exception as e:
            logger.error("Error getting Bot usage stats", bot_id=str(bot_id), error=str(e))
            raise

    async def get_popular_bots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular Bot configurations by conversation count.

        Args:
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of Bot with their conversation counts, ordered by popularity
        """
        try:
            stmt = (
                select(
                    Bot.id,
                    Bot.name,
                    Bot.language,
                    Bot.is_active,
                    CoreAI.name.label('core_ai_name'),
                    Platform.name.label('platform_name'),
                    func.count(Conversation.id).label('conversation_count')
                )
                .join(CoreAI, Bot.core_ai_id == CoreAI.id)
                .join(Platform, Bot.platform_id == Platform.id)
                .outerjoin(Conversation, Bot.id == Conversation.bot_id)
                .group_by(Bot.id, CoreAI.name, Platform.name)
                .order_by(func.count(Conversation.id).desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "bot_id": str(row.id),
                    "bot_name": row.name,
                    "language": row.language,
                    "is_active": row.is_active,
                    "core_ai_name": row.core_ai_name,
                    "platform_name": row.platform_name,
                    "conversation_count": row.conversation_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting popular Bots", error=str(e))
            raise
