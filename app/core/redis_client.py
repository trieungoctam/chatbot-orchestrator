import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis
import structlog

from app.core.settings import settings

logger = structlog.get_logger(__name__)

class RedisConversationState:
    """Redis-backed conversation state management"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.key_prefix = "conv_state:"
        self.lock_prefix = "conv_lock:"
        # Use TTL from centralized settings instead of hard-coded value
        self.default_ttl = settings.CONVERSATION_STATE_TTL

    async def connect(self):
        """Connect to Redis"""
        try:
            # Use computed Redis URL from settings
            print(settings.redis_url_computed)
            self.redis = redis.from_url(
                settings.redis_url_computed,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis connection established", url=settings.redis_url_computed)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    def _get_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation state"""
        return f"{self.key_prefix}{conversation_id}"

    def _get_lock_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation lock"""
        return f"{self.lock_prefix}{conversation_id}"

    async def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation state from Redis"""
        try:
            key = self._get_key(conversation_id)
            data = await self.redis.get(key)

            if data:
                state = json.loads(data)
                # Convert timestamp strings back to floats
                if 'last_message_timestamp' in state:
                    state['last_message_timestamp'] = float(state['last_message_timestamp'])
                return state
            return None

        except Exception as e:
            logger.error("Failed to get conversation state",
                        conversation_id=conversation_id, error=str(e))
            return None

    async def set_conversation_state(
        self,
        conversation_id: str,
        state: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Set conversation state in Redis"""
        try:
            key = self._get_key(conversation_id)

            # Ensure timestamp is serializable
            if 'last_message_timestamp' in state:
                state['last_message_timestamp'] = float(state['last_message_timestamp'])

            data = json.dumps(state, default=str)
            await self.redis.set(key, data, ex=ttl or self.default_ttl)

            logger.debug("Conversation state saved", conversation_id=conversation_id)
            return True

        except Exception as e:
            logger.error("Failed to set conversation state",
                        conversation_id=conversation_id, error=str(e))
            return False

    async def delete_conversation_state(self, conversation_id: str) -> bool:
        """Delete conversation state from Redis"""
        try:
            key = self._get_key(conversation_id)
            deleted = await self.redis.delete(key)

            if deleted:
                logger.info("Conversation state deleted", conversation_id=conversation_id)
                return True
            return False

        except Exception as e:
            logger.error("Failed to delete conversation state",
                        conversation_id=conversation_id, error=str(e))
            return False

    async def acquire_lock(
        self,
        conversation_id: str,
        timeout: Optional[int] = None
    ) -> bool:
        """Acquire distributed lock for conversation processing"""
        try:
            lock_key = self._get_lock_key(conversation_id)
            lock_value = f"{conversation_id}:{datetime.utcnow().isoformat()}"

            # Use processing lock TTL from settings if no timeout specified
            lock_timeout = timeout or settings.PROCESSING_LOCK_TTL

            # Try to acquire lock with timeout
            acquired = await self.redis.set(
                lock_key,
                lock_value,
                ex=lock_timeout,
                nx=True
            )

            if acquired:
                logger.debug("Lock acquired", conversation_id=conversation_id, timeout=lock_timeout)
                return True
            else:
                logger.debug("Lock already exists", conversation_id=conversation_id)
                return False

        except Exception as e:
            logger.error("Failed to acquire lock",
                        conversation_id=conversation_id, error=str(e))
            return False

    async def release_lock(self, conversation_id: str) -> bool:
        """Release distributed lock for conversation"""
        try:
            lock_key = self._get_lock_key(conversation_id)
            deleted = await self.redis.delete(lock_key)

            if deleted:
                logger.debug("Lock released", conversation_id=conversation_id)
                return True
            return False

        except Exception as e:
            logger.error("Failed to release lock",
                        conversation_id=conversation_id, error=str(e))
            return False

    async def get_all_conversation_ids(self) -> List[str]:
        """Get all active conversation IDs"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)

            # Extract conversation IDs from keys
            conversation_ids = [
                key.replace(self.key_prefix, "")
                for key in keys
            ]

            return conversation_ids

        except Exception as e:
            logger.error("Failed to get conversation IDs", error=str(e))
            return []

    async def cleanup_old_conversations(self, max_age_hours: Optional[int] = None) -> int:
        """Clean up old conversation states"""
        try:
            conversation_ids = await self.get_all_conversation_ids()
            cleaned_count = 0
            # Use MAX_CONVERSATION_AGE_HOURS from settings if not specified
            max_age = max_age_hours or settings.MAX_CONVERSATION_AGE_HOURS
            cutoff_time = datetime.utcnow().timestamp() - (max_age * 3600)

            for conv_id in conversation_ids:
                state = await self.get_conversation_state(conv_id)
                if state and state.get('last_message_timestamp', 0) < cutoff_time:
                    await self.delete_conversation_state(conv_id)
                    cleaned_count += 1

            logger.info("Cleaned up old conversations",
                       cleaned_count=cleaned_count,
                       max_age_hours=max_age)
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup old conversations", error=str(e))
            return 0

# Global Redis instance
_redis_conversation_state = RedisConversationState()

async def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return _redis_conversation_state.redis