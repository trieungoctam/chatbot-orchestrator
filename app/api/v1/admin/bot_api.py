"""
Bot Admin API Endpoints

This module provides FastAPI endpoints for managing Bot configurations
in the chatbot orchestrator system. All endpoints require admin
authentication and provide comprehensive CRUD operations with advanced features.

Features:
- Full CRUD operations (Create, Read, Update, Delete)
- Activation/Deactivation (soft delete)
- Search and filtering capabilities
- Statistics and analytics
- Usage monitoring
- Comprehensive error handling and logging

Dependencies:
- FastAPI for API framework
- BotCRUD for database operations
- Admin authentication for security

Author: Generated for Chatbot System Microservice Architecture
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
import structlog

from app.core.database import async_session_factory
from app.crud.bot_crud import BotCRUD
from app.crud.core_ai_crud import CoreAICRUD
from app.crud.platform_crud import PlatformCRUD
from app.schemas.request import CreateBotRequest, UpdateBotRequest
from app.schemas.response import BotResponse, CreateBotResponse, UpdateBotResponse, BotListResponse
from app.api.dependencies import verify_admin_token

logger = structlog.get_logger(__name__)

# Admin router with authentication requirement
router = APIRouter(prefix="/bot")


def _validate_uuid(uuid_str: str, param_name: str) -> uuid.UUID:
    """
    Validate and convert UUID string.

    Args:
        uuid_str (str): UUID string to validate
        param_name (str): Parameter name for error message

    Returns:
        uuid.UUID: Validated UUID object

    Raises:
        HTTPException: If UUID format is invalid
    """
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format"
        )


@router.post("/", dependencies=[Depends(verify_admin_token)], response_model=CreateBotResponse)
async def create_bot(request: CreateBotRequest):
    """
    Create a new Bot configuration.

    Creates a new chatbot configuration with the provided parameters.
    Validates that the specified CoreAI and Platform exist and are active.
    Ensures bot name uniqueness.

    Args:
        request (CreateBotRequest): Bot configuration data

    Returns:
        CreateBotResponse: Created Bot with success status

    Raises:
        HTTPException: 400 if validation fails, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            core_ai_crud = CoreAICRUD(session)
            platform_crud = PlatformCRUD(session)

            # Check if name already exists
            existing = await bot_crud.get_by_name(request.name)
            if existing:
                logger.warning("Bot creation failed - name exists", name=request.name)
                raise HTTPException(
                    status_code=400,
                    detail=f"Bot with name '{request.name}' already exists"
                )

            # Validate core_ai_id exists and is active
            core_ai_uuid = _validate_uuid(request.core_ai_id, "core_ai_id")
            core_ai = await core_ai_crud.get_by_id(core_ai_uuid)
            if not core_ai or not core_ai.is_active:
                raise HTTPException(status_code=400, detail="Invalid or inactive core_ai_id")

            # Validate platform_id exists and is active
            platform_uuid = _validate_uuid(request.platform_id, "platform_id")
            platform = await platform_crud.get_by_id(platform_uuid)
            if not platform or not platform.is_active:
                raise HTTPException(status_code=400, detail="Invalid or inactive platform_id")

            # Create Bot using CRUD
            response = await bot_crud.create(request)

            logger.info("Bot created successfully",
                       bot_id=response.data.id,
                       name=request.name)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating Bot", error=str(e), name=request.name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Bot: {str(e)}"
        )


@router.get("/", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_bots(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all Bot configurations with pagination.

    Retrieves all Bot configurations in the system with optional pagination.
    Results include CoreAI and Platform information and are ordered by creation date.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        BotListResponse: List of Bot configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_all(skip=skip, limit=limit)

            logger.info("Bot list retrieved",
                       count=len(response.data) if response.data else 0,
                       skip=skip, limit=limit)
            return response

    except Exception as e:
        logger.error("Error listing Bots", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot list: {str(e)}"
        )


@router.get("/active", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_active_bots(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all active Bot configurations.

    Retrieves only active (is_active=True) Bot configurations.
    Useful for filtering operational bot instances.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        BotListResponse: List of active Bot configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_active(skip=skip, limit=limit)

            logger.info("Active Bot list retrieved",
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing active Bots", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Bot list: {str(e)}"
        )


@router.get("/ready", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_ready_bots(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all ready Bot configurations.

    Retrieves only ready Bot configurations (active bots with active CoreAI and Platform).
    These are bots that are fully operational and can handle conversations.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        BotListResponse: List of ready Bot configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_ready_bots(skip=skip, limit=limit)

            logger.info("Ready Bot list retrieved",
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing ready Bots", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ready Bot list: {str(e)}"
        )


@router.get("/core-ai/{core_ai_id}", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_bots_by_core_ai(core_ai_id: str):
    """
    List Bot configurations by CoreAI.

    Retrieves all Bot configurations using a specific CoreAI.
    Useful for understanding CoreAI usage across bots.

    Args:
        core_ai_id (str): Unique identifier of the CoreAI

    Returns:
        BotListResponse: List of Bot configurations using the specified CoreAI

    Raises:
        HTTPException: 400 for invalid ID format, 500 for internal errors
    """
    try:
        core_ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_by_core_ai(core_ai_uuid)

            logger.info("Bots by CoreAI retrieved",
                       core_ai_id=core_ai_id,
                       count=len(response.data) if response.data else 0)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing Bots by CoreAI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bots by CoreAI: {str(e)}"
        )


@router.get("/platform/{platform_id}", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_bots_by_platform(platform_id: str):
    """
    List Bot configurations by Platform.

    Retrieves all Bot configurations using a specific Platform.
    Useful for understanding Platform usage across bots.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        BotListResponse: List of Bot configurations using the specified Platform

    Raises:
        HTTPException: 400 for invalid ID format, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_by_platform(platform_uuid)

            logger.info("Bots by Platform retrieved",
                       platform_id=platform_id,
                       count=len(response.data) if response.data else 0)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing Bots by Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bots by Platform: {str(e)}"
        )


@router.get("/language/{language}", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def list_bots_by_language(language: str):
    """
    List Bot configurations by language.

    Retrieves all Bot configurations supporting a specific language.
    Useful for language-specific bot management.

    Args:
        language (str): Language code (e.g., 'vi', 'en')

    Returns:
        BotListResponse: List of Bot configurations supporting the specified language

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.get_by_language(language)

            logger.info("Bots by language retrieved",
                       language=language,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing Bots by language", language=language, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bots by language: {str(e)}"
        )


@router.get("/{bot_id}", dependencies=[Depends(verify_admin_token)], response_model=BotResponse)
async def get_bot(bot_id: str):
    """
    Get a specific Bot configuration by ID.

    Retrieves detailed information about a specific Bot configuration
    including CoreAI and Platform information.

    Args:
        bot_id (str): Unique identifier of the Bot

    Returns:
        BotResponse: Bot configuration details

    Raises:
        HTTPException: 400 for invalid ID format, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            bot = await bot_crud.get_by_id(bot_uuid)

            if not bot:
                logger.warning("Bot not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            logger.info("Bot retrieved", bot_id=bot_id)
            return bot

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving Bot", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot: {str(e)}"
        )


@router.put("/{bot_id}", dependencies=[Depends(verify_admin_token)], response_model=UpdateBotResponse)
async def update_bot(bot_id: str, request: UpdateBotRequest):
    """
    Update a Bot configuration.

    Updates the specified Bot configuration with the provided data.
    Validates CoreAI and Platform if they are being changed.
    Ensures name uniqueness if name is being updated.

    Args:
        bot_id (str): Unique identifier of the Bot
        request (UpdateBotRequest): Update data

    Returns:
        UpdateBotResponse: Updated Bot configuration

    Raises:
        HTTPException: 400 for invalid ID or validation errors, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            core_ai_crud = CoreAICRUD(session)
            platform_crud = PlatformCRUD(session)

            # Check if Bot exists
            existing = await bot_crud.get_by_id(bot_uuid)
            if not existing:
                logger.warning("Bot update failed - not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            # Check name uniqueness if name is being updated
            if request.name is not None:
                name_check = await bot_crud.get_by_name(request.name)
                if name_check and name_check.id != bot_id:
                    logger.warning("Bot update failed - name exists",
                                 name=request.name, bot_id=bot_id)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Bot with name '{request.name}' already exists"
                    )

            # Validate core_ai_id if being updated
            if request.core_ai_id is not None:
                core_ai_uuid = _validate_uuid(request.core_ai_id, "core_ai_id")
                core_ai = await core_ai_crud.get_by_id(core_ai_uuid)
                if not core_ai or not core_ai.is_active:
                    raise HTTPException(status_code=400, detail="Invalid or inactive core_ai_id")

            # Validate platform_id if being updated
            if request.platform_id is not None:
                platform_uuid = _validate_uuid(request.platform_id, "platform_id")
                platform = await platform_crud.get_by_id(platform_uuid)
                if not platform or not platform.is_active:
                    raise HTTPException(status_code=400, detail="Invalid or inactive platform_id")

            # Update Bot using CRUD (includes foreign key validation)
            response = await bot_crud.update(bot_uuid, request)
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            logger.info("Bot updated successfully", bot_id=bot_id)
            return response

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors
        logger.warning("Bot update failed", bot_id=bot_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating Bot", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Bot: {str(e)}"
        )


@router.delete("/{bot_id}", dependencies=[Depends(verify_admin_token)])
async def delete_bot(bot_id: str):
    """
    Delete a Bot configuration.

    Permanently removes a Bot configuration from the system.
    Validates that the Bot is not being used in conversations before deletion.

    Args:
        bot_id (str): Unique identifier of the Bot

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID or if in use, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)

            # Check if Bot exists
            existing = await bot_crud.get_by_id(bot_uuid)
            if not existing:
                logger.warning("Bot deletion failed - not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            # Delete Bot using CRUD (includes dependency check)
            deleted = await bot_crud.delete(bot_uuid)
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            logger.info("Bot deleted successfully", bot_id=bot_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Bot '{bot_id}' deleted successfully"
            }

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors (dependency constraints)
        logger.warning("Bot deletion blocked", bot_id=bot_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting Bot", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Bot: {str(e)}"
        )


@router.post("/{bot_id}/activate", dependencies=[Depends(verify_admin_token)])
async def activate_bot(bot_id: str):
    """
    Activate a Bot configuration.

    Sets the is_active flag to True, enabling the Bot for use
    in conversations and other operations.

    Args:
        bot_id (str): Unique identifier of the Bot

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)

            success = await bot_crud.activate(bot_uuid)
            if not success:
                logger.warning("Bot activation failed - not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            logger.info("Bot activated successfully", bot_id=bot_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Bot '{bot_id}' activated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error activating Bot", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate Bot: {str(e)}"
        )


@router.post("/{bot_id}/deactivate", dependencies=[Depends(verify_admin_token)])
async def deactivate_bot(bot_id: str):
    """
    Deactivate a Bot configuration.

    Sets the is_active flag to False, disabling the Bot while
    preserving the configuration for potential future reactivation.

    Args:
        bot_id (str): Unique identifier of the Bot

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)

            success = await bot_crud.deactivate(bot_uuid)
            if not success:
                logger.warning("Bot deactivation failed - not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            logger.info("Bot deactivated successfully", bot_id=bot_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Bot '{bot_id}' deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating Bot", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate Bot: {str(e)}"
        )


@router.get("/search/name", dependencies=[Depends(verify_admin_token)], response_model=BotListResponse)
async def search_bots_by_name(
    name_pattern: str = Query(..., description="Name pattern to search for")
):
    """
    Search Bot configurations by name pattern.

    Performs case-insensitive partial matching on bot names.
    Useful for finding bots by name fragments.

    Args:
        name_pattern (str): Pattern to search for in bot names

    Returns:
        BotListResponse: List of matching Bot configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            response = await bot_crud.search_by_name(name_pattern)

            logger.info("Bot search completed",
                       pattern=name_pattern,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error searching Bots by name",
                    pattern=name_pattern, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Bots: {str(e)}"
        )


@router.get("/stats/total", dependencies=[Depends(verify_admin_token)])
async def get_bot_stats():
    """
    Get Bot statistics and analytics.

    Provides comprehensive statistics including total count,
    active/inactive distribution, and ready bot count.

    Returns:
        Dict: Bot statistics and metrics

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)

            total = await bot_crud.count_total()
            active = await bot_crud.count_active()
            ready = await bot_crud.count_ready()

            stats = {
                "total_bots": total,
                "active_bots": active,
                "ready_bots": ready,
                "inactive_bots": total - active,
                "activation_rate": round((active / total * 100) if total > 0 else 0, 2),
                "readiness_rate": round((ready / active * 100) if active > 0 else 0, 2)
            }

            logger.info("Bot statistics retrieved", **stats)
            return {
                "success": True,
                "status": "success",
                "message": "Bot statistics retrieved successfully",
                "data": stats
            }

    except Exception as e:
        logger.error("Error getting Bot statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot statistics: {str(e)}"
        )


@router.get("/stats/by-core-ai", dependencies=[Depends(verify_admin_token)])
async def get_bot_stats_by_core_ai():
    """
    Get Bot statistics grouped by CoreAI.

    Provides statistics showing how many bots are using each CoreAI
    configuration, including active vs inactive distribution.

    Returns:
        Dict: Bot statistics grouped by CoreAI

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            stats = await bot_crud.get_stats_by_core_ai()

            logger.info("Bot statistics by CoreAI retrieved", count=len(stats))
            return {
                "success": True,
                "status": "success",
                "message": "Bot statistics by CoreAI retrieved successfully",
                "data": {
                    "core_ai_stats": stats,
                    "total_core_ais": len(stats)
                }
            }

    except Exception as e:
        logger.error("Error getting Bot statistics by CoreAI", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot statistics by CoreAI: {str(e)}"
        )


@router.get("/stats/by-platform", dependencies=[Depends(verify_admin_token)])
async def get_bot_stats_by_platform():
    """
    Get Bot statistics grouped by Platform.

    Provides statistics showing how many bots are using each Platform
    configuration, including active vs inactive distribution.

    Returns:
        Dict: Bot statistics grouped by Platform

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            stats = await bot_crud.get_stats_by_platform()

            logger.info("Bot statistics by Platform retrieved", count=len(stats))
            return {
                "success": True,
                "status": "success",
                "message": "Bot statistics by Platform retrieved successfully",
                "data": {
                    "platform_stats": stats,
                    "total_platforms": len(stats)
                }
            }

    except Exception as e:
        logger.error("Error getting Bot statistics by Platform", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot statistics by Platform: {str(e)}"
        )


@router.get("/stats/by-language", dependencies=[Depends(verify_admin_token)])
async def get_bot_stats_by_language():
    """
    Get Bot statistics grouped by language.

    Provides statistics showing how many bots support each language,
    including active vs inactive distribution.

    Returns:
        Dict: Bot statistics grouped by language

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            stats = await bot_crud.get_stats_by_language()

            logger.info("Bot statistics by language retrieved", count=len(stats))
            return {
                "success": True,
                "status": "success",
                "message": "Bot statistics by language retrieved successfully",
                "data": {
                    "language_stats": stats,
                    "total_languages": len(stats)
                }
            }

    except Exception as e:
        logger.error("Error getting Bot statistics by language", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot statistics by language: {str(e)}"
        )


@router.get("/{bot_id}/usage", dependencies=[Depends(verify_admin_token)])
async def get_bot_usage(bot_id: str):
    """
    Get usage statistics for a specific Bot.

    Provides detailed usage information including conversation counts
    and conversation status distribution.

    Args:
        bot_id (str): Unique identifier of the Bot

    Returns:
        Dict: Usage statistics for the specified Bot

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        bot_uuid = _validate_uuid(bot_id, "bot_id")

        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)

            # Check if Bot exists
            existing = await bot_crud.get_by_id(bot_uuid)
            if not existing:
                logger.warning("Bot usage check failed - not found", bot_id=bot_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Bot with ID '{bot_id}' not found"
                )

            # Get usage statistics
            usage_stats = await bot_crud.get_usage_stats(bot_uuid)

            logger.info("Bot usage statistics retrieved",
                       bot_id=bot_id, **usage_stats)
            return {
                "success": True,
                "status": "success",
                "message": f"Usage statistics for Bot '{bot_id}' retrieved successfully",
                "data": {
                    "bot_id": bot_id,
                    "bot_name": existing.name,
                    **usage_stats
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting Bot usage", bot_id=bot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Bot usage: {str(e)}"
        )


@router.get("/stats/popular", dependencies=[Depends(verify_admin_token)])
async def get_popular_bots(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return")
):
    """
    Get most popular Bot configurations by conversation count.

    Returns Bot configurations ordered by the number of conversations.
    Useful for understanding which bots are most utilized.

    Args:
        limit (int): Maximum number of results to return

    Returns:
        Dict: List of popular Bot configurations with conversation counts

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            bot_crud = BotCRUD(session)
            popular_bots = await bot_crud.get_popular_bots(limit=limit)

            logger.info("Popular Bot list retrieved", count=len(popular_bots))
            return {
                "success": True,
                "status": "success",
                "message": "Popular Bot configurations retrieved successfully",
                "data": {
                    "popular_bots": popular_bots,
                    "total_returned": len(popular_bots)
                }
            }

    except Exception as e:
        logger.error("Error getting popular Bots", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve popular Bots: {str(e)}"
        )