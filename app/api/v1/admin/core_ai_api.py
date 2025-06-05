"""
Core AI Admin API Endpoints

This module provides FastAPI endpoints for managing Core AI configurations
in the chatbot orchestrator system. All endpoints require admin authentication
and provide comprehensive CRUD operations with advanced features.

Features:
- Full CRUD operations (Create, Read, Update, Delete)
- Activation/Deactivation (soft delete)
- Search and filtering capabilities
- Statistics and analytics
- Usage monitoring
- Comprehensive error handling and logging

Dependencies:
- FastAPI for API framework
- CoreAICRUD for database operations
- Admin authentication for security

Author: Generated for Chatbot System Microservice Architecture
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
import structlog

from app.core.database import async_session_factory
from app.crud.core_ai_crud import CoreAICRUD
from app.schemas.request import CreateCoreAIRequest, UpdateCoreAIRequest
from app.schemas.response import (
    CoreAIResponse, CreateCoreAIResponse, UpdateCoreAIResponse,
    CoreAIListResponse
)
from app.api.dependencies import verify_admin_token

logger = structlog.get_logger(__name__)

# Admin router with authentication requirement
router = APIRouter(prefix="/core-ai")


def _validate_uuid(uuid_str: str, param_name: str) -> uuid.UUID:
    """
    Validate and convert UUID string.

    Args:
        uuid_str (str): UUID string to validate
        param_name (str): Parameter name for error Message

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


@router.post("/", dependencies=[Depends(verify_admin_token)], response_model=CreateCoreAIResponse)
async def create_core_ai(request: CreateCoreAIRequest):
    """
    Create a new Core AI configuration.

    Creates a new AI service configuration with the provided parameters.
    Validates name uniqueness before creation.

    Args:
        request (CreateCoreAIRequest): Core AI configuration data

    Returns:
        CreateCoreAIResponse: Created Core AI with success status

    Raises:
        HTTPException: 400 if name already exists, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            # Check name uniqueness
            existing = await core_ai_crud.get_by_name(request.name)
            if existing:
                logger.warning("Core AI creation failed - name exists", name=request.name)
                raise HTTPException(
                    status_code=400,
                    detail=f"Core AI with name '{request.name}' already exists"
                )

            # Create using CRUD
            response = await core_ai_crud.create(request)

            logger.info("Core AI created successfully",
                       core_ai_id=response.data.id,
                       name=request.name)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating Core AI", error=str(e), name=request.name)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error occurred while creating Core AI"
        )


@router.get("/", dependencies=[Depends(verify_admin_token)], response_model=CoreAIListResponse)
async def list_core_ai(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all Core AI configurations with pagination.

    Retrieves all Core AI configurations in the system with optional pagination.
    Results are ordered by creation date (newest first).

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        CoreAIListResponse: List of Core AI configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)
            response = await core_ai_crud.get_all(skip=skip, limit=limit)

            logger.info("Core AI list retrieved",
                       count=len(response.data) if response.data else 0,
                       skip=skip, limit=limit)
            return response

    except Exception as e:
        logger.error("Error listing Core AI", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Core AI list: {str(e)}"
        )


@router.get("/active", dependencies=[Depends(verify_admin_token)], response_model=CoreAIListResponse)
async def list_active_core_ai(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all active Core AI configurations.

    Retrieves only active (is_active=True) Core AI configurations.
    Useful for filtering operational AI services.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        CoreAIListResponse: List of active Core AI configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)
            response = await core_ai_crud.get_active(skip=skip, limit=limit)

            logger.info("Active Core AI list retrieved",
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing active Core AI", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Core AI list: {str(e)}"
        )


@router.get("/{core_ai_id}", dependencies=[Depends(verify_admin_token)], response_model=CoreAIResponse)
async def get_core_ai(core_ai_id: str):
    """
    Get a specific Core AI configuration by ID.

    Retrieves detailed information about a specific Core AI configuration
    including all related metadata and status information.

    Args:
        core_ai_id (str): Unique identifier of the Core AI

    Returns:
        CoreAIResponse: Core AI configuration details

    Raises:
        HTTPException: 400 for invalid ID format, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)
            core_ai = await core_ai_crud.get_by_id(ai_uuid)

            if not core_ai:
                logger.warning("Core AI not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            logger.info("Core AI retrieved", core_ai_id=core_ai_id)
            return core_ai

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving Core AI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Core AI: {str(e)}"
        )


@router.put("/{core_ai_id}", dependencies=[Depends(verify_admin_token)], response_model=UpdateCoreAIResponse)
async def update_core_ai(core_ai_id: str, request: UpdateCoreAIRequest):
    """
    Update a Core AI configuration.

    Updates the specified Core AI configuration with the provided data.
    Validates name uniqueness if name is being changed.

    Args:
        core_ai_id (str): Unique identifier of the Core AI
        request (UpdateCoreAIRequest): Update data

    Returns:
        UpdateCoreAIResponse: Updated Core AI configuration

    Raises:
        HTTPException: 400 for invalid ID or name conflict, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            # Check if Core AI exists
            existing = await core_ai_crud.get_by_id(ai_uuid)
            if not existing:
                logger.warning("Core AI update failed - not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            # Check name uniqueness if name is being updated
            if request.name is not None:
                name_check = await core_ai_crud.get_by_name(request.name)
                if name_check and name_check.id != core_ai_id:
                    logger.warning("Core AI update failed - name exists",
                                 name=request.name, core_ai_id=core_ai_id)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Core AI with name '{request.name}' already exists"
                    )

            # Update using CRUD
            response = await core_ai_crud.update(ai_uuid, request)
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            logger.info("Core AI updated successfully", core_ai_id=core_ai_id)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating Core AI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Core AI: {str(e)}"
        )


@router.delete("/{core_ai_id}", dependencies=[Depends(verify_admin_token)])
async def delete_core_ai(core_ai_id: str):
    """
    Delete a Core AI configuration.

    Permanently removes a Core AI configuration from the system.
    Validates that the Core AI is not being used by any bots before deletion.

    Args:
        core_ai_id (str): Unique identifier of the Core AI

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID or if in use, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            # Check if Core AI exists
            existing = await core_ai_crud.get_by_id(ai_uuid)
            if not existing:
                logger.warning("Core AI deletion failed - not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            # Delete using CRUD (includes dependency check)
            deleted = await core_ai_crud.delete(ai_uuid)
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            logger.info("Core AI deleted successfully", core_ai_id=core_ai_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Core AI '{core_ai_id}' deleted successfully"
            }

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors (dependency constraints)
        logger.warning("Core AI deletion blocked", core_ai_id=core_ai_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting Core AI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Core AI: {str(e)}"
        )


@router.post("/{core_ai_id}/activate", dependencies=[Depends(verify_admin_token)])
async def activate_core_ai(core_ai_id: str):
    """
    Activate a Core AI configuration.

    Sets the is_active flag to True, enabling the Core AI for use
    by bots and other system components.

    Args:
        core_ai_id (str): Unique identifier of the Core AI

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            success = await core_ai_crud.activate(ai_uuid)
            if not success:
                logger.warning("Core AI activation failed - not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            logger.info("Core AI activated successfully", core_ai_id=core_ai_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Core AI '{core_ai_id}' activated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error activating Core AI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate Core AI: {str(e)}"
        )


@router.post("/{core_ai_id}/deactivate", dependencies=[Depends(verify_admin_token)])
async def deactivate_core_ai(core_ai_id: str):
    """
    Deactivate a Core AI configuration.

    Sets the is_active flag to False, disabling the Core AI while
    preserving the configuration for potential future reactivation.

    Args:
        core_ai_id (str): Unique identifier of the Core AI

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            success = await core_ai_crud.deactivate(ai_uuid)
            if not success:
                logger.warning("Core AI deactivation failed - not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            logger.info("Core AI deactivated successfully", core_ai_id=core_ai_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Core AI '{core_ai_id}' deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating Core AI", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate Core AI: {str(e)}"
        )


@router.get("/search/endpoint", dependencies=[Depends(verify_admin_token)], response_model=CoreAIListResponse)
async def search_core_ai_by_endpoint(
    endpoint_pattern: str = Query(..., description="Pattern to search for in API endpoints")
):
    """
    Search Core AI configurations by API endpoint pattern.

    Performs case-insensitive partial matching on API endpoint URLs.
    Useful for finding AI services by their endpoint patterns.

    Args:
        endpoint_pattern (str): Pattern to search for in endpoints

    Returns:
        CoreAIListResponse: List of matching Core AI configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)
            response = await core_ai_crud.search_by_endpoint(endpoint_pattern)

            logger.info("Core AI search completed",
                       pattern=endpoint_pattern,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error searching Core AI by endpoint",
                    pattern=endpoint_pattern, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Core AI: {str(e)}"
        )


@router.get("/stats/total", dependencies=[Depends(verify_admin_token)])
async def get_core_ai_stats():
    """
    Get Core AI statistics and analytics.

    Provides comprehensive statistics including total count,
    active/inactive distribution, and other relevant metrics.

    Returns:
        Dict: Core AI statistics and metrics

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            total = await core_ai_crud.count_total()
            active = await core_ai_crud.count_active()

            stats = {
                "total_core_ai": total,
                "active_core_ai": active,
                "inactive_core_ai": total - active,
                "activation_rate": round((active / total * 100) if total > 0 else 0, 2)
            }

            logger.info("Core AI statistics retrieved", **stats)
            return {
                "success": True,
                "status": "success",
                "message": "Core AI statistics retrieved successfully",
                "data": stats
            }

    except Exception as e:
        logger.error("Error getting Core AI statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Core AI statistics: {str(e)}"
        )


@router.get("/{core_ai_id}/usage", dependencies=[Depends(verify_admin_token)])
async def get_core_ai_usage(core_ai_id: str):
    """
    Get usage statistics for a specific Core AI.

    Provides detailed usage information including bot count,
    active bot count, and other usage metrics.

    Args:
        core_ai_id (str): Unique identifier of the Core AI

    Returns:
        Dict: Usage statistics for the specified Core AI

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        ai_uuid = _validate_uuid(core_ai_id, "core_ai_id")

        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)

            # Check if Core AI exists
            existing = await core_ai_crud.get_by_id(ai_uuid)
            if not existing:
                logger.warning("Core AI usage check failed - not found", core_ai_id=core_ai_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Core AI with ID '{core_ai_id}' not found"
                )

            # Get usage statistics
            usage_stats = await core_ai_crud.get_usage_stats(ai_uuid)

            logger.info("Core AI usage statistics retrieved",
                       core_ai_id=core_ai_id, **usage_stats)
            return {
                "success": True,
                "status": "success",
                "message": f"Usage statistics for Core AI '{core_ai_id}' retrieved successfully",
                "data": {
                    "core_ai_id": core_ai_id,
                    "core_ai_name": existing.name,
                    **usage_stats
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting Core AI usage", core_ai_id=core_ai_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Core AI usage: {str(e)}"
        )


@router.get("/stats/popular", dependencies=[Depends(verify_admin_token)])
async def get_popular_core_ais(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return")
):
    """
    Get most popular Core AI configurations by bot count.

    Returns Core AI configurations ordered by the number of bots using them.
    Useful for understanding which AI services are most utilized.

    Args:
        limit (int): Maximum number of results to return

    Returns:
        Dict: List of popular Core AI configurations with usage counts

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            core_ai_crud = CoreAICRUD(session)
            popular_core_ais = await core_ai_crud.get_popular_core_ais(limit=limit)

            logger.info("Popular Core AI list retrieved", count=len(popular_core_ais))
            return {
                "success": True,
                "status": "success",
                "message": "Popular Core AI configurations retrieved successfully",
                "data": {
                    "popular_core_ais": popular_core_ais,
                    "total_returned": len(popular_core_ais)
                }
            }

    except Exception as e:
        logger.error("Error getting popular Core AI", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve popular Core AI: {str(e)}"
        )