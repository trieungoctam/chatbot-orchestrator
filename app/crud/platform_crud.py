"""
Platform CRUD Operations Module

This module provides comprehensive CRUD (Create, Read, Update, Delete) operations
for the Platform and PlatformAction models, which manage communication platform
configurations and their available actions in the chatbot orchestrator system.

The PlatformCRUD and PlatformActionCRUD classes handle:
- Basic CRUD operations (create, read, update, delete)
- Advanced querying (search, filtering by status)
- Bulk operations and statistics
- Soft delete functionality (activate/deactivate)
- Foreign key validation with dependent models

Dependencies:
- SQLAlchemy with async support for database operations
- Platform and PlatformAction models from app.models
- Bot model for dependency checking

Author: Generated for Chatbot System Microservice Architecture
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, or_
from sqlalchemy.orm import selectinload, joinedload
import uuid
import structlog

from app.models import Platform, PlatformAction, Bot
from app.schemas.request import (
    CreatePlatformRequest, UpdatePlatformRequest,
    CreatePlatformActionRequest, UpdatePlatformActionRequest
)
from app.schemas.response import (
    PlatformResponse, CreatePlatformResponse, UpdatePlatformResponse, PlatformListResponse,
    PlatformAction as PlatformActionSchema,  # Rename to avoid conflict
    PlatformActionResponse, CreatePlatformActionResponse, UpdatePlatformActionResponse, PlatformActionListResponse
)

logger = structlog.get_logger(__name__)


class PlatformCRUD:
    """
    CRUD operations for Platform model.

    This class provides a comprehensive interface for managing Platform configurations
    in the database. Each Platform represents a communication channel/service configuration
    with associated bots and actions.

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

    def _to_response(self, platform: Platform) -> PlatformResponse:
        """
        Convert Platform model to response schema.

        Args:
            platform (Platform): Platform model instance

        Returns:
            PlatformResponse: Converted response schema
        """
        # Convert actions if they are loaded - but don't try to access them if not loaded
        actions_response = []
        # Check if actions were eagerly loaded to avoid lazy loading issues
        if hasattr(platform, 'actions') and platform.actions is not None:
            for action in platform.actions:
                action_response = PlatformActionSchema(
                    id=str(action.id),
                    platform_id=str(action.platform_id),
                    platform_name=platform.name,  # Use the current platform's name
                    name=action.name,
                    description=action.description,
                    method=action.method,
                    path=action.path,
                    is_active=action.is_active,
                    meta_data=action.meta_data or {},
                )
                actions_response.append(action_response)

        return PlatformResponse(
            id=str(platform.id),
            name=platform.name,
            description=platform.description,
            base_url=platform.base_url,
            rate_limit_per_minute=platform.rate_limit_per_minute,
            auth_required=platform.auth_required,
            auth_token=platform.auth_token,
            is_active=platform.is_active,
            meta_data=platform.meta_data or {},
            created_at=platform.created_at.isoformat() if platform.created_at else None,
            updated_at=platform.updated_at.isoformat() if platform.updated_at else None,
            actions=actions_response
        )

    async def create(self, platform_data: CreatePlatformRequest) -> CreatePlatformResponse:
        """
        Create a new Platform configuration.

        Args:
            platform_data (CreatePlatformRequest): Request containing Platform fields and values

        Returns:
            CreatePlatformResponse: The newly created Platform instance wrapped in response schema

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            data = platform_data.model_dump()

            platform = Platform(**data)
            self.db.add(platform)
            await self.db.commit()
            # await self.db.refresh(platform, options=[selectinload(Platform.actions)])
            await self.db.refresh(platform)

            response_data = self._to_response(platform)

            logger.info("Platform created successfully", platform_id=str(platform.id))
            return CreatePlatformResponse(
                success=True,
                status="success",
                message="Platform created successfully",
                data=response_data
            )
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating Platform", error=str(e))
            raise

    async def get_by_id(self, platform_id: uuid.UUID) -> Optional[PlatformResponse]:
        """
        Get Platform by ID with eager loading of related data.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform

        Returns:
            Optional[PlatformResponse]: Platform response if found, None otherwise
        """
        try:
            stmt = select(Platform).options(selectinload(Platform.actions)).where(Platform.id == platform_id)
            result = await self.db.execute(stmt)
            platform = result.scalar_one_or_none()

            if platform:
                return self._to_response(platform)
            return None
        except Exception as e:
            logger.error("Error getting Platform by ID", platform_id=str(platform_id), error=str(e))
            raise

    async def get_by_id_with_actions(self, platform_id: uuid.UUID) -> Optional[PlatformResponse]:
        """
        Get Platform by ID with eager loading of related data.
        """
        try:
            stmt = select(Platform).where(Platform.id == platform_id).options(selectinload(Platform.actions))
            result = await self.db.execute(stmt)
            platform = result.scalar_one_or_none()
            if platform:
                return self._to_response(platform)
            return None
        except Exception as e:
            logger.error("Error getting Platform by ID with actions", platform_id=str(platform_id), error=str(e))
            raise

    async def get_by_name(self, name: str) -> Optional[PlatformResponse]:
        """
        Get Platform by name.

        Args:
            name (str): The name of the Platform configuration

        Returns:
            Optional[PlatformResponse]: Platform response if found, None otherwise
        """
        try:
            stmt = select(Platform).options(selectinload(Platform.actions)).where(Platform.name == name)
            result = await self.db.execute(stmt)
            platform = result.scalar_one_or_none()

            if platform:
                return self._to_response(platform)
            return None
        except Exception as e:
            logger.error("Error getting Platform by name", name=name, error=str(e))
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> PlatformListResponse:
        """
        Get all Platform configurations with pagination.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            PlatformListResponse: List of Platform instances wrapped in response schema
        """
        try:
            stmt = (
                select(Platform)
                .options(selectinload(Platform.actions))
                .order_by(Platform.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            platforms = result.scalars().all()

            platform_list = [self._to_response(platform) for platform in platforms]

            logger.info("Platform list retrieved", count=len(platform_list))
            return PlatformListResponse(
                success=True,
                status="success",
                message="Platform list retrieved successfully",
                data=platform_list
            )
        except Exception as e:
            logger.error("Error getting all Platforms", error=str(e))
            raise

    async def get_active(self, skip: int = 0, limit: int = 100) -> PlatformListResponse:
        """
        Get all active Platform configurations with pagination.

        Only returns Platform instances where is_active=True, useful for
        filtering out deactivated/disabled platform services.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            PlatformListResponse: List of active Platform instances wrapped in response schema
        """
        try:
            stmt = (
                select(Platform)
                .options(selectinload(Platform.actions))
                .where(Platform.is_active == True)
                .order_by(Platform.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            platforms = result.scalars().all()

            platform_list = [self._to_response(platform) for platform in platforms]

            logger.info("Active Platform list retrieved", count=len(platform_list))
            return PlatformListResponse(
                success=True,
                status="success",
                message="Active Platform list retrieved successfully",
                data=platform_list
            )
        except Exception as e:
            logger.error("Error getting active Platforms", error=str(e))
            raise

    async def update(self, platform_id: uuid.UUID, platform_data: UpdatePlatformRequest) -> Optional[UpdatePlatformResponse]:
        """
        Update Platform configuration with provided data.

        Automatically filters out protected fields (id, timestamps) to prevent
        accidental modification of system-managed fields.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform to update
            platform_data (UpdatePlatformRequest): Request containing fields to update

        Returns:
            Optional[UpdatePlatformResponse]: Updated Platform response if found, None otherwise
        """
        try:
            # Convert request to dict and remove None values
            update_data = {
                k: v for k, v in platform_data.model_dump(exclude_unset=True).items()
                if v is not None and k not in ['id', 'created_at', 'updated_at']
            }

            if not update_data:
                # No valid fields to update, return current data
                current_platform = await self.get_by_id(platform_id)
                if current_platform:
                    return UpdatePlatformResponse(
                        success=True,
                        status="success",
                        message="No changes to update",
                        data=current_platform
                    )
                return None

            stmt = (
                update(Platform)
                .where(Platform.id == platform_id)
                .values(**update_data)
                .returning(Platform)
            )
            result = await self.db.execute(stmt)
            updated_platform = result.scalar_one_or_none()

            if updated_platform:
                await self.db.commit()
                await self.db.refresh(updated_platform, options=[selectinload(Platform.actions)])

                response_data = self._to_response(updated_platform)

                logger.info("Platform updated successfully", platform_id=str(platform_id))
                return UpdatePlatformResponse(
                    success=True,
                    status="success",
                    message="Platform updated successfully",
                    data=response_data
                )
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating Platform", platform_id=str(platform_id), error=str(e))
            raise

    async def delete(self, platform_id: uuid.UUID) -> bool:
        """
        Hard delete Platform configuration from database.

        Checks for dependent bots before deletion to prevent orphaned records.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform to delete

        Returns:
            bool: True if record was deleted, False if not found

        Raises:
            ValueError: If Platform is being used by active bots
        """
        try:
            # Check if Platform is being used by bots
            bot_count_stmt = select(func.count(Bot.id)).where(Bot.platform_id == platform_id)
            bot_count_result = await self.db.execute(bot_count_stmt)
            bot_count = bot_count_result.scalar()

            if bot_count > 0:
                raise ValueError(f"Cannot delete Platform: it's being used by {bot_count} bot(s)")

            stmt = delete(Platform).where(Platform.id == platform_id)
            result = await self.db.execute(stmt)

            if result.rowcount > 0:
                await self.db.commit()
                logger.info("Platform deleted successfully", platform_id=str(platform_id))
                return True
            return False
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error deleting Platform", platform_id=str(platform_id), error=str(e))
            raise

    async def activate(self, platform_id: uuid.UUID) -> bool:
        """
        Reactivate a previously deactivated Platform configuration.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform to activate

        Returns:
            bool: True if successfully activated, False if not found
        """
        try:
            activate_request = UpdatePlatformRequest(is_active=True)
            result = await self.update(platform_id, activate_request)
            return result is not None
        except Exception as e:
            logger.error("Error activating Platform", platform_id=str(platform_id), error=str(e))
            raise

    async def deactivate(self, platform_id: uuid.UUID) -> bool:
        """
        Soft delete Platform configuration by setting is_active=False.

        Preferred over hard delete as it preserves data for audit trails
        and potential reactivation.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform to deactivate

        Returns:
            bool: True if successfully deactivated, False if not found
        """
        try:
            deactivate_request = UpdatePlatformRequest(is_active=False)
            result = await self.update(platform_id, deactivate_request)
            return result is not None
        except Exception as e:
            logger.error("Error deactivating Platform", platform_id=str(platform_id), error=str(e))
            raise

    async def search_by_url(self, url_pattern: str) -> PlatformListResponse:
        """
        Search Platform configurations by base URL pattern.

        Performs case-insensitive partial matching on the base_url field.
        Useful for finding platform services by their URL patterns.

        Args:
            url_pattern (str): Pattern to search for in base URLs

        Returns:
            PlatformListResponse: List of matching Platform instances wrapped in response schema
        """
        try:
            stmt = (
                select(Platform)
                .where(Platform.base_url.ilike(f"%{url_pattern}%"))
                .order_by(Platform.created_at.desc())
            )
            result = await self.db.execute(stmt)
            platforms = result.scalars().all()

            platform_list = [self._to_response(platform) for platform in platforms]

            logger.info("Platform search by URL completed", pattern=url_pattern, count=len(platform_list))
            return PlatformListResponse(
                success=True,
                status="success",
                message=f"Platform search by URL pattern '{url_pattern}' completed",
                data=platform_list
            )
        except Exception as e:
            logger.error("Error searching Platform by URL", pattern=url_pattern, error=str(e))
            raise

    async def search_by_name(self, name_pattern: str) -> PlatformListResponse:
        """
        Search Platform configurations by name pattern.

        Args:
            name_pattern (str): Pattern to search for in platform names

        Returns:
            PlatformListResponse: List of matching Platform instances wrapped in response schema
        """
        try:
            stmt = (
                select(Platform)
                .where(Platform.name.ilike(f"%{name_pattern}%"))
                .order_by(Platform.created_at.desc())
            )
            result = await self.db.execute(stmt)
            platforms = result.scalars().all()

            platform_list = [self._to_response(platform) for platform in platforms]

            logger.info("Platform search by name completed", pattern=name_pattern, count=len(platform_list))
            return PlatformListResponse(
                success=True,
                status="success",
                message=f"Platform search by name pattern '{name_pattern}' completed",
                data=platform_list
            )
        except Exception as e:
            logger.error("Error searching Platform by name", pattern=name_pattern, error=str(e))
            raise

    async def count_total(self) -> int:
        """
        Count total number of Platform configurations in the database.

        Returns:
            int: Total count of all Platform records
        """
        try:
            stmt = select(func.count(Platform.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting total Platforms", error=str(e))
            raise

    async def count_active(self) -> int:
        """
        Count total number of active Platform configurations.

        Returns:
            int: Count of active Platform records (is_active=True)
        """
        try:
            stmt = select(func.count(Platform.id)).where(Platform.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting active Platforms", error=str(e))
            raise

    async def get_usage_stats(self, platform_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get usage statistics for a specific Platform.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform

        Returns:
            Dict[str, Any]: Usage statistics including bot count and action count
        """
        try:
            # Count total bots using this Platform
            total_bots_stmt = select(func.count(Bot.id)).where(Bot.platform_id == platform_id)
            total_bots_result = await self.db.execute(total_bots_stmt)
            total_bots = total_bots_result.scalar() or 0

            # Count active bots using this Platform
            active_bots_stmt = select(func.count(Bot.id)).where(
                and_(Bot.platform_id == platform_id, Bot.is_active == True)
            )
            active_bots_result = await self.db.execute(active_bots_stmt)
            active_bots = active_bots_result.scalar() or 0

            # Count platform actions
            total_actions_stmt = select(func.count(PlatformAction.id)).where(
                PlatformAction.platform_id == platform_id
            )
            total_actions_result = await self.db.execute(total_actions_stmt)
            total_actions = total_actions_result.scalar() or 0

            # Count active platform actions
            active_actions_stmt = select(func.count(PlatformAction.id)).where(
                and_(PlatformAction.platform_id == platform_id, PlatformAction.is_active == True)
            )
            active_actions_result = await self.db.execute(active_actions_stmt)
            active_actions = active_actions_result.scalar() or 0

            return {
                "total_bots": total_bots,
                "active_bots": active_bots,
                "inactive_bots": total_bots - active_bots,
                "total_actions": total_actions,
                "active_actions": active_actions,
                "inactive_actions": total_actions - active_actions
            }
        except Exception as e:
            logger.error("Error getting Platform usage stats", platform_id=str(platform_id), error=str(e))
            raise

    async def get_popular_platforms(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular Platform configurations by bot count.

        Args:
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of Platform with their bot counts, ordered by popularity
        """
        try:
            stmt = (
                select(
                    Platform.id,
                    Platform.name,
                    Platform.base_url,
                    Platform.is_active,
                    func.count(Bot.id).label('bot_count')
                )
                .outerjoin(Bot, Platform.id == Bot.platform_id)
                .group_by(Platform.id)
                .order_by(func.count(Bot.id).desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                {
                    "platform_id": str(row.id),
                    "platform_name": row.name,
                    "base_url": row.base_url,
                    "is_active": row.is_active,
                    "bot_count": row.bot_count
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Error getting popular Platforms", error=str(e))
            raise


class PlatformActionCRUD:
    """
    CRUD operations for PlatformAction model.

    This class provides a comprehensive interface for managing PlatformAction configurations
    in the database. Each PlatformAction represents an available action/operation
    that can be performed on a platform.

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

    def _to_response(self, action: PlatformAction, platform_name: str = None) -> PlatformActionResponse:
        """
        Convert PlatformAction model to response schema.

        Args:
            action (PlatformAction): PlatformAction model instance
            platform_name (str, optional): Platform name to include in response

        Returns:
            PlatformActionResponse: Converted response schema
        """
        return PlatformActionResponse(
            id=str(action.id),
            platform_id=str(action.platform_id),
            platform_name=platform_name,
            name=action.name,
            description=action.description,
            method=action.method,
            path=action.path,
            is_active=action.is_active,
            meta_data=action.meta_data or {},
            created_at=action.created_at.isoformat() if action.created_at else None,
            updated_at=action.updated_at.isoformat() if action.updated_at else None
        )

    async def create(self, action_data: CreatePlatformActionRequest) -> CreatePlatformActionResponse:
        """
        Create a new PlatformAction configuration.

        Args:
            action_data (CreatePlatformActionRequest): Request containing PlatformAction fields

        Returns:
            CreatePlatformActionResponse: The newly created PlatformAction wrapped in response schema

        Raises:
            ValueError: If platform_id is invalid
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate platform exists
            platform = await self.db.get(Platform, uuid.UUID(action_data.platform_id))
            if not platform:
                raise ValueError("Invalid platform_id: Platform not found")

            data = action_data.model_dump()
            # Remove any fields that shouldn't be passed to SQLAlchemy
            data.pop('platform_name', None)  # Remove Pydantic-only field

            # Create new action with proper UUID fields
            action = PlatformAction(
                id=uuid.uuid4(),
                platform_id=uuid.UUID(data['platform_id']),
                name=data['name'],
                description=data.get('description'),
                method=data['method'],
                path=data['path'],
                is_active=data.get('is_active', True),
                meta_data=data.get('meta_data')
            )

            self.db.add(action)
            await self.db.commit()
            await self.db.refresh(action)

            response_data = self._to_response(action, platform.name)

            logger.info("PlatformAction created successfully", action_id=str(action.id))
            return CreatePlatformActionResponse(
                success=True,
                status="success",
                message="Platform Action created successfully",
                data=response_data
            )
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating PlatformAction", error=str(e))
            raise

    async def get_by_id(self, action_id: uuid.UUID) -> Optional[PlatformActionResponse]:
        """
        Get PlatformAction by ID with platform information.

        Args:
            action_id (uuid.UUID): The unique identifier of the PlatformAction

        Returns:
            Optional[PlatformActionResponse]: PlatformAction response if found, None otherwise
        """
        try:
            stmt = (
                select(PlatformAction, Platform.name)
                .join(Platform, PlatformAction.platform_id == Platform.id)
                .where(PlatformAction.id == action_id)
            )
            result = await self.db.execute(stmt)
            row = result.first()

            if row:
                action, platform_name = row
                return self._to_response(action, platform_name)
            return None
        except Exception as e:
            logger.error("Error getting PlatformAction by ID", action_id=str(action_id), error=str(e))
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> PlatformActionListResponse:
        """
        Get all PlatformAction configurations with pagination.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            PlatformActionListResponse: List of PlatformAction instances wrapped in response schema
        """
        try:
            stmt = (
                select(PlatformAction, Platform.name)
                .join(Platform, PlatformAction.platform_id == Platform.id)
                .order_by(PlatformAction.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            action_list = [self._to_response(action, platform_name) for action, platform_name in rows]

            logger.info("PlatformAction list retrieved", count=len(action_list))
            return PlatformActionListResponse(
                success=True,
                status="success",
                message="Platform Action list retrieved successfully",
                data=action_list
            )
        except Exception as e:
            logger.error("Error getting all PlatformActions", error=str(e))
            raise

    async def get_active(self, skip: int = 0, limit: int = 100) -> PlatformActionListResponse:
        """
        Get all active PlatformAction configurations.

        Args:
            skip (int): Number of records to skip (for pagination)
            limit (int): Maximum number of records to return

        Returns:
            PlatformActionListResponse: List of active PlatformAction instances wrapped in response schema
        """
        try:
            stmt = (
                select(PlatformAction, Platform.name)
                .join(Platform, PlatformAction.platform_id == Platform.id)
                .where(PlatformAction.is_active == True)
                .order_by(PlatformAction.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            action_list = [self._to_response(action, platform_name) for action, platform_name in rows]

            logger.info("Active PlatformAction list retrieved", count=len(action_list))
            return PlatformActionListResponse(
                success=True,
                status="success",
                message="Active Platform Action list retrieved successfully",
                data=action_list
            )
        except Exception as e:
            logger.error("Error getting active PlatformActions", error=str(e))
            raise

    async def get_by_platform(self, platform_id: uuid.UUID) -> PlatformActionListResponse:
        """
        Get all actions for a specific platform.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform

        Returns:
            PlatformActionListResponse: List of PlatformAction instances for the platform
        """
        try:
            stmt = (
                select(PlatformAction, Platform.name)
                .join(Platform, PlatformAction.platform_id == Platform.id)
                .where(PlatformAction.platform_id == platform_id)
                .order_by(PlatformAction.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            action_list = [self._to_response(action, platform_name) for action, platform_name in rows]

            logger.info("PlatformActions by platform retrieved", platform_id=str(platform_id), count=len(action_list))
            return PlatformActionListResponse(
                success=True,
                status="success",
                message=f"Platform Actions for platform '{platform_id}' retrieved successfully",
                data=action_list
            )
        except Exception as e:
            logger.error("Error getting PlatformActions by platform", platform_id=str(platform_id), error=str(e))
            raise

    async def get_by_type(self, method_type: str) -> PlatformActionListResponse:
        """
        Get PlatformActions by HTTP method type.

        Args:
            method_type (str): The HTTP method type to filter by (GET, POST, PUT, DELETE)

        Returns:
            PlatformActionListResponse: List of PlatformAction instances for the method type
        """
        try:
            stmt = (
                select(PlatformAction, Platform.name)
                .join(Platform, PlatformAction.platform_id == Platform.id)
                .where(PlatformAction.method == method_type)
                .order_by(PlatformAction.created_at.desc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            action_list = [self._to_response(action, platform_name) for action, platform_name in rows]

            logger.info("PlatformActions by method retrieved", method_type=method_type, count=len(action_list))
            return PlatformActionListResponse(
                success=True,
                status="success",
                message=f"Platform Actions with method '{method_type}' retrieved successfully",
                data=action_list
            )
        except Exception as e:
            logger.error("Error getting PlatformActions by method", method_type=method_type, error=str(e))
            raise

    async def update(self, action_id: uuid.UUID, action_data: UpdatePlatformActionRequest) -> Optional[UpdatePlatformActionResponse]:
        """
        Update PlatformAction configuration.

        Args:
            action_id (uuid.UUID): The unique identifier of the PlatformAction to update
            action_data (UpdatePlatformActionRequest): Request containing fields to update

        Returns:
            Optional[UpdatePlatformActionResponse]: Updated PlatformAction response if found, None otherwise
        """
        try:
            # Convert request to dict and remove None values
            update_data = {
                k: v for k, v in action_data.model_dump(exclude_unset=True).items()
                if v is not None and k not in ['id', 'created_at', 'updated_at']
            }

            # Validate platform if being updated
            if 'platform_id' in update_data:
                platform = await self.db.get(Platform, uuid.UUID(update_data["platform_id"]))
                if not platform:
                    raise ValueError("Invalid platform_id: Platform not found")
                # Convert string to UUID
                update_data['platform_id'] = uuid.UUID(update_data['platform_id'])

            if not update_data:
                # No valid fields to update, return current data
                current_action = await self.get_by_id(action_id)
                if current_action:
                    return UpdatePlatformActionResponse(
                        success=True,
                        status="success",
                        message="No changes to update",
                        data=current_action
                    )
                return None

            stmt = (
                update(PlatformAction)
                .where(PlatformAction.id == action_id)
                .values(**update_data)
                .returning(PlatformAction)
            )
            result = await self.db.execute(stmt)
            updated_action = result.scalar_one_or_none()

            if updated_action:
                await self.db.commit()
                await self.db.refresh(updated_action)

                # Get platform name for response
                platform = await self.db.get(Platform, updated_action.platform_id)
                platform_name = platform.name if platform else None

                response_data = self._to_response(updated_action, platform_name)

                logger.info("PlatformAction updated successfully", action_id=str(action_id))
                return UpdatePlatformActionResponse(
                    success=True,
                    status="success",
                    message="Platform Action updated successfully",
                    data=response_data
                )
            return None
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating PlatformAction", action_id=str(action_id), error=str(e))
            raise

    async def delete(self, action_id: uuid.UUID) -> bool:
        """
        Hard delete PlatformAction configuration from database.

        Args:
            action_id (uuid.UUID): The unique identifier of the PlatformAction to delete

        Returns:
            bool: True if record was deleted, False if not found

        Raises:
            ValueError: If PlatformAction is being used by bots
        """
        try:
            # Note: Check if action is being used by bots if needed
            # Currently no direct relationship, but this could be added in the future

            stmt = delete(PlatformAction).where(PlatformAction.id == action_id)
            result = await self.db.execute(stmt)

            if result.rowcount > 0:
                await self.db.commit()
                logger.info("PlatformAction deleted successfully", action_id=str(action_id))
                return True
            return False
        except Exception as e:
            await self.db.rollback()
            logger.error("Error deleting PlatformAction", action_id=str(action_id), error=str(e))
            raise

    async def activate(self, action_id: uuid.UUID) -> bool:
        """
        Reactivate a previously deactivated PlatformAction.

        Args:
            action_id (uuid.UUID): The unique identifier of the PlatformAction to activate

        Returns:
            bool: True if successfully activated, False if not found
        """
        try:
            activate_request = UpdatePlatformActionRequest(is_active=True)
            result = await self.update(action_id, activate_request)
            return result is not None
        except Exception as e:
            logger.error("Error activating PlatformAction", action_id=str(action_id), error=str(e))
            raise

    async def deactivate(self, action_id: uuid.UUID) -> bool:
        """
        Soft delete PlatformAction by setting is_active=False.

        Args:
            action_id (uuid.UUID): The unique identifier of the PlatformAction to deactivate

        Returns:
            bool: True if successfully deactivated, False if not found
        """
        try:
            deactivate_request = UpdatePlatformActionRequest(is_active=False)
            result = await self.update(action_id, deactivate_request)
            return result is not None
        except Exception as e:
            logger.error("Error deactivating PlatformAction", action_id=str(action_id), error=str(e))
            raise

    async def count_by_platform(self, platform_id: uuid.UUID) -> int:
        """
        Count actions for a specific platform.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform

        Returns:
            int: Count of actions for the platform
        """
        try:
            stmt = select(func.count(PlatformAction.id)).where(PlatformAction.platform_id == platform_id)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting PlatformActions by platform", platform_id=str(platform_id), error=str(e))
            raise

    async def count_active_by_platform(self, platform_id: uuid.UUID) -> int:
        """
        Count active actions for a specific platform.

        Args:
            platform_id (uuid.UUID): The unique identifier of the Platform

        Returns:
            int: Count of active actions for the platform
        """
        try:
            stmt = select(func.count(PlatformAction.id)).where(
                and_(PlatformAction.platform_id == platform_id, PlatformAction.is_active == True)
            )
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting active PlatformActions by platform", platform_id=str(platform_id), error=str(e))
            raise

    async def count_by_type(self, method_type: str) -> int:
        """
        Count actions by HTTP method type.

        Args:
            method_type (str): The HTTP method type to count

        Returns:
            int: Count of actions for the method type
        """
        try:
            stmt = select(func.count(PlatformAction.id)).where(PlatformAction.method == method_type)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error("Error counting PlatformActions by method", method_type=method_type, error=str(e))
            raise