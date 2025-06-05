"""
Conversation Admin API Endpoints

This module provides FastAPI endpoints for managing Conversation configurations
in the chatbot orchestrator system. All endpoints require admin authentication
and provide comprehensive CRUD operations with advanced features.

Features:
- Full CRUD operations for Conversations and Messages
- Filter by bot, status, date ranges
- Search and analytics capabilities
- Conversation lifecycle management (start, end, pause, resume)
- Message management within conversations
- Statistics and monitoring
- Comprehensive error handling and logging

Dependencies:
- FastAPI for API framework
- ConversationCRUD and MessageCRUD for database operations
- Admin authentication for security

Author: Generated for Chatbot System Microservice Architecture
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta
import structlog

from app.core.database import async_session_factory
from app.crud.conversation_crud import ConversationCRUD, MessageCRUD
from app.crud.bot_crud import BotCRUD
from app.schemas.request import (
    CreateConversationRequest, UpdateConversationRequest,
    CreateMessageRequest, UpdateMessageRequest
)
from app.schemas.response import (
    ConversationResponse, CreateConversationResponse, UpdateConversationResponse, ConversationListResponse,
    MessageResponse, CreateMessageResponse, UpdateMessageResponse, MessageListResponse
)
from app.api.dependencies import verify_admin_token

logger = structlog.get_logger(__name__)

# Admin router with authentication requirement
router = APIRouter(prefix="/conversation")


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
# CONVERSATION MANAGEMENT
# ===============================================

@router.post("/", dependencies=[Depends(verify_admin_token)], response_model=CreateConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new Conversation for a Bot.

    Creates a new conversation with the specified bot and configuration.
    Validates that the bot exists and is active before creation.

    Args:
        request (CreateConversationRequest): Conversation configuration data

    Returns:
        CreateConversationResponse: Created Conversation with success status

    Raises:
        HTTPException: 400 if bot invalid or inactive, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            bot_crud = BotCRUD(session)

            # Validate bot exists and is active
            bot_uuid = _validate_uuid(request.bot_id, "bot_id")
            bot = await bot_crud.get_by_id(bot_uuid)
            if not bot or not bot.is_active:
                logger.warning("Conversation creation failed - invalid bot", bot_id=request.bot_id)
                raise HTTPException(
                    status_code=400,
                    detail=f"Bot with ID '{request.bot_id}' not found or inactive"
                )

            # Create Conversation using CRUD
            conversation_data = await conversation_crud.create(request)

            logger.info("Conversation created successfully",
                       conversation_id=conversation_data.id,
                       bot_id=request.bot_id)

            return CreateConversationResponse(
                success=True,
                status="success",
                message="Conversation created successfully",
                data=conversation_data
            )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors
        logger.warning("Conversation creation failed", reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating Conversation", error=str(e), bot_id=request.bot_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Conversation: {str(e)}"
        )


@router.get("/", dependencies=[Depends(verify_admin_token)], response_model=ConversationListResponse)
async def list_conversations(
    bot_id: Optional[str] = Query(None, description="Filter by bot ID"),
    status: Optional[str] = Query(None, description="Filter by conversation status"),
    hours: Optional[int] = Query(None, description="Filter conversations from last N hours"),
    min_messages: Optional[int] = Query(None, description="Minimum message count"),
    max_messages: Optional[int] = Query(None, description="Maximum message count"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List Conversations with advanced filtering options.

    Retrieves conversations with optional filtering by bot, status, time range,
    and message count. Results are paginated and ordered by update time.

    Args:
        bot_id (str, optional): Filter by specific bot ID
        status (str, optional): Filter by conversation status
        hours (int, optional): Get conversations from last N hours
        min_messages (int, optional): Minimum message count filter
        max_messages (int, optional): Maximum message count filter
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        ConversationListResponse: List of Conversation configurations

    Raises:
        HTTPException: 400 for invalid parameters, 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            # Apply filters based on parameters
            if bot_id:
                bot_uuid = _validate_uuid(bot_id, "bot_id")
                conversations = await conversation_crud.get_by_bot(bot_uuid, skip=skip, limit=limit)
            elif status:
                conversations = await conversation_crud.get_by_status(status, skip=skip, limit=limit)
            elif hours:
                conversations = await conversation_crud.get_recent(hours=hours, skip=skip, limit=limit)
            elif min_messages is not None:
                conversations = await conversation_crud.get_with_message_count_range(
                    min_count=min_messages, max_count=max_messages
                )
            else:
                conversations = await conversation_crud.get_all(skip=skip, limit=limit)

            logger.info("Conversations list retrieved",
                       count=len(conversations),
                       bot_id=bot_id, status=status, hours=hours)

            return ConversationListResponse(
                success=True,
                status="success",
                message="Conversations retrieved successfully",
                data=conversations
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing Conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Conversations: {str(e)}"
        )


@router.get("/active", dependencies=[Depends(verify_admin_token)], response_model=ConversationListResponse)
async def list_active_conversations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    List all active Conversations.

    Retrieves only active conversations (is_active=True).
    Useful for monitoring ongoing conversations.

    Args:
        skip (int): Number of records to skip for pagination
        limit (int): Maximum number of records to return

    Returns:
        ConversationListResponse: List of active Conversations

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            conversations = await conversation_crud.get_active(skip=skip, limit=limit)

            logger.info("Active Conversations list retrieved", count=len(conversations))
            return ConversationListResponse(
                success=True,
                status="success",
                message="Active Conversations retrieved successfully",
                data=conversations
            )

    except Exception as e:
        logger.error("Error listing active Conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Conversations: {str(e)}"
        )


@router.get("/{conversation_id}", dependencies=[Depends(verify_admin_token)], response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """
    Get a specific Conversation by ID.

    Retrieves detailed information about a conversation including
    metadata, context, and current status.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        ConversationResponse: Conversation details

    Raises:
        HTTPException: 400 for invalid ID format, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            conversation = await conversation_crud.get_by_id(conversation_uuid)

            if not conversation:
                logger.warning("Conversation not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation retrieved", conversation_id=conversation_id)
            return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Conversation: {str(e)}"
        )


@router.put("/{conversation_id}", dependencies=[Depends(verify_admin_token)], response_model=UpdateConversationResponse)
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """
    Update a Conversation configuration.

    Updates the specified conversation with the provided data.
    Validates bot if it's being changed.

    Args:
        conversation_id (str): Unique identifier of the Conversation
        request (UpdateConversationRequest): Update data

    Returns:
        UpdateConversationResponse: Updated Conversation configuration

    Raises:
        HTTPException: 400 for invalid ID or validation errors, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            # Check if Conversation exists
            existing = await conversation_crud.get_by_id(conversation_uuid)
            if not existing:
                logger.warning("Conversation update failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            # Validate bot if being updated
            if request.bot_id is not None:
                bot_crud = BotCRUD(session)
                bot_uuid = _validate_uuid(request.bot_id, "bot_id")
                bot = await bot_crud.get_by_id(bot_uuid)
                if not bot or not bot.is_active:
                    raise HTTPException(status_code=400, detail="Invalid or inactive bot_id")

            # Update using CRUD
            updated_conversation = await conversation_crud.update(conversation_uuid, request)
            if not updated_conversation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation updated successfully", conversation_id=conversation_id)
            return UpdateConversationResponse(
                success=True,
                status="success",
                message="Conversation updated successfully",
                data=updated_conversation
            )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors
        logger.warning("Conversation update failed", conversation_id=conversation_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Conversation: {str(e)}"
        )


@router.delete("/{conversation_id}", dependencies=[Depends(verify_admin_token)])
async def delete_conversation(conversation_id: str):
    """
    Delete a Conversation and all its messages.

    Permanently removes a conversation from the system including
    all associated messages. Use with caution.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            # Check if Conversation exists
            existing = await conversation_crud.get_by_id(conversation_uuid)
            if not existing:
                logger.warning("Conversation deletion failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            # Delete Conversation
            deleted = await conversation_crud.delete(conversation_uuid)
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation deleted successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' and all messages deleted successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Conversation: {str(e)}"
        )


# ===============================================
# CONVERSATION LIFECYCLE MANAGEMENT
# ===============================================

@router.post("/{conversation_id}/end", dependencies=[Depends(verify_admin_token)])
async def end_conversation(conversation_id: str):
    """
    End a conversation (set status to 'ended').

    Marks the conversation as completed. No further messages
    should be processed for ended conversations.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            success = await conversation_crud.end_conversation(conversation_uuid)
            if not success:
                logger.warning("Conversation end failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation ended successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' ended successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error ending Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end Conversation: {str(e)}"
        )


@router.post("/{conversation_id}/pause", dependencies=[Depends(verify_admin_token)])
async def pause_conversation(conversation_id: str):
    """
    Pause a conversation.

    Temporarily suspends conversation processing while preserving
    the conversation state for potential resumption.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            success = await conversation_crud.pause_conversation(conversation_uuid)
            if not success:
                logger.warning("Conversation pause failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation paused successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' paused successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error pausing Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause Conversation: {str(e)}"
        )


@router.post("/{conversation_id}/resume", dependencies=[Depends(verify_admin_token)])
async def resume_conversation(conversation_id: str):
    """
    Resume a paused conversation.

    Reactivates a paused conversation, allowing message processing
    to continue from where it left off.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            success = await conversation_crud.resume_conversation(conversation_uuid)
            if not success:
                logger.warning("Conversation resume failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation resumed successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' resumed successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error resuming Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume Conversation: {str(e)}"
        )


@router.post("/{conversation_id}/activate", dependencies=[Depends(verify_admin_token)])
async def activate_conversation(conversation_id: str):
    """
    Activate a deactivated conversation.

    Reactivates a conversation that was previously deactivated,
    making it available for processing again.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            success = await conversation_crud.activate(conversation_uuid)
            if not success:
                logger.warning("Conversation activation failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation activated successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' activated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error activating Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate Conversation: {str(e)}"
        )


@router.post("/{conversation_id}/deactivate", dependencies=[Depends(verify_admin_token)])
async def deactivate_conversation(conversation_id: str):
    """
    Deactivate a conversation (soft delete).

    Marks a conversation as inactive while preserving all data.
    Preferred over hard delete for audit trails.

    Args:
        conversation_id (str): Unique identifier of the Conversation

    Returns:
        Dict: Success confirmation message

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            success = await conversation_crud.deactivate(conversation_uuid)
            if not success:
                logger.warning("Conversation deactivation failed - not found", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            logger.info("Conversation deactivated successfully", conversation_id=conversation_id)
            return {
                "success": True,
                "status": "success",
                "message": f"Conversation '{conversation_id}' deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating Conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate Conversation: {str(e)}"
        )


# ===============================================
# CONVERSATION MESSAGES MANAGEMENT
# ===============================================

@router.get("/{conversation_id}/messages", dependencies=[Depends(verify_admin_token)], response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of messages to return")
):
    """
    Get all messages for a specific conversation.

    Retrieves the message history for a conversation ordered by creation time.
    Useful for reviewing conversation content and debugging.

    Args:
        conversation_id (str): Unique identifier of the Conversation
        limit (int): Maximum number of messages to return

    Returns:
        MessageListResponse: List of messages in the conversation

    Raises:
        HTTPException: 400 for invalid ID, 404 if not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            # Verify conversation exists
            conversation = await conversation_crud.get_by_id(conversation_uuid)
            if not conversation:
                logger.warning("Conversation not found for messages", conversation_id=conversation_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID '{conversation_id}' not found"
                )

            # Get messages
            messages = await conversation_crud.get_conversation_messages(conversation_uuid, limit=limit)

            logger.info("Conversation messages retrieved",
                       conversation_id=conversation_id,
                       message_count=len(messages))

            return MessageListResponse(
                success=True,
                status="success",
                message=f"Messages for conversation '{conversation_id}' retrieved successfully",
                data=messages
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting conversation messages",
                    conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation messages: {str(e)}"
        )


@router.post("/{conversation_id}/messages", dependencies=[Depends(verify_admin_token)], response_model=CreateMessageResponse)
async def create_message(conversation_id: str, request: CreateMessageRequest):
    """
    Create a new message in a conversation.

    Adds a new message to the specified conversation and updates
    the conversation's message count automatically.

    Args:
        conversation_id (str): Unique identifier of the Conversation
        request (CreateMessageRequest): Message data

    Returns:
        CreateMessageResponse: Created message with success status

    Raises:
        HTTPException: 400 for invalid ID or data, 404 if conversation not found, 500 for internal errors
    """
    try:
        conversation_uuid = _validate_uuid(conversation_id, "conversation_id")

        # Ensure the conversation_id in request matches the URL parameter
        if request.conversation_id != conversation_id:
            raise HTTPException(
                status_code=400,
                detail="Conversation ID in request body must match URL parameter"
            )

        async with async_session_factory() as session:
            message_crud = MessageCRUD(session)

            # Create message (CRUD will validate conversation exists)
            message_data = await message_crud.create(request)

            logger.info("Message created successfully",
                       message_id=message_data.id,
                       conversation_id=conversation_id)

            return CreateMessageResponse(
                success=True,
                status="success",
                message="Message created successfully",
                data=message_data
            )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle CRUD validation errors
        logger.warning("Message creation failed", conversation_id=conversation_id, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating Message", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Message: {str(e)}"
        )


# ===============================================
# CONVERSATION STATISTICS AND ANALYTICS
# ===============================================

@router.get("/stats/total", dependencies=[Depends(verify_admin_token)])
async def get_conversation_stats():
    """
    Get comprehensive conversation statistics.

    Provides statistics including total count, active/inactive distribution,
    average message count, and status distribution.

    Returns:
        Dict: Conversation statistics and metrics

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)

            total = await conversation_crud.count_total()
            active = await conversation_crud.count_active()
            avg_messages = await conversation_crud.get_avg_message_count()

            # Get status distribution
            status_counts = {}
            for status in ["active", "ended", "paused", "transferred"]:
                count = await conversation_crud.count_by_status(status)
                status_counts[f"{status}_conversations"] = count

            stats = {
                "total_conversations": total,
                "active_conversations": active,
                "inactive_conversations": total - active,
                "average_messages_per_conversation": round(avg_messages, 2),
                "activation_rate": round((active / total * 100) if total > 0 else 0, 2),
                **status_counts
            }

            logger.info("Conversation statistics retrieved", **stats)
            return {
                "success": True,
                "status": "success",
                "message": "Conversation statistics retrieved successfully",
                "data": stats
            }

    except Exception as e:
        logger.error("Error getting Conversation statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Conversation statistics: {str(e)}"
        )


@router.get("/stats/daily", dependencies=[Depends(verify_admin_token)])
async def get_daily_conversation_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days to get statistics for")
):
    """
    Get daily conversation creation statistics.

    Returns the number of conversations created each day for the
    specified time period.

    Args:
        days (int): Number of days to include in statistics (1-30)

    Returns:
        Dict: Daily conversation creation statistics

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            daily_stats = await conversation_crud.get_daily_stats(days=days)

            logger.info("Daily conversation statistics retrieved", days=days, count=len(daily_stats))
            return {
                "success": True,
                "status": "success",
                "message": f"Daily conversation statistics for last {days} days retrieved successfully",
                "data": {
                    "daily_stats": daily_stats,
                    "total_days": len(daily_stats),
                    "period_days": days
                }
            }

    except Exception as e:
        logger.error("Error getting daily conversation statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve daily conversation statistics: {str(e)}"
        )


@router.get("/stats/by-bot", dependencies=[Depends(verify_admin_token)])
async def get_conversation_stats_by_bot():
    """
    Get conversation statistics grouped by bot.

    Provides statistics showing how many conversations each bot has handled,
    useful for understanding bot usage patterns.

    Returns:
        Dict: Conversation statistics grouped by bot

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            # Get bot statistics
            bot_crud = BotCRUD(session)
            bot_stats = await bot_crud.get_stats_by_platform()  # Reuse existing method

            logger.info("Conversation statistics by bot retrieved", count=len(bot_stats))
            return {
                "success": True,
                "status": "success",
                "message": "Conversation statistics by bot retrieved successfully",
                "data": {
                    "bot_stats": bot_stats,
                    "total_bots": len(bot_stats)
                }
            }

    except Exception as e:
        logger.error("Error getting conversation statistics by bot", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation statistics by bot: {str(e)}"
        )


# ===============================================
# MAINTENANCE AND CLEANUP
# ===============================================

@router.post("/cleanup/old", dependencies=[Depends(verify_admin_token)])
async def cleanup_old_conversations(
    days_old: int = Query(30, ge=1, le=365, description="Delete conversations older than N days")
):
    """
    Clean up old conversations.

    Permanently deletes conversations older than the specified number of days.
    Use with caution as this operation is irreversible.

    Args:
        days_old (int): Delete conversations older than this many days

    Returns:
        Dict: Number of conversations deleted

    Raises:
        HTTPException: 500 for internal errors
    """
    try:
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            deleted_count = await conversation_crud.cleanup_old_conversations(days_old=days_old)

            logger.info("Old conversations cleaned up", deleted_count=deleted_count, days_old=days_old)
            return {
                "success": True,
                "status": "success",
                "message": f"Cleaned up {deleted_count} conversations older than {days_old} days",
                "data": {
                    "deleted_count": deleted_count,
                    "days_old": days_old
                }
            }

    except Exception as e:
        logger.error("Error cleaning up old conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup old conversations: {str(e)}"
        )