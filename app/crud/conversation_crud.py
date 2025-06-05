"""
Conversation CRUD Operations Module

This module provides comprehensive CRUD (Create, Read, Update, Delete) operations
for the Conversation and Message models, which manage chat conversations and messages
in the chatbot orchestrator system.

Dependencies:
- SQLAlchemy with async support for database operations
- Conversation, Message, Bot models from app.models

Author: Generated for Chatbot System Microservice Architecture
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, desc, and_, or_
from sqlalchemy.orm import selectinload, joinedload
import uuid
from datetime import datetime, timedelta

from app.models import Conversation, Message, Bot
from app.schemas.request import CreateConversationRequest, UpdateConversationRequest, CreateMessageRequest, UpdateMessageRequest
from app.schemas.response import (
    ConversationResponse, CreateConversationResponse, UpdateConversationResponse, ConversationListResponse,
    MessageResponse, CreateMessageResponse, UpdateMessageResponse, MessageListResponse
)


class ConversationCRUD:
    """CRUD operations for Conversation model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, conversation_data: CreateConversationRequest) -> ConversationResponse:
        """Create a new Conversation."""
        # Validate bot exists
        bot = await self.db.get(Bot, uuid.UUID(conversation_data.bot_id))
        if not bot or not bot.is_active:
            raise ValueError("Invalid or inactive bot_id")

        data = conversation_data.model_dump()
        data['bot_id'] = uuid.UUID(data['bot_id'])

        conversation = Conversation(**data)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        response_data = ConversationResponse(
            id=str(conversation.id),
            conversation_id=str(conversation.conversation_id),
            bot_id=str(conversation.bot_id),
            status=conversation.status,
            context=conversation.context,
            history=conversation.history,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

        return response_data

    async def create_conversation_by_bot_and_conversation_id(self, bot_id: uuid.UUID, conversation_id: str) -> ConversationResponse:
        """Create a new Conversation by Bot and Conversation ID."""
        conversation = Conversation(
            conversation_id=conversation_id,
            bot_id=bot_id,
            status="active",
            history=""
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse(
            id=str(conversation.id),
            conversation_id=str(conversation.conversation_id),
            bot_id=str(conversation.bot_id),
            status=conversation.status,
            context=conversation.context,
            history=conversation.history,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    async def get_by_conversation_id(self, conversation_id: str) -> Optional[ConversationResponse]:
        """Get Conversation by Conversation ID."""
        stmt = select(Conversation).where(Conversation.conversation_id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation:
            return ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
        return None

    async def get_by_id(self, conversation_id: uuid.UUID) -> Optional[ConversationResponse]:
        """Get Conversation by ID with all relationships."""
        stmt = (
            select(Conversation)
            # .options(
            #     selectinload(Conversation.bot),
            #     selectinload(Conversation.messages)
            # )
            .where(Conversation.id == conversation_id)
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            return ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
        return None

    async def get_by_id_simple(self, conversation_id: uuid.UUID) -> Optional[ConversationResponse]:
        """Get Conversation by ID without relationships (for better performance)."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            return ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
        return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ConversationResponse]:
        """Get all Conversations with pagination."""
        stmt = (
            select(Conversation)
            # .options(selectinload(Conversation.bot))
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def get_active(self, skip: int = 0, limit: int = 100) -> List[ConversationResponse]:
        """Get all active Conversations."""
        stmt = (
            select(Conversation)
            # .options(selectinload(Conversation.bot))
            .where(Conversation.is_active == True)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def get_by_bot(self, bot_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[ConversationResponse]:
        """Get Conversations by Bot."""
        stmt = (
            select(Conversation)
            # .options(selectinload(Conversation.bot))
            .where(Conversation.bot_id == bot_id)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[ConversationResponse]:
        """Get Conversations by status."""
        stmt = (
            select(Conversation)
            .where(Conversation.status == status)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def get_recent(self, hours: int = 24, skip: int = 0, limit: int = 100) -> List[ConversationResponse]:
        """Get recent Conversations within specified hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Conversation)
            .where(Conversation.updated_at >= since)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def get_with_message_count_range(self, min_count: int, max_count: int = None) -> List[ConversationResponse]:
        """Get Conversations with message count in range."""
        conditions = [Conversation.message_count >= min_count]
        if max_count:
            conditions.append(Conversation.message_count <= max_count)

        stmt = (
            select(Conversation)
            .where(and_(*conditions))
            .order_by(desc(Conversation.updated_at))
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        conversation_responses = []
        for conversation in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conversation.id),
                conversation_id=str(conversation.conversation_id),
                bot_id=str(conversation.bot_id),
                status=conversation.status,
                context=conversation.context,
                history=conversation.history,
                message_count=conversation.message_count,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            ))

        return conversation_responses

    async def update(self, conversation_id: uuid.UUID, conversation_data: UpdateConversationRequest) -> Optional[ConversationResponse]:
        """Update Conversation."""
        update_data = {k: v for k, v in conversation_data.model_dump(exclude_unset=True).items()
                      if v is not None and k not in ['id', 'created_at']}

        if 'bot_id' in update_data:
            bot = await self.db.get(Bot, uuid.UUID(update_data["bot_id"]))
            if not bot or not bot.is_active:
                raise ValueError("Invalid or inactive bot_id")
            update_data['bot_id'] = uuid.UUID(update_data['bot_id'])

        if not update_data:
            existing_conversation = await self.get_by_id(conversation_id)
            if existing_conversation:
                return existing_conversation
            return None

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(**update_data)
            .returning(Conversation)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_conversation = result.scalar_one_or_none()
        if updated_conversation:
            await self.db.refresh(updated_conversation)
            response_data = ConversationResponse(
                id=str(updated_conversation.id),
                conversation_id=str(updated_conversation.conversation_id),
                bot_id=str(updated_conversation.bot_id),
                status=updated_conversation.status,
                context=updated_conversation.context,
                history=updated_conversation.history,
                message_count=updated_conversation.message_count,
                created_at=updated_conversation.created_at,
                updated_at=updated_conversation.updated_at
            )
            return response_data
        return None

    async def update_message_count(self, conversation_id: uuid.UUID) -> Optional[ConversationResponse]:
        """Update message count for a conversation."""
        count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        result = await self.db.execute(count_stmt)
        actual_count = result.scalar()

        update_request = UpdateConversationRequest(message_count=actual_count)
        result = await self.update(conversation_id, update_request)
        return result

    async def update_status(self, conversation_id: uuid.UUID, status: str) -> bool:
        """Update conversation status."""
        update_request = UpdateConversationRequest(status=status)
        result = await self.update(conversation_id, update_request)
        return result is not None

    async def add_context(self, conversation_id: uuid.UUID, context_data: dict) -> bool:
        """Add or update context data for conversation."""
        conversation = await self.get_by_id_simple(conversation_id)
        if not conversation:
            return False

        current_context = conversation.context or {}
        current_context.update(context_data)

        update_request = UpdateConversationRequest(context=current_context)
        result = await self.update(conversation_id, update_request)
        return result is not None

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        """Delete Conversation."""
        stmt = delete(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def deactivate(self, conversation_id: uuid.UUID) -> bool:
        """Deactivate Conversation instead of deleting."""
        deactivate_request = UpdateConversationRequest(is_active=False)
        result = await self.update(conversation_id, deactivate_request)
        return result is not None

    async def activate(self, conversation_id: uuid.UUID) -> bool:
        """Activate Conversation."""
        activate_request = UpdateConversationRequest(is_active=True)
        result = await self.update(conversation_id, activate_request)
        return result is not None

    async def end_conversation(self, conversation_id: uuid.UUID) -> bool:
        """End a conversation (set status to 'ended')."""
        return await self.update_status(conversation_id, "ended")

    async def pause_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Pause a conversation."""
        return await self.update_status(conversation_id, "paused")

    async def resume_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Resume a paused conversation."""
        return await self.update_status(conversation_id, "active")

    async def get_conversation_messages(self, conversation_id: uuid.UUID, limit: int = 50) -> List[MessageResponse]:
        """Get messages for a conversation."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        message_responses = []
        for message in messages:
            message_responses.append(MessageResponse(
                id=str(message.id),
                conversation_id=str(message.conversation_id),
                content=message.content,
                message_role=message.message_role,
                content_type=message.content_type,
                created_at=message.created_at,
                updated_at=message.updated_at
            ))

        return message_responses

    async def search_by_context(self, key: str, value: str) -> List[ConversationResponse]:
        """Search conversations by context data."""
        # This is a simplified search - in production you might want to use proper JSON queries
        stmt = (
            select(Conversation)
            .where(Conversation.context.contains({key: value}))
            .order_by(desc(Conversation.updated_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_orphaned_conversations(self) -> List[Conversation]:
        """Get conversations without a bot (orphaned)."""
        stmt = (
            select(Conversation)
            .where(Conversation.bot_id.is_(None))
            .order_by(desc(Conversation.updated_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def cleanup_old_conversations(self, days_old: int = 30) -> int:
        """Delete conversations older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        stmt = delete(Conversation).where(Conversation.created_at < cutoff_date)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    # Statistics Methods
    async def count_total(self) -> int:
        """Count total Conversations."""
        stmt = select(func.count(Conversation.id))
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_active(self) -> int:
        """Count active Conversations."""
        stmt = select(func.count(Conversation.id)).where(Conversation.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_by_status(self, status: str) -> int:
        """Count Conversations by status."""
        stmt = select(func.count(Conversation.id)).where(Conversation.status == status)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_by_bot(self, bot_id: uuid.UUID) -> int:
        """Count Conversations by Bot."""
        stmt = select(func.count(Conversation.id)).where(Conversation.bot_id == bot_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_avg_message_count(self) -> float:
        """Get average message count across all conversations."""
        stmt = select(func.avg(Conversation.message_count))
        result = await self.db.execute(stmt)
        avg = result.scalar()
        return float(avg) if avg else 0.0

    async def get_daily_stats(self, days: int = 7) -> List[dict]:
        """Get daily conversation statistics for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                func.date(Conversation.created_at).label('date'),
                func.count(Conversation.id).label('count')
            )
            .where(Conversation.created_at >= since)
            .group_by(func.date(Conversation.created_at))
            .order_by(func.date(Conversation.created_at))
        )

        result = await self.db.execute(stmt)
        return [{"date": row.date.isoformat(), "count": row.count} for row in result]


class MessageCRUD:
    """CRUD operations for Message model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, message_data: CreateMessageRequest) -> MessageResponse:
        """Create a new Message."""
        # Validate conversation exists
        conversation = await self.db.get(Conversation, uuid.UUID(message_data.conversation_id))
        if not conversation:
            raise ValueError("Invalid conversation_id")

        data = message_data.model_dump()
        data['conversation_id'] = uuid.UUID(data['conversation_id'])

        message = Message(**data)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        # Update conversation message count
        conversation_crud = ConversationCRUD(self.db)
        await conversation_crud.update_message_count(uuid.UUID(message_data.conversation_id))

        response_data = MessageResponse(
            id=str(message.id),
            conversation_id=str(message.conversation_id),
            content=message.content,
            message_role=message.message_role,
            content_type=message.content_type,
            created_at=message.created_at,
            updated_at=message.updated_at
        )

        return response_data

    async def get_by_id(self, message_id: uuid.UUID) -> Optional[MessageResponse]:
        """Get Message by ID."""
        stmt = select(Message).where(Message.id == message_id)
        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if message:
            return MessageResponse(
                id=str(message.id),
                conversation_id=str(message.conversation_id),
                content=message.content,
                message_role=message.message_role,
                content_type=message.content_type,
                created_at=message.created_at,
                updated_at=message.updated_at
            )
        return None

    async def update(self, message_id: uuid.UUID, message_data: UpdateMessageRequest) -> Optional[MessageResponse]:
        """Update Message."""
        update_data = {k: v for k, v in message_data.model_dump(exclude_unset=True).items()
                      if v is not None and k not in ['id', 'created_at']}

        if 'conversation_id' in update_data:
            conversation = await self.db.get(Conversation, uuid.UUID(update_data["conversation_id"]))
            if not conversation:
                raise ValueError("Invalid conversation_id")
            update_data['conversation_id'] = uuid.UUID(update_data['conversation_id'])

        if not update_data:
            existing_message = await self.get_by_id(message_id)
            if existing_message:
                return existing_message
            return None

        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(**update_data)
            .returning(Message)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_message = result.scalar_one_or_none()
        if updated_message:
            await self.db.refresh(updated_message)
            response_data = MessageResponse(
                id=str(updated_message.id),
                conversation_id=str(updated_message.conversation_id),
                content=updated_message.content,
                message_role=updated_message.message_role,
                content_type=updated_message.content_type,
                created_at=updated_message.created_at,
                updated_at=updated_message.updated_at
            )
            return response_data
        return None

    async def delete(self, message_id: uuid.UUID) -> bool:
        """Delete Message."""
        # Get message to update conversation count after deletion
        message = await self.get_by_id(message_id)
        if not message:
            return False

        stmt = delete(Message).where(Message.id == message_id)
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            # Update conversation message count
            conversation_crud = ConversationCRUD(self.db)
            await conversation_crud.update_message_count(uuid.UUID(message.conversation_id))
            return True
        return False
