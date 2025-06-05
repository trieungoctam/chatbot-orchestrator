from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import Dict, Any, Optional, List
import uuid
import time
import structlog

from app.services import get_message_handler, MessageHandler
from app.schemas.request import PancakeMessageRequest
from app.schemas.response import PancakeMessageResponse
from app.api.dependencies import verify_access

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat")

@router.post("/message", response_model=PancakeMessageResponse)
async def send_message(
    request: PancakeMessageRequest,
    _: bool = Depends(verify_access),
    message_handler: MessageHandler = Depends(get_message_handler)
):
    """
    Send a message through the enhanced message handling system with context chunking.

    This endpoint:
    1. Chunks old history to keep only recent messages within specified limits
    2. Checks for existing message locks and consolidates if needed
    3. Retrieves bot and AI configuration
    4. Starts background AI processing with chunked context
    5. Returns immediately with job tracking info

    Context Management:
    - max_context_messages: Limits the number of recent messages to keep (1-100, default: 20)
    - max_context_chars: Limits the total characters in context (1000-50000, default: 10000)
    - Older messages beyond these limits are automatically removed
    """

    try:
        # Generate message ID if not provided
        if not request.conversation_id:
            request.conversation_id = str(uuid.uuid4())

        logger.info("Message request with context limits",
                   conversation_id=request.conversation_id,
                   history_length=len(request.history),
                   history_preview=request.history[:100])

        # Process the message with context chunking
        result = await message_handler.handle_message_request(
            conversation_id=request.conversation_id,
            bot_id=request.bot_id,
            history=request.history,
            resources=request.resources,
        )

        return PancakeMessageResponse(**result)

    except Exception as e:
        logger.error("Message processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Message processing failed: {str(e)}")

@router.get("/context/limits")
async def get_context_limits():
    """
    Get recommended context limits for different use cases.
    """
    return {
        "limits": {
            "conservative": {
                "max_messages": 10,
                "max_chars": 5000,
                "description": "For simple conversations with limited context needs"
            },
            "standard": {
                "max_messages": 20,
                "max_chars": 10000,
                "description": "Default setting for most healthcare conversations"
            },
            "extended": {
                "max_messages": 50,
                "max_chars": 25000,
                "description": "For complex medical consultations requiring more context"
            },
            "maximum": {
                "max_messages": 100,
                "max_chars": 50000,
                "description": "Maximum supported context for comprehensive discussions"
            }
        },
        "recommendations": [
            "Use 'conservative' for simple symptom checking",
            "Use 'standard' for general medical conversations",
            "Use 'extended' for detailed consultations",
            "Use 'maximum' only when full conversation history is critical"
        ]
    }