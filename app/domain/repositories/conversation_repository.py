"""
Conversation Repository Interface - Domain Layer
Defines contract for conversation data persistence
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.domain.entities.conversation import Conversation, ConversationStatus, ConversationPriority


class IConversationRepository(ABC):
    """
    Conversation Repository Interface

    Defines all data access operations for Conversation entities
    """

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Create new conversation"""
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by internal ID"""
        pass

    @abstractmethod
    async def get_by_external_id(self, external_id: str) -> Optional[Conversation]:
        """Get conversation by external conversation ID"""
        pass

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Update existing conversation"""
        pass

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> bool:
        """Delete conversation (soft delete)"""
        pass

    @abstractmethod
    async def list_by_bot_id(self, bot_id: UUID, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations by bot"""
        pass

    @abstractmethod
    async def list_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations by user"""
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: ConversationStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[Conversation]:
        """List conversations by status"""
        pass

    @abstractmethod
    async def list_by_priority(
        self,
        priority: ConversationPriority,
        limit: int = 100,
        offset: int = 0
    ) -> List[Conversation]:
        """List conversations by priority"""
        pass

    @abstractmethod
    async def list_active_conversations(
        self,
        bot_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Conversation]:
        """List active conversations, optionally filtered by bot"""
        pass

    @abstractmethod
    async def list_escalated_conversations(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations that need human attention"""
        pass

    @abstractmethod
    async def list_timed_out_conversations(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations that have timed out"""
        pass

    @abstractmethod
    async def search_conversations(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Conversation]:
        """Search conversations by content or metadata"""
        pass

    @abstractmethod
    async def count_by_status(self, status: ConversationStatus) -> int:
        """Count conversations by status"""
        pass

    @abstractmethod
    async def count_by_bot(self, bot_id: UUID) -> int:
        """Count conversations for specific bot"""
        pass

    @abstractmethod
    async def get_conversation_metrics(
        self,
        conversation_id: UUID
    ) -> Dict[str, Any]:
        """Get conversation performance metrics"""
        pass

    @abstractmethod
    async def get_bot_conversation_stats(
        self,
        bot_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get conversation statistics for bot in date range"""
        pass