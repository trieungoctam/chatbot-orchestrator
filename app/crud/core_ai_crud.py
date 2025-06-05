"""
CoreAI CRUD Operations Module

This module provides comprehensive CRUD (Create, Read, Update, Delete) operations
for the CoreAI model, which manages AI service configurations in the chatbot
orchestrator system.

The CoreAICRUD class handles:
- Basic CRUD operations (create, read, update, delete)
- Advanced querying (search, filtering by status)
- Bulk operations and statistics
- Soft delete functionality (activate/deactivate)
- Foreign key validation with dependent models

Dependencies:
- SQLAlchemy with async support for database operations
- CoreAI model from app.models
- Bot model for dependency checking

Author: Generated for Chatbot System Microservice Architecture
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload
import uuid
import structlog

from app.models import CoreAI, Bot
from app.schemas.request import CreateCoreAIRequest, UpdateCoreAIRequest
from app.schemas.response import (
    CoreAIResponse, CoreAIListResponse, UpdateCoreAIResponse,
    CreateCoreAIResponse
)

logger = structlog.get_logger(__name__)


class CoreAICRUD:
    """
    CRUD operations for CoreAI model.

    This class provides a comprehensive interface for managing CoreAI configurations
    in the database. Each CoreAI represents an AI service configuration with
    associated bots and authentication settings.

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

    def _to_response(self, core_ai: CoreAI) -> CoreAIResponse:
        """
        Convert CoreAI model to response schema.

        Args:
            core_ai (CoreAI): CoreAI model instance

        Returns:
            CoreAIResponse: Converted response schema
        """
        return CoreAIResponse(
            id=str(core_ai.id),
            name=core_ai.name,
            api_endpoint=core_ai.api_endpoint,
            auth_required=core_ai.auth_required,
            auth_token=core_ai.auth_token,
            timeout_seconds=core_ai.timeout_seconds,
            is_active=core_ai.is_active,
            meta_data=core_ai.meta_data or {},
            created_at=core_ai.created_at.isoformat() if core_ai.created_at else None,
            updated_at=core_ai.updated_at.isoformat() if core_ai.updated_at else None
        )

    async def create(self, core_ai_data: CreateCoreAIRequest) -> CreateCoreAIResponse:
        """
        Create a new CoreAI configuration.

        Args:
            core_ai_data (CreateCoreAIRequest): Request containing CoreAI fields and values

        Returns:
            CreateCoreAIResponse: The newly created CoreAI instance wrapped in response schema

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            data = core_ai_data.model_dump()

            core_ai = CoreAI(**data)
            self.db.add(core_ai)
            await self.db.commit()
            await self.db.refresh(core_ai)

            response_data = self._to_response(core_ai)

            logger.info("CoreAI created successfully", core_ai_id=str(core_ai.id))
            return CreateCoreAIResponse(
                success=True,
                status="success",
                message="Core AI created successfully",
                data=response_data
            )
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating CoreAI", error=str(e))
            raise

    async def get_by_id(self, core_ai_id: uuid.UUID) -> Optional[CoreAIResponse]:
        """
        Get CoreAI by ID with eager loading of related bots.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI

        Returns:
            Optional[CoreAIResponse]: CoreAI response if found, None otherwise
        """
        try:
            stmt = select(CoreAI).options(selectinload(CoreAI.bots)).where(CoreAI.id == core_ai_id)
            result = await self.db.execute(stmt)
            core_ai = result.scalar_one_or_none()

            if core_ai:
                return self._to_response(core_ai)
            return None
        except Exception as e:
            logger.error("Error getting CoreAI by ID", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def get_by_name(self, name: str) -> Optional[CoreAIResponse]:
        """
        Get CoreAI by name with eager loading of related bots.

        Args:
            name (str): The name of the CoreAI configuration

        Returns:
            Optional[CoreAIResponse]: CoreAI response if found, None otherwise
        """
        try:
            stmt = select(CoreAI).options(selectinload(CoreAI.bots)).where(CoreAI.name == name)
            result = await self.db.execute(stmt)
            core_ai = result.scalar_one_or_none()

            if core_ai:
                return self._to_response(core_ai)
            return None
        except Exception as e:
            logger.error("Error getting CoreAI by name", name=name, error=str(e))
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> CoreAIListResponse:
        """
        Get all CoreAI configurations with pagination and eager loading.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            CoreAIListResponse: List of CoreAI instances wrapped in response schema
        """
        try:
            stmt = select(CoreAI).options(selectinload(CoreAI.bots)).offset(skip).limit(limit).order_by(CoreAI.created_at.desc())
            result = await self.db.execute(stmt)
            core_ais = result.scalars().all()

            core_ai_list = [self._to_response(core_ai) for core_ai in core_ais]

            logger.info("CoreAI list retrieved", count=len(core_ai_list))
            return CoreAIListResponse(
                success=True,
                status="success",
                message="Core AI list retrieved successfully",
                data=core_ai_list
            )
        except Exception as e:
            logger.error("Error getting all CoreAI", error=str(e))
            raise

    async def get_active(self, skip: int = 0, limit: int = 100) -> CoreAIListResponse:
        """
        Get all active CoreAI configurations with pagination.

        Only returns CoreAI instances where is_active=True, useful for
        filtering out deactivated/disabled AI services.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            CoreAIListResponse: List of active CoreAI instances wrapped in response schema
        """
        try:
            stmt = (
                select(CoreAI)
                .options(selectinload(CoreAI.bots))
                .where(CoreAI.is_active == True)
                .offset(skip)
                .limit(limit)
                .order_by(CoreAI.created_at.desc())
            )
            result = await self.db.execute(stmt)
            core_ais = result.scalars().all()

            core_ai_list = [self._to_response(core_ai) for core_ai in core_ais]

            logger.info("Active CoreAI list retrieved", count=len(core_ai_list))
            return CoreAIListResponse(
                success=True,
                status="success",
                message="Active Core AI list retrieved successfully",
                data=core_ai_list
            )
        except Exception as e:
            logger.error("Error getting active CoreAI", error=str(e))
            raise

    async def update(self, core_ai_id: uuid.UUID, core_ai_data: UpdateCoreAIRequest) -> Optional[UpdateCoreAIResponse]:
        """
        Update CoreAI configuration with provided data.

        Automatically filters out protected fields (id, timestamps) to prevent
        accidental modification of system-managed fields.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI to update
            core_ai_data (UpdateCoreAIRequest): Request containing fields to update

        Returns:
            Optional[UpdateCoreAIResponse]: Updated CoreAI response if found, None otherwise
        """
        try:
            # Convert request to dict and remove None values
            update_data = {
                k: v for k, v in core_ai_data.model_dump(exclude_unset=True).items()
                if v is not None and k not in ['id', 'created_at', 'updated_at']
            }

            if not update_data:
                # No valid fields to update, return current data
                current_ai = await self.get_by_id(core_ai_id)
                if current_ai:
                    return UpdateCoreAIResponse(
                        success=True,
                        status="success",
                        message="No changes to update",
                        data=current_ai
                    )
                return None

            stmt = (
                update(CoreAI)
                .where(CoreAI.id == core_ai_id)
                .values(**update_data)
                .returning(CoreAI)
            )
            result = await self.db.execute(stmt)
            updated_ai = result.scalar_one_or_none()

            if updated_ai:
                await self.db.commit()
                await self.db.refresh(updated_ai)

                response_data = self._to_response(updated_ai)

                logger.info("CoreAI updated successfully", core_ai_id=str(core_ai_id))
                return UpdateCoreAIResponse(
                    success=True,
                    status="success",
                    message="Core AI updated successfully",
                    data=response_data
                )
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating CoreAI", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def delete(self, core_ai_id: uuid.UUID) -> bool:
        """
        Hard delete CoreAI configuration from database.

        Checks for dependent bots before deletion to prevent orphaned records.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI to delete

        Returns:
            bool: True if record was deleted, False if not found

        Raises:
            ValueError: If CoreAI is being used by active bots
        """
        try:
            # Check if CoreAI is being used by bots
            bot_count_stmt = select(func.count(Bot.id)).where(Bot.core_ai_id == core_ai_id)
            bot_count_result = await self.db.execute(bot_count_stmt)
            bot_count = bot_count_result.scalar()

            if bot_count > 0:
                raise ValueError(f"Cannot delete Core AI: it's being used by {bot_count} bot(s)")

            stmt = delete(CoreAI).where(CoreAI.id == core_ai_id)
            result = await self.db.execute(stmt)

            if result.rowcount > 0:
                await self.db.commit()
                logger.info("CoreAI deleted successfully", core_ai_id=str(core_ai_id))
                return True
            return False
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error deleting CoreAI", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def activate(self, core_ai_id: uuid.UUID) -> bool:
        """
        Reactivate a previously deactivated CoreAI configuration.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI to activate

        Returns:
            bool: True if successfully activated, False if not found
        """
        try:
            activate_request = UpdateCoreAIRequest(is_active=True)
            result = await self.update(core_ai_id, activate_request)
            return result is not None
        except Exception as e:
            logger.error("Error activating CoreAI", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def deactivate(self, core_ai_id: uuid.UUID) -> bool:
        """
        Soft delete CoreAI configuration by setting is_active=False.

        Preferred over hard delete as it preserves data for audit trails
        and potential reactivation.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI to deactivate

        Returns:
            bool: True if successfully deactivated, False if not found
        """
        try:
            deactivate_request = UpdateCoreAIRequest(is_active=False)
            result = await self.update(core_ai_id, deactivate_request)
            return result is not None
        except Exception as e:
            logger.error("Error deactivating CoreAI", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def search_by_endpoint(self, endpoint_pattern: str) -> CoreAIListResponse:
        """
        Search CoreAI configurations by API endpoint pattern.

        Performs case-insensitive partial matching on the api_endpoint field.
        Useful for finding AI services by their API URL patterns.

        Args:
            endpoint_pattern (str): Pattern to search for in API endpoints

        Returns:
            CoreAIListResponse: List of matching CoreAI instances wrapped in response schema
        """
        try:
            stmt = (
                select(CoreAI)
                .options(selectinload(CoreAI.bots))
                .where(CoreAI.api_endpoint.ilike(f"%{endpoint_pattern}%"))
                .order_by(CoreAI.created_at.desc())
            )
            result = await self.db.execute(stmt)
            core_ais = result.scalars().all()

            core_ai_list = [self._to_response(core_ai) for core_ai in core_ais]

            logger.info("CoreAI search by endpoint completed", pattern=endpoint_pattern, count=len(core_ai_list))
            return CoreAIListResponse(
                success=True,
                status="success",
                message=f"Core AI search by endpoint pattern '{endpoint_pattern}' completed",
                data=core_ai_list
            )
        except Exception as e:
            logger.error("Error searching CoreAI by endpoint", pattern=endpoint_pattern, error=str(e))
            raise

    async def count_total(self) -> int:
        """
        Count total number of CoreAI configurations in the database.

        Returns:
            int: Total count of all CoreAI records
        """
        try:
            stmt = select(func.count(CoreAI.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting total CoreAI", error=str(e))
            raise

    async def count_active(self) -> int:
        """
        Count total number of active CoreAI configurations.

        Returns:
            int: Count of active CoreAI records (is_active=True)
        """
        try:
            stmt = select(func.count(CoreAI.id)).where(CoreAI.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting active CoreAI", error=str(e))
            raise

    async def get_usage_stats(self, core_ai_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get usage statistics for a specific CoreAI.

        Args:
            core_ai_id (uuid.UUID): The unique identifier of the CoreAI

        Returns:
            Dict[str, Any]: Usage statistics including bot count and active bot count
        """
        try:
            # Count total bots using this CoreAI
            total_bots_stmt = select(func.count(Bot.id)).where(Bot.core_ai_id == core_ai_id)
            total_bots_result = await self.db.execute(total_bots_stmt)
            total_bots = total_bots_result.scalar() or 0

            # Count active bots using this CoreAI
            active_bots_stmt = select(func.count(Bot.id)).where(
                and_(Bot.core_ai_id == core_ai_id, Bot.is_active == True)
            )
            active_bots_result = await self.db.execute(active_bots_stmt)
            active_bots = active_bots_result.scalar() or 0

            return {
                "total_bots": total_bots,
                "active_bots": active_bots,
                "inactive_bots": total_bots - active_bots
            }
        except Exception as e:
            logger.error("Error getting CoreAI usage stats", core_ai_id=str(core_ai_id), error=str(e))
            raise

    async def get_popular_core_ais(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular CoreAI configurations by bot count.

        Args:
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of CoreAI with their bot counts, ordered by popularity
        """
        try:
            stmt = (
                select(
                    CoreAI.id,
                    CoreAI.name,
                    CoreAI.api_endpoint,
                    CoreAI.is_active,
                    func.count(Bot.id).label('bot_count')
                )
                .outerjoin(Bot, CoreAI.id == Bot.core_ai_id)
                .group_by(CoreAI.id)
                .order_by(func.count(Bot.id).desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "core_ai_id": str(row.id),
                    "core_ai_name": row.name,
                    "api_endpoint": row.api_endpoint,
                    "is_active": row.is_active,
                    "bot_count": row.bot_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting popular CoreAI", error=str(e))
            raise
