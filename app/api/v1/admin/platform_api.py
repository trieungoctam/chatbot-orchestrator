"""
Platform Admin API Endpoints

This module provides FastAPI endpoints for managing Platform and PlatformAction
configurations in the chatbot orchestrator system. All endpoints require admin
authentication and provide comprehensive CRUD operations with advanced features.

Features:
- Full CRUD operations for both Platform and PlatformAction
- Activation/Deactivation (soft delete)
- Search and filtering capabilities
- Statistics and analytics
- Usage monitoring
- Comprehensive error handling and logging

Dependencies:
- FastAPI for API framework
- PlatformCRUD and PlatformActionCRUD for database operations
- Admin authentication for security

Author: Generated for Chatbot System Microservice Architecture
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
import structlog

from app.core.database import async_session_factory
from app.crud.platform_crud import PlatformCRUD, PlatformActionCRUD
from app.schemas.request import (
    CreatePlatformRequest, UpdatePlatformRequest,
    CreatePlatformActionRequest, UpdatePlatformActionRequest
)
from app.schemas.response import (
    PlatformResponse, CreatePlatformResponse, UpdatePlatformResponse, PlatformListResponse,
    PlatformActionResponse, CreatePlatformActionResponse, UpdatePlatformActionResponse, PlatformActionListResponse
)
from app.api.dependencies import verify_admin_token

logger = structlog.get_logger(__name__)

# Admin router with authentication requirement
router = APIRouter(prefix="/platform")


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


# ===============================================
# PLATFORM ACTIONS MANAGEMENT
# ===============================================

@router.post("/actions", dependencies=[Depends(verify_admin_token)], response_model=CreatePlatformActionResponse)
async def create_platform_action(request: CreatePlatformActionRequest):
    """
    Create a new Platform Action.

    Creates a new action configuration for a specific platform.
    Validates that the specified platform exists before creation.

    Args:
        request (CreatePlatformActionRequest): Platform Action configuration data

    Returns:
        CreatePlatformActionResponse: Created Platform Action with success status

    Raises:
        HTTPException: 400 if platform invalid, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            # Create Platform Action using CRUD (includes platform validation)
            response = await action_crud.create(request)

            logger.info("Platform Action created successfully",
                       action_id=response.data.id,
                       name=request.name)
            return response

    except ValueError as e:
        # Handle validation errors from CRUD
        logger.warning("Platform Action creation failed", reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating Platform Action", error=str(e), name=request.name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Platform Action: {str(e)}"
        )


@router.get("/actions", dependencies=[Depends(verify_admin_token)], response_model=PlatformActionListResponse)
async def list_platform_actions(
    platform_id: Optional[str] = Query(None, description="Filter by platform ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all Platform Actions, optionally filtered by platform_id.

    Retrieves Platform Actions with optional filtering by platform.
    Results are paginated and ordered by creation date.

    Args:
        platform_id (str, optional): Filter by platform ID
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        PlatformActionListResponse: List of Platform Actions

    Raises:
        HTTPException: 400 for invalid platform_id format, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            if platform_id:
                platform_uuid = _validate_uuid(platform_id, "platform_id")
                response = await action_crud.get_by_platform(platform_uuid)
            else:
                response = await action_crud.get_all(skip=skip, limit=limit)

            logger.info("Platform Actions list retrieved",
                       platform_id=platform_id,
                       count=len(response.data) if response.data else 0)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing Platform Actions", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform Actions: {str(e)}"
        )


@router.get("/actions/active", dependencies=[Depends(verify_admin_token)], response_model=PlatformActionListResponse)
async def list_active_platform_actions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all active Platform Actions.

    Retrieves only active Platform Actions across all platforms.
    Useful for finding operational actions.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        PlatformActionListResponse: List of active Platform Actions

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)
            response = await action_crud.get_active(skip=skip, limit=limit)

            logger.info("Active Platform Actions list retrieved",
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing active Platform Actions", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Platform Actions: {str(e)}"
        )


@router.get("/actions/method/{method_type}", dependencies=[Depends(verify_admin_token)], response_model=PlatformActionListResponse)
async def list_platform_actions_by_method(method_type: str):
    """
    List Platform Actions by HTTP method.

    Retrieves all Platform Actions with a specific HTTP method across all platforms.
    Useful for finding actions with specific HTTP method types (GET, POST, PUT, DELETE).

    Args:
        method_type (str): The HTTP method to filter by (GET, POST, PUT, DELETE)

    Returns:
        PlatformActionListResponse: List of Platform Actions with the specified method

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)
            response = await action_crud.get_by_type(method_type)

            logger.info("Platform Actions by method retrieved",
                       method_type=method_type,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing Platform Actions by method",
                    method_type=method_type, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform Actions by method: {str(e)}"
        )


@router.get("/actions/{action_id}", dependencies=[Depends(verify_admin_token)], response_model=PlatformActionResponse)
async def get_platform_action(action_id: str):
    """
    Get a specific Platform Action by ID.

    Retrieves detailed information about a specific Platform Action
    including platform information and action configuration.

    Args:
        action_id (str): Unique identifier of the Platform Action

    Returns:
        PlatformActionResponse: Platform Action details

    Raises:
        HTTPException: 400 for invalid ID format, 404 if not found, 500 for internal errors
    """
    try:
        action_uuid = _validate_uuid(action_id, "action_id")

        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)
            action = await action_crud.get_by_id(action_uuid)

            if not action:
                logger.warning("Platform Action not found", action_id=action_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            logger.info("Platform Action retrieved", action_id=action_id)
            return action

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving Platform Action", action_id=action_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform Action: {str(e)}"
        )


@router.put("/actions/{action_id}", dependencies=[Depends(verify_admin_token)], response_model=UpdatePlatformActionResponse)
async def update_platform_action(action_id: str, request: UpdatePlatformActionRequest):
    """
    Update a Platform Action configuration.

    Updates the specified Platform Action with the provided data.
    Validates platform_id if it's being changed.

    Args:
        action_id (str): Unique identifier of the Platform Action
        request (UpdatePlatformActionRequest): Update data

    Returns:
        UpdatePlatformActionResponse: Updated Platform Action configuration

    Raises:
        HTTPException: 400 for invalid ID or platform, 404 if not found, 500 for internal errors
    """
    try:
        action_uuid = _validate_uuid(action_id, "action_id")

        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            # Check if Action exists
            existing = await action_crud.get_by_id(action_uuid)
            if not existing:
                logger.warning("Platform Action update failed - not found", action_id=action_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            # Update using CRUD (includes platform validation if needed)
            response = await action_crud.update(action_uuid, request)
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            logger.info("Platform Action updated successfully", action_id=action_id)
            return response

    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors from CRUD
        logger.warning("Platform Action update failed", action_id=action_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating Platform Action", action_id=action_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Platform Action: {str(e)}"
        )


@router.delete("/actions/{action_id}", dependencies=[Depends(verify_admin_token)])
async def delete_platform_action(action_id: str):
    """
    Delete a Platform Action configuration.

    Permanently removes a Platform Action from the system.
    Validates that the action is not being used before deletion.

    Args:
        action_id (str): Unique identifier of the Platform Action

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID or if in use, 404 if not found, 500 for internal errors
    """
    try:
        action_uuid = _validate_uuid(action_id, "action_id")

        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            # Check if Action exists
            existing = await action_crud.get_by_id(action_uuid)
            if not existing:
                logger.warning("Platform Action deletion failed - not found", action_id=action_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            # Delete using CRUD
            deleted = await action_crud.delete(action_uuid)
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            logger.info("Platform Action deleted successfully", action_id=action_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform Action '{action_id}' deleted successfully"
            }

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors
        logger.warning("Platform Action deletion blocked", action_id=action_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting Platform Action", action_id=action_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Platform Action: {str(e)}"
        )


@router.post("/actions/{action_id}/activate", dependencies=[Depends(verify_admin_token)])
async def activate_platform_action(action_id: str):
    """
    Activate a Platform Action.

    Sets the is_active flag to True, enabling the Platform Action
    for use in platform operations.

    Args:
        action_id (str): Unique identifier of the Platform Action

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        action_uuid = _validate_uuid(action_id, "action_id")

        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            success = await action_crud.activate(action_uuid)
            if not success:
                logger.warning("Platform Action activation failed - not found", action_id=action_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            logger.info("Platform Action activated successfully", action_id=action_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform Action '{action_id}' activated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error activating Platform Action", action_id=action_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate Platform Action: {str(e)}"
        )


@router.post("/actions/{action_id}/deactivate", dependencies=[Depends(verify_admin_token)])
async def deactivate_platform_action(action_id: str):
    """
    Deactivate a Platform Action.

    Sets the is_active flag to False, disabling the Platform Action
    while preserving the configuration for potential future reactivation.

    Args:
        action_id (str): Unique identifier of the Platform Action

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        action_uuid = _validate_uuid(action_id, "action_id")

        async with async_session_factory() as session:
            action_crud = PlatformActionCRUD(session)

            success = await action_crud.deactivate(action_uuid)
            if not success:
                logger.warning("Platform Action deactivation failed - not found", action_id=action_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform Action with ID '{action_id}' not found"
                )

            logger.info("Platform Action deactivated successfully", action_id=action_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform Action '{action_id}' deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating Platform Action", action_id=action_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate Platform Action: {str(e)}"
        )


# ===============================================
# PLATFORM MANAGEMENT
# ===============================================

@router.post("/", dependencies=[Depends(verify_admin_token)], response_model=CreatePlatformResponse)
async def create_platform(request: CreatePlatformRequest):
    """
    Create a new Platform configuration.

    Creates a new communication platform configuration with the provided parameters.
    Validates name uniqueness before creation.

    Args:
        request (CreatePlatformRequest): Platform configuration data

    Returns:
        CreatePlatformResponse: Created Platform with success status

    Raises:
        HTTPException: 400 if name already exists, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            # Check name uniqueness
            existing = await platform_crud.get_by_name(request.name)
            if existing:
                logger.warning("Platform creation failed - name exists", name=request.name)
                raise HTTPException(
                    status_code=400,
                    detail=f"Platform with name '{request.name}' already exists"
                )

            # Create using CRUD
            response = await platform_crud.create(request)

            logger.info("Platform created successfully",
                       platform_id=response.data.id,
                       name=request.name)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating Platform", error=str(e), name=request.name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Platform: {str(e)}"
        )


@router.get("/", dependencies=[Depends(verify_admin_token)], response_model=PlatformListResponse)
async def list_platforms(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all Platform configurations with pagination.

    Retrieves all Platform configurations in the system with optional pagination.
    Results are ordered by creation date (newest first).

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        PlatformListResponse: List of Platform configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            response = await platform_crud.get_all(skip=skip, limit=limit)

            logger.info("Platform list retrieved",
                       count=len(response.data) if response.data else 0,
                       skip=skip, limit=limit)
            return response

    except Exception as e:
        logger.error("Error listing Platforms", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform list: {str(e)}"
        )


@router.get("/active", dependencies=[Depends(verify_admin_token)], response_model=PlatformListResponse)
async def list_active_platforms(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all active Platform configurations.

    Retrieves only active (is_active=True) Platform configurations.
    Useful for filtering operational platform services.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        PlatformListResponse: List of active Platform configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            response = await platform_crud.get_active(skip=skip, limit=limit)

            logger.info("Active Platform list retrieved",
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error listing active Platforms", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Platform list: {str(e)}"
        )


@router.get("/search/url", dependencies=[Depends(verify_admin_token)], response_model=PlatformListResponse)
async def search_platform_by_url(
    url_pattern: str = Query(..., description="URL pattern to search for in base URLs")
):
    """
    Search Platform configurations by base URL pattern.

    Performs case-insensitive partial matching on base URL fields.
    Useful for finding platform services by their URL patterns.

    Args:
        url_pattern (str): Pattern to search for in base URLs

    Returns:
        PlatformListResponse: List of matching Platform configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            response = await platform_crud.search_by_url(url_pattern)

            logger.info("Platform search completed",
                       pattern=url_pattern,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error searching Platform by URL",
                    pattern=url_pattern, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Platform: {str(e)}"
        )


@router.get("/search/name", dependencies=[Depends(verify_admin_token)], response_model=PlatformListResponse)
async def search_platform_by_name(
    name_pattern: str = Query(..., description="Name pattern to search for in platform names")
):
    """
    Search Platform configurations by name pattern.

    Performs case-insensitive partial matching on platform names.
    Useful for finding platforms by name fragments.

    Args:
        name_pattern (str): Pattern to search for in platform names

    Returns:
        PlatformListResponse: List of matching Platform configurations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            response = await platform_crud.search_by_name(name_pattern)

            logger.info("Platform name search completed",
                       pattern=name_pattern,
                       count=len(response.data) if response.data else 0)
            return response

    except Exception as e:
        logger.error("Error searching Platform by name",
                    pattern=name_pattern, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Platform by name: {str(e)}"
        )


@router.get("/stats/total", dependencies=[Depends(verify_admin_token)])
async def get_platform_stats():
    """
    Get Platform statistics and analytics.

    Provides comprehensive statistics including total count,
    active/inactive distribution, and other relevant metrics.

    Returns:
        Dict: Platform statistics and metrics

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            total = await platform_crud.count_total()
            active = await platform_crud.count_active()

            stats = {
                "total_platforms": total,
                "active_platforms": active,
                "inactive_platforms": total - active,
                "activation_rate": round((active / total * 100) if total > 0 else 0, 2)
            }

            logger.info("Platform statistics retrieved", **stats)
            return {
                "success": True,
                "status": "success",
                "message": "Platform statistics retrieved successfully",
                "data": stats
            }

    except Exception as e:
        logger.error("Error getting Platform statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform statistics: {str(e)}"
        )


@router.get("/stats/popular", dependencies=[Depends(verify_admin_token)])
async def get_popular_platforms(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return")
):
    """
    Get most popular Platform configurations by bot count.

    Returns Platform configurations ordered by the number of bots using them.
    Useful for understanding which platform services are most utilized.

    Args:
        limit (int): Maximum number of results to return

    Returns:
        Dict: List of popular Platform configurations with usage counts

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            popular_platforms = await platform_crud.get_popular_platforms(limit=limit)

            logger.info("Popular Platform list retrieved", count=len(popular_platforms))
            return {
                "success": True,
                "status": "success",
                "message": "Popular Platform configurations retrieved successfully",
                "data": {
                    "popular_platforms": popular_platforms,
                    "total_returned": len(popular_platforms)
                }
            }

    except Exception as e:
        logger.error("Error getting popular Platform", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve popular Platform: {str(e)}"
        )


@router.get("/{platform_id}", dependencies=[Depends(verify_admin_token)], response_model=PlatformResponse)
async def get_platform(platform_id: str):
    """
    Get a specific Platform configuration by ID.

    Retrieves detailed information about a specific Platform configuration
    including all related metadata and status information.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        PlatformResponse: Platform configuration details

    Raises:
        HTTPException: 400 for invalid ID format, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)
            platform = await platform_crud.get_by_id(platform_uuid)

            if not platform:
                logger.warning("Platform not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            logger.info("Platform retrieved", platform_id=platform_id)
            return platform

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform: {str(e)}"
        )


@router.put("/{platform_id}", dependencies=[Depends(verify_admin_token)], response_model=UpdatePlatformResponse)
async def update_platform(platform_id: str, request: UpdatePlatformRequest):
    """
    Update a Platform configuration.

    Updates the specified Platform configuration with the provided data.
    Validates name uniqueness if name is being changed.

    Args:
        platform_id (str): Unique identifier of the Platform
        request (UpdatePlatformRequest): Update data

    Returns:
        UpdatePlatformResponse: Updated Platform configuration

    Raises:
        HTTPException: 400 for invalid ID or name conflict, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            # Check if Platform exists
            existing = await platform_crud.get_by_id(platform_uuid)
            if not existing:
                logger.warning("Platform update failed - not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            # Check name uniqueness if name is being updated
            if request.name is not None:
                name_check = await platform_crud.get_by_name(request.name)
                if name_check and name_check.id != platform_id:
                    logger.warning("Platform update failed - name exists",
                                 name=request.name, platform_id=platform_id)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Platform with name '{request.name}' already exists"
                    )

            # Update using CRUD
            response = await platform_crud.update(platform_uuid, request)
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            logger.info("Platform updated successfully", platform_id=platform_id)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Platform: {str(e)}"
        )


@router.delete("/{platform_id}", dependencies=[Depends(verify_admin_token)])
async def delete_platform(platform_id: str):
    """
    Delete a Platform configuration.

    Permanently removes a Platform configuration from the system.
    Validates that the Platform is not being used by any bots before deletion.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID or if in use, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            # Check if Platform exists
            existing = await platform_crud.get_by_id(platform_uuid)
            if not existing:
                logger.warning("Platform deletion failed - not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            # Delete using CRUD (includes dependency check)
            deleted = await platform_crud.delete(platform_uuid)
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            logger.info("Platform deleted successfully", platform_id=platform_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform '{platform_id}' deleted successfully"
            }

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors (dependency constraints)
        logger.warning("Platform deletion blocked", platform_id=platform_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Platform: {str(e)}"
        )


@router.post("/{platform_id}/activate", dependencies=[Depends(verify_admin_token)])
async def activate_platform(platform_id: str):
    """
    Activate a Platform configuration.

    Sets the is_active flag to True, enabling the Platform for use
    by bots and other system components.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            success = await platform_crud.activate(platform_uuid)
            if not success:
                logger.warning("Platform activation failed - not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            logger.info("Platform activated successfully", platform_id=platform_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform '{platform_id}' activated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error activating Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate Platform: {str(e)}"
        )


@router.post("/{platform_id}/deactivate", dependencies=[Depends(verify_admin_token)])
async def deactivate_platform(platform_id: str):
    """
    Deactivate a Platform configuration.

    Sets the is_active flag to False, disabling the Platform while
    preserving the configuration for potential future reactivation.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            success = await platform_crud.deactivate(platform_uuid)
            if not success:
                logger.warning("Platform deactivation failed - not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            logger.info("Platform deactivated successfully", platform_id=platform_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Platform '{platform_id}' deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating Platform", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate Platform: {str(e)}"
        )


@router.get("/{platform_id}/usage", dependencies=[Depends(verify_admin_token)])
async def get_platform_usage(platform_id: str):
    """
    Get usage statistics for a specific Platform.

    Provides detailed usage information including bot count,
    action count, and other usage metrics.

    Args:
        platform_id (str): Unique identifier of the Platform

    Returns:
        Dict: Usage statistics for the specified Platform

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        platform_uuid = _validate_uuid(platform_id, "platform_id")

        async with async_session_factory() as session:
            platform_crud = PlatformCRUD(session)

            # Check if Platform exists
            existing = await platform_crud.get_by_id(platform_uuid)
            if not existing:
                logger.warning("Platform usage check failed - not found", platform_id=platform_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Platform with ID '{platform_id}' not found"
                )

            # Get usage statistics
            usage_stats = await platform_crud.get_usage_stats(platform_uuid)

            logger.info("Platform usage statistics retrieved",
                       platform_id=platform_id, **usage_stats)
            return {
                "success": True,
                "status": "success",
                "message": f"Usage statistics for Platform '{platform_id}' retrieved successfully",
                "data": {
                    "platform_id": platform_id,
                    "platform_name": existing.name,
                    **usage_stats
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting Platform usage", platform_id=platform_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Platform usage: {str(e)}"
        )