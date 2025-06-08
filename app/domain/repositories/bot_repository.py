"""
Bot Repository Interface - Domain Layer
Defines contract for bot data persistence
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.entities.bot import Bot, BotStatus, BotType


class IBotRepository(ABC):
    """
    Bot Repository Interface

    Defines all data access operations for Bot entities
    Following Repository pattern to keep domain layer pure
    """

    @abstractmethod
    async def create(self, bot: Bot) -> Bot:
        """Create new bot"""
        pass

    @abstractmethod
    async def get_by_id(self, bot_id: UUID) -> Optional[Bot]:
        """Get bot by ID"""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Bot]:
        """Get bot by name"""
        pass

    @abstractmethod
    async def get_by_platform_bot_id(self, platform: str, platform_bot_id: str) -> Optional[Bot]:
        """Get bot by platform-specific ID"""
        pass

    @abstractmethod
    async def update(self, bot: Bot) -> Bot:
        """Update existing bot"""
        pass

    @abstractmethod
    async def delete(self, bot_id: UUID) -> bool:
        """Delete bot (soft delete)"""
        pass

    @abstractmethod
    async def list_by_status(self, status: BotStatus, limit: int = 100, offset: int = 0) -> List[Bot]:
        """List bots by status"""
        pass

    @abstractmethod
    async def list_by_type(self, bot_type: BotType, limit: int = 100, offset: int = 0) -> List[Bot]:
        """List bots by type"""
        pass

    @abstractmethod
    async def list_active_bots(self, limit: int = 100, offset: int = 0) -> List[Bot]:
        """List all active bots"""
        pass

    @abstractmethod
    async def search_bots(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Bot]:
        """Search bots by query with filters"""
        pass

    @abstractmethod
    async def count_by_status(self, status: BotStatus) -> int:
        """Count bots by status"""
        pass

    @abstractmethod
    async def get_bot_metrics(self, bot_id: UUID) -> Dict[str, Any]:
        """Get bot performance metrics"""
        pass

    @abstractmethod
    async def get_overloaded_bots(self, threshold: float = 0.9) -> List[Bot]:
        """Get bots that are overloaded (above threshold)"""
        pass