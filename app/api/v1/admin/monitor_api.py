# import uuid
# import json
# from typing import Dict, Any, Optional, List
# from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
# from pydantic import BaseModel, Field
# import structlog
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.database import async_session_factory, get_db_session
# from app.models import Message
# from app.crud import CoreAICRUD, BotCRUD, ConversationCRUD, PancakeCRUD, PancakeActionCRUD
# from app.clients.ai_client import get_ai_service
# from sqlalchemy import select, desc, text, func
# from datetime import datetime, timedelta
# from app.api.dependencies import verify_admin_token

# logger = structlog.get_logger(__name__)

# # Admin router with authentication requirement
# router = APIRouter(prefix="/admin/chat")


# # ===============================================
# # PYDANTIC MODELS
# # ===============================================

# # Chat Stats
# class AdminChatStats(BaseModel):
#     total_conversations: int
#     total_messages: int
#     active_conversations: int
#     messages_today: int
#     avg_response_time_ms: Optional[float]


# class ConversationDetail(BaseModel):
#     id: str
#     status: str
#     context: Dict[str, Any]
#     message_count: int
#     created_at: str
#     updated_at: Optional[str]
#     last_message_content: Optional[str]
#     last_message_role: Optional[str]


# class AdminConversationList(BaseModel):
#     success: bool
#     conversations: List[ConversationDetail]
#     total_count: int
#     page: int
#     page_size: int

# # ===============================================
# # CHAT STATISTICS & CONVERSATIONS (existing)
# # ===============================================

# @router.get("/conversations", dependencies=[Depends(verify_admin_token)], response_model=AdminConversationList)
# async def list_conversations(
#     page: int = 1,
#     page_size: int = 20,
#     status: Optional[str] = None,
#     user_id: Optional[str] = None,
#     search: Optional[str] = None
# ):
#     """
#     List all conversations with admin filtering options.

#     Requires admin authentication.
#     """
#     try:
#         offset = (page - 1) * page_size

#         async with async_session_factory() as session:
#             # Build WHERE conditions
#             where_conditions = []
#             params = {}

#             if status:
#                 where_conditions.append("c.status = :status")
#                 params["status"] = status

#             if user_id:
#                 where_conditions.append("c.context::text LIKE :user_id")
#                 params["user_id"] = f"%{user_id}%"

#             if search:
#                 where_conditions.append("""
#                     (c.id::text LIKE :search OR
#                      c.context::text LIKE :search OR
#                      EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id AND m.content LIKE :search))
#                 """)
#                 params["search"] = f"%{search}%"

#             where_clause = ""
#             if where_conditions:
#                 where_clause = "WHERE " + " AND ".join(where_conditions)

#             # Get conversations with last message info
#             query = f"""
#                 SELECT
#                     c.id, c.status, c.context, c.created_at, c.updated_at,
#                     COUNT(m.id) as message_count,
#                     (SELECT content FROM messages m2 WHERE m2.conversation_id = c.id ORDER BY m2.created_at DESC LIMIT 1) as last_message_content,
#                     (SELECT message_role FROM messages m3 WHERE m3.conversation_id = c.id ORDER BY m3.created_at DESC LIMIT 1) as last_message_role
#                 FROM conversations c
#                 LEFT JOIN messages m ON m.conversation_id = c.id
#                 {where_clause}
#                 GROUP BY c.id, c.status, c.context, c.created_at, c.updated_at
#                 ORDER BY c.updated_at DESC
#                 LIMIT :limit OFFSET :offset
#             """

#             params.update({"limit": page_size, "offset": offset})

#             result = await session.execute(text(query), params)
#             rows = result.fetchall()

#             # Get total count
#             count_query = f"""
#                 SELECT COUNT(DISTINCT c.id) FROM conversations c
#                 LEFT JOIN messages m ON m.conversation_id = c.id
#                 {where_clause}
#             """

#             count_result = await session.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]})
#             total_count = count_result.scalar() or 0

#             # Format conversations
#             conversations = [
#                 ConversationDetail(
#                     id=str(row.id),
#                     status=row.status,
#                     context=json.loads(row.context) if row.context else {},
#                     message_count=row.message_count,
#                     created_at=row.created_at.isoformat(),
#                     updated_at=row.updated_at.isoformat() if row.updated_at else None,
#                     last_message_content=row.last_message_content,
#                     last_message_role=row.last_message_role
#                 )
#                 for row in rows
#             ]

#             return AdminConversationList(
#                 success=True,
#                 conversations=conversations,
#                 total_count=total_count,
#                 page=page,
#                 page_size=page_size
#             )

#     except Exception as e:
#         logger.error("Error listing conversations", error=str(e))
#         raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# @router.get("/conversations/{conversation_id}/details", dependencies=[Depends(verify_admin_token)])
# async def get_conversation_details(conversation_id: str):
#     """Get detailed conversation info including all messages for admin review."""
#     try:
#         # Validate conversation_id format
#         try:
#             conv_uuid = uuid.UUID(conversation_id)
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Invalid conversation_id format")

#         async with async_session_factory() as session:
#             conversation_crud = ConversationCRUD(session)

#             # Get conversation info
#             conversation = await conversation_crud.get_by_id(conv_uuid)
#             if not conversation:
#                 raise HTTPException(status_code=404, detail="Conversation not found")

#             # Get conversation messages
#             messages_list = await conversation_crud.get_conversation_messages(conv_uuid)

#             messages = [
#                 {
#                     "id": str(msg.id),
#                     "content": msg.content,
#                     "role": msg.message_role,
#                     "content_type": msg.content_type,
#                     "processing_time_ms": msg.processing_time_ms,
#                     "created_at": msg.created_at.isoformat()
#                 }
#                 for msg in messages_list
#             ]

#             return {
#                 "success": True,
#                 "conversation": {
#                     "id": conversation_id,
#                     "status": conversation.status,
#                     "context": conversation.context or {},
#                     "created_at": conversation.created_at.isoformat(),
#                     "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
#                     "message_count": len(messages)
#                 },
#                 "messages": messages
#             }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error("Error getting conversation details",
#                     conversation_id=conversation_id,
#                     error=str(e))
#         raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# @router.delete("/conversations/{conversation_id}", dependencies=[Depends(verify_admin_token)])
# async def delete_conversation(conversation_id: str):
#     """Delete a conversation and all its messages."""
#     try:
#         # Validate conversation_id format
#         try:
#             conv_uuid = uuid.UUID(conversation_id)
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Invalid conversation_id format")

#         async with async_session_factory() as session:
#             conversation_crud = ConversationCRUD(session)

#             # Check if conversation exists and delete it
#             deleted = await conversation_crud.delete(conv_uuid)
#             if not deleted:
#                 raise HTTPException(status_code=404, detail="Conversation not found")

#             logger.info("Conversation deleted by admin", conversation_id=conversation_id)

#             return {
#                 "success": True,
#                 "message": f"Conversation {conversation_id} deleted successfully"
#             }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error("Error deleting conversation",
#                     conversation_id=conversation_id,
#                     error=str(e))
#         raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")