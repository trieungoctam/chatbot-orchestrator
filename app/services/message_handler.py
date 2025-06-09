import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import structlog
import json
import time
import uuid
import re
import hashlib
import random

from app.core.redis_client import get_redis_client
from app.core.database import async_session_factory
from app.crud.bot_crud import BotCRUD
from app.crud.core_ai_crud import CoreAICRUD
from app.crud.platform_crud import PlatformCRUD
from app.crud.conversation_crud import ConversationCRUD
from app.utils.common import history_parser
from app.clients.core_ai_client import get_ai_service
from app.clients.platform_client import PlatformClient, get_platform_client
from app.schemas.request import UpdateConversationRequest

logger = structlog.get_logger(__name__)

# Constants
LOCK_TTL_SECONDS = 3600  # 1 hour
JOB_TTL_SECONDS = 3600   # 1 hour
CACHE_TTL_SECONDS = 3600 # 1 hour
WORKER_TIMEOUT_SECONDS = 10
CLEANUP_MAX_AGE_HOURS = 24
MAX_HISTORY_LENGTH = 10000


@dataclass
class LockData:
    """Lock data structure."""
    conversation_id: str
    history_hash: int
    created_at: float
    lock_id: int  # Changed from str to int for timestamp
    consolidated_count: int = 1
    updated_at: Optional[float] = None
    ai_job_id: Optional[str] = None
    previous_ai_job_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "history_hash": self.history_hash,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "lock_id": self.lock_id,
            "ai_job_id": self.ai_job_id,
            "previous_ai_job_id": self.previous_ai_job_id,
            "consolidated_count": self.consolidated_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LockData':
        """Create from dictionary."""
        return cls(
            conversation_id=data["conversation_id"],
            history_hash=data["history_hash"],
            created_at=data["created_at"],
            lock_id=data["lock_id"],
            consolidated_count=data.get("consolidated_count", 1),
            updated_at=data.get("updated_at"),
            ai_job_id=data.get("ai_job_id"),
            previous_ai_job_id=data.get("previous_ai_job_id")
        )

    @classmethod
    def generate_lock_id(cls) -> int:
        """Generate a new lock ID using hash-based approach with 1e9+7 for better distribution."""

        # Create unique data combining timestamp, random, and process info for uniqueness
        data = f"{time.time()}{random.randint(1, 1000000)}{id(cls)}"

        # Create hash and convert to integer
        hash_obj = hashlib.md5(data.encode())
        hash_int = int.from_bytes(hash_obj.digest(), 'big')

        # Apply modulo with large prime (1e9+7) for good distribution
        MOD = 10000007
        lock_id = (hash_int % MOD) + 1

        return lock_id


@dataclass
class JobData:
    """Job data structure."""
    job_id: str
    status: str
    created_at: float
    payload: Dict[str, Any]
    updated_at: Optional[float] = None
    processing_started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "payload": self.payload,
            "updated_at": self.updated_at,
            "processing_started_at": self.processing_started_at,
            "completed_at": self.completed_at,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobData':
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            status=data["status"],
            created_at=data["created_at"],
            payload=data["payload"],
            updated_at=data.get("updated_at"),
            processing_started_at=data.get("processing_started_at"),
            completed_at=data.get("completed_at"),
            error=data.get("error")
        )


class CacheProvider(ABC):
    """Abstract cache provider interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        pass

    @abstractmethod
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        pass


class RedisCacheProvider(CacheProvider):
    """Redis-based cache provider."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning("Redis get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value with optional TTL."""
        try:
            if ttl:
                result = await self.redis.set(key, value, ex=ttl)
            else:
                result = await self.redis.set(key, value)
            return bool(result)
        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.warning("Redis delete failed", key=key, error=str(e))
            return False

    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.warning("Redis keys failed", pattern=pattern, error=str(e))
            return []


class MemoryCacheProvider(CacheProvider):
    """In-memory fallback cache provider."""

    def __init__(self):
        self._cache = {}
        self._ttl_cache = {}

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        # Check TTL
        if key in self._ttl_cache and time.time() > self._ttl_cache[key]:
            self._cache.pop(key, None)
            self._ttl_cache.pop(key, None)
            return None

        return self._cache.get(key)

    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value with optional TTL."""
        self._cache[key] = value
        if ttl:
            self._ttl_cache[key] = time.time() + ttl
        return True

    async def delete(self, key: str) -> bool:
        """Delete key."""
        deleted = key in self._cache
        self._cache.pop(key, None)
        self._ttl_cache.pop(key, None)
        return deleted

    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        # Simple pattern matching for fallback
        import fnmatch
        return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]


class CacheManager:
    """Manages cache operations with fallback."""

    def __init__(self, redis_client=None):
        if redis_client:
            self.primary = RedisCacheProvider(redis_client)
        else:
            self.primary = None
        self.fallback = MemoryCacheProvider()

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value by key."""
        value = await self._get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in cache", key=key)
        return None

    async def set_json(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        """Set JSON value with optional TTL."""
        try:
            json_str = json.dumps(value)
            return await self._set(key, json_str, ttl)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to serialize JSON", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        success = False
        if self.primary:
            success = await self.primary.delete(key)
        # Always try fallback as well
        fallback_success = await self.fallback.delete(key)
        return success or fallback_success

    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        if self.primary:
            return await self.primary.keys(pattern)
        return await self.fallback.keys(pattern)

    async def _get(self, key: str) -> Optional[str]:
        """Get with fallback."""
        if self.primary:
            value = await self.primary.get(key)
            if value is not None:
                return value
        return await self.fallback.get(key)

    async def _set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set with fallback."""
        success = False
        if self.primary:
            success = await self.primary.set(key, value, ttl)
        # Always set in fallback as well
        fallback_success = await self.fallback.set(key, value, ttl)
        return success or fallback_success


class MessageLockManager:
    """Enhanced message lock manager with proper abstractions."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.lock_prefix = "msg_lock:"

    async def check_and_acquire_lock(
        self,
        conversation_id: str,
        history: str,
        resources: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if conversation needs lock and acquire if necessary."""
        lock_key = f"{self.lock_prefix}{conversation_id}"

        try:
            # Check for existing lock
            existing_lock_data = await self.cache.get_json(lock_key)
            existing_lock = LockData.from_dict(existing_lock_data) if existing_lock_data else None

            if existing_lock:
                return await self._handle_existing_lock(existing_lock, conversation_id, history, lock_key)
            else:
                return await self._acquire_new_lock(conversation_id, history, lock_key)

        except Exception as e:
            logger.error("Error in lock check and acquire", error=str(e))
            return await self._create_fallback_lock(conversation_id, history, lock_key)

    async def _handle_existing_lock(
        self,
        existing_lock: LockData,
        conversation_id: str,
        history: str,
        lock_key: str
    ) -> Dict[str, Any]:
        """Handle existing lock found."""
        logger.info("Existing lock found, cancelling current job and reprocessing",
                   conversation_id=conversation_id,
                   existing_ai_job_id=existing_lock.ai_job_id)

        updated_lock = LockData(
            conversation_id=conversation_id,
            history_hash=hash(history),
            created_at=existing_lock.created_at,
            updated_at=time.time(),
            lock_id=existing_lock.lock_id,
            previous_ai_job_id=existing_lock.ai_job_id,
            consolidated_count=existing_lock.consolidated_count + 1
        )

        await self.cache.set_json(lock_key, updated_lock.to_dict(), LOCK_TTL_SECONDS)

        return {
            "action": "lock_updated_cancel_and_reprocess",
            "should_call_ai": True,
            "should_cancel_previous": True,
            "previous_ai_job_id": existing_lock.ai_job_id,
            "consolidated_message_count": updated_lock.consolidated_count,
            "lock_data": {
                "lock_id": updated_lock.lock_id,
                "conversation_id": conversation_id,
                "updated": True
            }
        }

    async def _acquire_new_lock(self, conversation_id: str, history: str, lock_key: str) -> Dict[str, Any]:
        """Acquire new lock."""
        new_lock = LockData(
            conversation_id=conversation_id,
            history_hash=hash(history),
            created_at=time.time(),
            lock_id=LockData.generate_lock_id(),
            consolidated_count=1
        )

        success = await self.cache.set_json(lock_key, new_lock.to_dict(), LOCK_TTL_SECONDS)

        if success:
            return {
                "action": "lock_acquired",
                "should_call_ai": True,
                "should_cancel_previous": False,
                "consolidated_message_count": 1,
                "lock_data": {
                    "lock_id": new_lock.lock_id,
                    "conversation_id": conversation_id,
                    "updated": False
                }
            }
        else:
            return {
                "action": "lock_exists",
                "should_call_ai": False,
                "should_cancel_previous": False,
                "consolidated_message_count": 0,
                "lock_data": None
            }

    async def _create_fallback_lock(self, conversation_id: str, history: str, lock_key: str) -> Dict[str, Any]:
        """Create fallback lock on error."""
        fallback_lock = LockData(
            conversation_id=conversation_id,
            history_hash=hash(history),
            created_at=time.time(),
            lock_id=LockData.generate_lock_id(),
            consolidated_count=1
        )

        await self.cache.set_json(lock_key, fallback_lock.to_dict(), LOCK_TTL_SECONDS)

        return {
            "action": "lock_acquired_fallback",
            "should_call_ai": True,
            "should_cancel_previous": False,
            "consolidated_message_count": 1,
            "lock_data": {
                "lock_id": fallback_lock.lock_id,
                "conversation_id": conversation_id,
                "updated": False
            }
        }

    async def release_lock(self, conversation_id: str) -> bool:
        """Release conversation lock."""
        lock_key = f"{self.lock_prefix}{conversation_id}"
        return await self.cache.delete(lock_key)

    async def get_lock_info(self, conversation_id: str) -> Optional[LockData]:
        """Get lock information for conversation."""
        lock_key = f"{self.lock_prefix}{conversation_id}"
        lock_data = await self.cache.get_json(lock_key)
        return LockData.from_dict(lock_data) if lock_data else None

    async def update_lock_with_ai_job(self, conversation_id: str, ai_job_id: str) -> bool:
        """Update lock with AI job ID."""
        lock_key = f"{self.lock_prefix}{conversation_id}"

        try:
            lock_data = await self.cache.get_json(lock_key)
            if lock_data:
                lock = LockData.from_dict(lock_data)
                lock.ai_job_id = ai_job_id
                lock.updated_at = time.time()
                return await self.cache.set_json(lock_key, lock.to_dict(), LOCK_TTL_SECONDS)
            return False
        except Exception as e:
            logger.warning("Failed to update lock with AI job", error=str(e))
            return False


class BackgroundJobManager:
    """Enhanced background job manager with proper abstractions."""

    def __init__(self, cache_manager: CacheManager, parent_handler=None):
        self.cache = cache_manager
        self.job_prefix = "ai_job:"
        self.parent_handler = parent_handler
        self._worker_task = None
        self._worker_running = False
        self._processing_queue = asyncio.Queue()

    async def create_ai_processing_job(self, payload: Dict[str, Any]) -> str:
        """Create an AI processing job."""
        job_id = str(time.time())

        job = JobData(
            job_id=job_id,
            status="pending",
            created_at=time.time(),
            payload=payload
        )

        job_key = f"{self.job_prefix}{job_id}"
        await self.cache.set_json(job_key, job.to_dict(), JOB_TTL_SECONDS)

        # Queue the job for processing
        await self._queue_job_for_processing(job_id)
        return job_id

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job_key = f"{self.job_prefix}{job_id}"
        job_data = await self.cache.get_json(job_key)

        if job_data:
            return job_data

        return {
            "job_id": job_id,
            "status": "not_found",
            "error": "Job not found"
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        try:
            await self._update_job_status(job_id, "cancelled", {
                "cancelled_at": time.time(),
                "reason": "cancelled_by_user"
            })
            logger.info("Job cancelled successfully", job_id=job_id)
            return True
        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            return False

    async def _update_job_status(self, job_id: str, status: str, additional_data: Dict = None):
        """Update job status."""
        job_key = f"{self.job_prefix}{job_id}"

        try:
            job_data = await self.cache.get_json(job_key)
            if job_data:
                job = JobData.from_dict(job_data)
                job.status = status
                job.updated_at = time.time()

                if additional_data:
                    # Update the job data dict directly for additional fields
                    job_dict = job.to_dict()
                    job_dict.update(additional_data)
                    await self.cache.set_json(job_key, job_dict, JOB_TTL_SECONDS)
                else:
                    await self.cache.set_json(job_key, job.to_dict(), JOB_TTL_SECONDS)

                logger.info("Job status updated",
                           job_id=job_id,
                           status=status,
                           additional_data=additional_data)
        except Exception as e:
            logger.warning("Failed to update job status", job_id=job_id, error=str(e))

    async def _check_job_cancellation(self, job_id: str) -> bool:
        """Check if a job has been cancelled."""
        try:
            job_status = await self.get_job_status(job_id)
            return job_status.get("status") == "cancelled"
        except Exception as e:
            logger.warning("Failed to check job cancellation status", job_id=job_id, error=str(e))
            return False

    async def _process_ai_job(self, job_id: str):
        """Process AI job using real AI service."""
        job_key = f"{self.job_prefix}{job_id}"

        # Check if job was cancelled before processing
        if await self._check_job_cancellation(job_id):
            logger.info("Job was cancelled before processing started", job_id=job_id)
            return

        # Update status to processing
        await self._update_job_status(job_id, "processing", {
            "processing_started_at": time.time()
        })

        try:
            # Get job data
            job_data = await self.cache.get_json(job_key)
            if not job_data:
                await self._update_job_status(job_id, "failed", {
                    "error": "Job data not found",
                    "completed_at": time.time()
                })
                return

            # Check for cancellation after fetching job data
            if await self._check_job_cancellation(job_id):
                logger.info("Job was cancelled during data fetching", job_id=job_id)
                return

            # Process the job
            result = await self._execute_ai_processing(job_id, job_data)

            if not await self._check_job_cancellation(job_id):
                await self._handle_ai_result(job_id, job_data, result)

        except Exception as e:
            if not await self._check_job_cancellation(job_id):
                logger.error("AI job processing error", job_id=job_id, error=str(e))
                await self._update_job_status(job_id, "failed", {
                    "error": f"Job processing exception: {str(e)}",
                    "completed_at": time.time()
                })

    async def _execute_ai_processing(self, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI processing for the job."""
        payload = job_data.get("payload", {})
        conversation_id = payload.get("conversation_id")
        messages = payload.get("messages", [])
        bot_config = payload.get("bot_config", {})
        ai_config = payload.get("ai_config", {})
        resources = payload.get("resources", {})
        lock_id = payload.get("lock_id", "")

        ai_service = get_ai_service()

        # Final check for cancellation before AI processing
        if await self._check_job_cancellation(job_id):
            logger.info("Job was cancelled before AI processing", job_id=job_id)
            return {"success": False, "error": "Job cancelled"}

        # Process with AI service
        return await ai_service.process_job(
            job_id=job_id,
            conversation_id=conversation_id,
            messages=messages,
            context={
                "bot_config": bot_config,
                "ai_config": ai_config,
                "resources": resources,
                "lock_id": lock_id
            },
            core_ai_id=ai_config.get("core_ai_id")
        )

    async def _handle_ai_result(self, job_id: str, job_data: Dict[str, Any], ai_result: Dict[str, Any]):
        """Handle AI processing result."""
        if ai_result.get("success"):
            await self._handle_successful_ai_result(job_id, job_data, ai_result)
        else:
            await self._handle_failed_ai_result(job_id, ai_result)

    async def _handle_successful_ai_result(self, job_id: str, job_data: Dict[str, Any], ai_result: Dict[str, Any]):
        """Handle successful AI processing result."""
        payload = job_data.get("payload", {})
        conversation_id = payload.get("conversation_id")
        platform_conversation_id = payload.get("platform_conversation_id", "")
        platform_config = payload.get("platform_config", {})
        history = payload.get("history", "")
        # First, update job status to completed
        await self._update_job_status(job_id, "completed", {
            "ai_response": ai_result.get("data", {}),
            "ai_action": ai_result.get("action", ""),
            "processing_time_ms": ai_result.get("processing_time_ms"),
            "conversation_turns": ai_result.get("conversation_turns", 0),
            "completed_at": time.time()
        })

        logger.info("AI job completed successfully",
                   job_id=job_id,
                   conversation_id=conversation_id,
                   ai_action=ai_result.get("action", ""))

        # Note: History saving and lock removal now happens in platform actions before execution

        # Now execute platform actions (which will save history and remove lock first)
        logger.info("Starting platform actions - will save history and remove lock first",
                   job_id=job_id,
                   conversation_id=conversation_id,
                   ai_action=ai_result.get("action", ""))

        await self._handle_platform_actions(job_id, conversation_id, platform_conversation_id,
                                           platform_config, ai_result, history)

    async def _handle_failed_ai_result(self, job_id: str, ai_result: Dict[str, Any]):
        """Handle failed AI processing result."""
        await self._update_job_status(job_id, "failed", {
            "error": ai_result.get("error", "AI processing failed"),
            "ai_action": ai_result.get("action", ""),
            "processing_time_ms": ai_result.get("processing_time_ms"),
            "completed_at": time.time()
        })
        logger.error("AI job failed", job_id=job_id, error=ai_result.get("error"))

        # For failed processing, keep the lock active to allow conversation continuation
        try:
            # Extract conversation_id from job data if available
            job_data = await self.cache.get_json(f"{self.job_prefix}{job_id}")
            if job_data:
                payload = job_data.get("payload", {})
                conversation_id = payload.get("conversation_id")
                if conversation_id:
                    await self._update_lock_for_continuation(conversation_id, job_id, ai_result)
                    logger.info("Lock updated for conversation continuation after failed AI processing",
                               job_id=job_id,
                               conversation_id=conversation_id)
                else:
                    logger.warning("No conversation_id found in job payload for lock update",
                                 job_id=job_id)
            else:
                logger.warning("No job data found for lock update",
                             job_id=job_id)
        except Exception as e:
            logger.error("Failed to update lock for continuation after failure",
                        job_id=job_id,
                        error=str(e))

    async def _handle_platform_actions(
        self,
        job_id: str,
        conversation_id: str,
        platform_conversation_id: str,
        platform_config: Dict[str, Any],
        ai_result: Dict[str, Any],
        history: str
    ):
        """Handle platform actions after AI processing."""
        try:
            ai_action = ai_result.get("action", "")
            ai_response = ai_result.get("data", {})

            if ai_action == "OUT_OF_SCOPE":
                ai_action = "NOTIFY"

            platform_client = get_platform_client()
            platform_id = platform_config.get("id")

            logger.info("Starting platform history validation",
                       job_id=job_id,
                       conversation_id=conversation_id,
                       platform_id=platform_id)

            # Check for history updates
            latest_history = await platform_client.get_conversation_history(
                conversation_id=platform_conversation_id,
                platform_config=platform_config
            )

            new_history = latest_history.get("history", "")
            old_history = history

            # Handle None case for old_history and compare lengths safely
            if old_history is None:
                old_history = ""

            if new_history != old_history:
                # Handle updated history
                print("========== Cancel Job ==========")
                print("========== New Job ==========")
                await self._handle_history_update(job_id, conversation_id, new_history, latest_history)
                return

            # Here , save history to database
            try:
                await self.parent_handler._save_history_to_database_from_platform(conversation_id, platform_conversation_id, platform_config)
                logger.info("History saved to database before platform action execution",
                           job_id=job_id,
                           conversation_id=conversation_id,
                           ai_action=ai_action)
            except Exception as e:
                logger.error("Failed to save history to database before platform actions",
                            job_id=job_id,
                            conversation_id=conversation_id,
                            error=str(e))

            # Remove lock after saving history (before platform actions)
            try:
                await self.parent_handler._remove_lock_from_platform_actions(conversation_id, job_id, ai_action)
                logger.info("Lock removed before platform action execution",
                           job_id=job_id,
                           conversation_id=conversation_id,
                           ai_action=ai_action)
            except Exception as e:
                logger.error("Failed to remove lock before platform actions",
                            job_id=job_id,
                            conversation_id=conversation_id,
                            error=str(e))

            # Execute platform action
            await self.parent_handler._execute_platform_action(
                ai_action, ai_response, platform_conversation_id, platform_config, job_id, platform_client
            )

        except Exception as e:
            logger.error("Error during platform action execution",
                       job_id=job_id,
                       conversation_id=conversation_id,
                       error=str(e))
            await self._update_job_status(job_id, "completed_with_error", {
                "ai_action": ai_action,
                "platform_error": str(e),
                "completed_at": time.time()
            })

    async def _handle_history_update(
        self,
        job_id: str,
        conversation_id: str,
        new_history: str,
        latest_history: Dict[str, Any]
    ):
        """Handle platform history update."""
        logger.info("Platform history updated, proceeding with message request",
                   job_id=job_id,
                   conversation_id=conversation_id)

        resources = latest_history.get("resources", {})
        await self.parent_handler._set_cached_history(conversation_id, new_history)

        # Trigger new message handling
        bot_config = await self.parent_handler.bot_config_service.get_bot_config(conversation_id)
        await self.parent_handler.handle_message_request(
            conversation_id=conversation_id,
            bot_id=bot_config.get("bot_id"),
            history=new_history,
            resources=resources
        )

    async def start_background_worker(self):
        """Start background worker."""
        if self._worker_running:
            logger.warning("Background worker already running")
            logger.info("Background worker already running")
            return

        self._worker_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Background worker started")

    async def stop_background_worker(self):
        """Stop background worker."""
        if not self._worker_running:
            logger.warning("Background worker not running")
            return

        self._worker_running = False

        if self._worker_task:
            try:
                self._worker_task.cancel()
                await self._worker_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Error stopping background worker", error=str(e))
            finally:
                self._worker_task = None

        logger.info("Background worker stopped")

    async def _worker_loop(self):
        """Main worker loop that processes jobs from the queue."""
        logger.info("Background worker loop started")

        while self._worker_running:
            try:
                job_id = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=WORKER_TIMEOUT_SECONDS
                )

                if job_id:
                    await self._process_ai_job(job_id)
                    self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error("Error in worker loop", error=str(e))
                await asyncio.sleep(1)

        logger.info("Background worker loop stopped")

    async def _queue_job_for_processing(self, job_id: str):
        """Queue a job for background processing."""
        try:
            if self._worker_running:
                await self._processing_queue.put(job_id)
            else:
                # Auto-start worker if not running (self-healing)
                logger.warning("Background worker not running, attempting to start it", job_id=job_id)
                try:
                    await self.start_background_worker()
                    if self._worker_running:
                        await self._processing_queue.put(job_id)
                        logger.info("Background worker restarted and job queued", job_id=job_id)
                    else:
                        logger.error("Failed to restart background worker, processing job immediately", job_id=job_id)
                        asyncio.create_task(self._process_ai_job(job_id))
                except Exception as worker_start_error:
                    logger.error("Failed to start background worker",
                               job_id=job_id,
                               error=str(worker_start_error))
                    asyncio.create_task(self._process_ai_job(job_id))
        except Exception as e:
            logger.error("Failed to queue job", job_id=job_id, error=str(e))
            asyncio.create_task(self._process_ai_job(job_id))

    async def get_worker_status(self) -> Dict[str, Any]:
        """Get worker status."""
        return {
            "worker_running": self._worker_running,
            "worker_task_active": bool(self._worker_task and not self._worker_task.done()),
            "queue_size": self._processing_queue.qsize(),
            "status": "healthy" if self._worker_running else "stopped"
        }

    async def close(self):
        """Close job manager."""
        logger.info("Closing background job manager")
        await self.stop_background_worker()

        # Clear any remaining jobs in queue
        while not self._processing_queue.empty():
            try:
                self._processing_queue.get_nowait()
                self._processing_queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.info("Background job manager closed")


class BotConfigService:
    """Service for retrieving bot configuration."""

    async def get_bot_config(self, section_id: str) -> Dict[str, Any]:
        """Get bot configuration for conversation."""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)
                bot_crud = BotCRUD(session)

                conversation = await conversation_crud.get_by_id(section_id)
                if not conversation:
                    return await self._get_default_bot_config()

                bot = await bot_crud.get_by_id(conversation.bot_id)
                if not bot:
                    return await self._get_default_bot_config()

                return {
                    "bot_id": str(bot.id),
                    "name": bot.name,
                    "description": bot.description,
                    "language": bot.language,
                    "is_active": bot.is_active,
                    "core_ai_id": str(bot.core_ai_id),
                    "platform_id": str(bot.platform_id),
                    "meta_data": bot.meta_data
                }
        except Exception as e:
            logger.error("Error getting bot config", error=str(e))
            return await self._get_default_bot_config()

    async def _get_default_bot_config(self) -> Dict[str, Any]:
        """Get default bot configuration."""
        return {
            "bot_id": "default",
            "name": "Default Bot",
            "description": "Default bot configuration",
            "language": "vi",
            "is_active": True,
            "core_ai_id": "default",
            "platform_id": "default",
            "meta_data": {}
        }


class HistoryProcessor:
    """Handles history processing operations."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.history_cache_prefix = "processed_history:"

    async def cut_old_history(self, section_id: str, current_history: str) -> str:
        """Cut old history from new history and return only the new part."""
        try:
            old_history = await self.get_cached_history(section_id)
            if not old_history:
                old_history = await self._get_processed_history_from_db(section_id)
                print("####### old_history from db", old_history)

            if old_history:
                print("####### old_history", old_history)
                new_history_part = self._cut_history_string(current_history, old_history)
                print("####### new_history_part", new_history_part)
                await self.set_cached_history(section_id, current_history)

                return new_history_part
            else:
                return current_history

        except Exception as e:
            logger.warning("Failed to cut old history, using full history",
                          section_id=section_id, error=str(e))
            return current_history

    async def get_cached_history(self, conversation_id: str) -> Optional[str]:
        """Get cached processed history."""
        try:
            cache_key = f"{self.history_cache_prefix}{conversation_id}"
            cached_data = await self.cache.get_json(cache_key)

            if cached_data:
                return cached_data.get("history", "")
            return None

        except Exception as e:
            logger.warning("Failed to get cached history",
                          conversation_id=conversation_id, error=str(e))
            return None

    async def set_cached_history(self, conversation_id: str, history: str) -> bool:
        """Set cached history."""
        try:
            cache_key = f"{self.history_cache_prefix}{conversation_id}"
            cache_data = {
                "history": history,
                "processed_at": time.time(),
                "history_length": len(history)
            }
            return await self.cache.set_json(cache_key, cache_data, CACHE_TTL_SECONDS)

        except Exception as e:
            logger.error("Error setting cached history", error=str(e))
            return False

    async def _get_processed_history_from_db(self, conversation_id: str) -> Optional[str]:
        """Get last processed history from database."""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)
                conversation = await conversation_crud.get_by_id_simple(uuid.UUID(conversation_id))

                if conversation and conversation.history:
                    return conversation.history
                return None

        except Exception as e:
            logger.warning("Failed to get history from database",
                          conversation_id=conversation_id, error=str(e))
            return None

    def _cut_history_string(self, current_history: str, old_history: str) -> str:
        """Cut old history from current history using suffix-prefix matching algorithm."""
        try:
            if not old_history:
                return current_history

            # Case 1: Old history is completely contained in current history
            if old_history in current_history:
                old_end_position = current_history.find(old_history) + len(old_history)
                new_part = current_history[old_end_position:]  # Don't strip here to preserve intentional spaces
                return new_part

            # Case 2: Find the longest prefix of current_history that matches a suffix of old_history
            max_overlap_length = 0

            # Check all possible prefixes of current_history
            for i in range(1, len(current_history) + 1):
                prefix = current_history[:i]  # First i characters of current_history

                if old_history.endswith(prefix):
                    max_overlap_length = len(prefix)

            if max_overlap_length > 0:
                # Cut the matching prefix from the beginning of current_history
                new_part = current_history[max_overlap_length:]  # Don't strip to preserve spaces
                return new_part

            # Case 3: No overlap found, return entire current history
            return current_history

        except Exception as e:
            logger.warning("Failed to cut old history using suffix algorithm", error=str(e))
            return current_history

    def parse_history(self, history: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse and chunk history into structured messages."""
        try:
            if not history:
                return []

            message_data = []
            patterns = [
                (r'<USER>(.*?)</USER>', 'user'),
                (r'<BOT>(.*?)</BOT>', 'bot'),
                (r'<SALE>(.*?)</SALE>', 'sale')
            ]

            for pattern, role in patterns:
                for match in re.finditer(pattern, history, re.DOTALL):
                    message_data.append({
                        "role": role,
                        "content": match.group(1).strip(),
                        "timestamp": time.time(),
                        "position": match.start()
                    })

            # Sort by position and clean up
            message_data.sort(key=lambda x: x["position"])

            messages = []
            for msg in message_data:
                messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"],
                    "timestamp": msg["timestamp"]
                })

            return messages

        except Exception as e:
            logger.error("Error in history processing", error=str(e))
            # Fallback: truncate and return as single message
            truncated_history = history[-MAX_HISTORY_LENGTH:] if len(history) > MAX_HISTORY_LENGTH else history
            return [{"role": "user", "content": truncated_history, "timestamp": time.time()}]


class ConfigurationService:
    """Service for retrieving various configurations."""

    async def get_ai_config(self, core_ai_id: str) -> Dict[str, Any]:
        """Get AI core configuration."""
        try:
            async with async_session_factory() as session:
                core_ai_crud = CoreAICRUD(session)

                if core_ai_id and core_ai_id != "default":
                    core_ai = await core_ai_crud.get_by_id(uuid.UUID(core_ai_id))
                    if core_ai and core_ai.is_active:
                        return {
                            "core_ai_id": str(core_ai.id),
                            "name": core_ai.name,
                            "api_endpoint": core_ai.api_endpoint,
                            "auth_required": core_ai.auth_required,
                            "auth_token": core_ai.auth_token,
                            "timeout_seconds": core_ai.timeout_seconds,
                            "meta_data": core_ai.meta_data
                        }

                return self._get_default_ai_config()

        except Exception as e:
            logger.error("Error getting AI config", error=str(e))
            return self._get_default_ai_config()

    async def get_platform_config(self, platform_id: str) -> Dict[str, Any]:
        """Get platform configuration."""
        try:
            async with async_session_factory() as session:
                platform_crud = PlatformCRUD(session)

                if platform_id and platform_id != "default":
                    try:
                        platform = await platform_crud.get_by_id_with_actions(uuid.UUID(platform_id))
                        if platform and platform.is_active:
                            # Handle actions safely - they might be Pydantic models or dicts
                            actions = []
                            if platform.actions:
                                logger.debug("Processing platform actions",
                                           platform_id=platform_id,
                                           actions_count=len(platform.actions),
                                           actions_type=type(platform.actions).__name__)

                                for i, action in enumerate(platform.actions):
                                    logger.debug("Processing action",
                                               action_index=i,
                                               action_type=type(action).__name__,
                                               has_model_dump=hasattr(action, 'model_dump'),
                                               is_dict=isinstance(action, dict))

                                    try:
                                        if hasattr(action, 'model_dump'):
                                            # It's a Pydantic model
                                            action_dict = action.model_dump()
                                            actions.append(action_dict)
                                            logger.debug("Successfully converted Pydantic model to dict", action_index=i)
                                        elif isinstance(action, dict):
                                            # It's already a dictionary
                                            actions.append(action)
                                            logger.debug("Used existing dictionary", action_index=i)
                                        else:
                                            # Convert to dict if possible
                                            try:
                                                action_dict = dict(action)
                                                actions.append(action_dict)
                                                logger.debug("Successfully converted object to dict", action_index=i)
                                            except Exception as convert_error:
                                                logger.warning("Unable to convert action to dict",
                                                             action_index=i,
                                                             action=str(action),
                                                             error=str(convert_error))
                                                actions.append({})
                                    except Exception as action_error:
                                        logger.error("Error processing action",
                                                   action_index=i,
                                                   action_type=type(action).__name__,
                                                   error=str(action_error))
                                        # Add empty dict to prevent index issues
                                        actions.append({})

                                logger.debug("Finished processing actions",
                                           total_actions=len(actions),
                                           platform_id=platform_id)

                            return {
                                "id": str(platform.id),
                                "platform_id": str(platform.id),
                                "name": platform.name,
                                "description": platform.description,
                                "base_url": platform.base_url,
                                "auth_required": platform.auth_required,
                                "auth_token": platform.auth_token,
                                "rate_limit_per_minute": platform.rate_limit_per_minute,
                                "meta_data": platform.meta_data,
                                "actions": actions
                            }
                    except Exception as platform_retrieval_error:
                        logger.error("Error retrieving platform from database",
                                   platform_id=platform_id,
                                   error=str(platform_retrieval_error))
                        # Fall through to default config

                return self._get_default_platform_config()

        except Exception as e:
            logger.error("Error getting platform config",
                       platform_id=platform_id,
                       error=str(e))
            return self._get_default_platform_config()

    def _get_default_ai_config(self) -> Dict[str, Any]:
        """Get default AI configuration."""
        return {
            "core_ai_id": "default",
            "name": "Default AI",
            "api_endpoint": "http://localhost:8000",
            "auth_required": False,
            "timeout_seconds": 30,
            "meta_data": {}
        }

    def _get_default_platform_config(self) -> Dict[str, Any]:
        """Get default platform configuration."""
        return {
            "id": "default",
            "platform_id": "default",
            "name": "Default Platform",
            "description": "Default platform",
            "base_url": "http://localhost:8000",
            "auth_required": False,
            "rate_limit_per_minute": 60,
            "meta_data": {},
            "actions": []
        }


class MessageHandler:
    """Enhanced MessageHandler with improved architecture."""

    def __init__(self):
        self.cache_manager = None
        self.lock_manager = None
        self.background_job_manager = None
        self.bot_config_service = BotConfigService()
        self.history_processor = None
        self.config_service = ConfigurationService()
        self._initialized = False

    async def initialize(self):
        """Initialize all components."""
        if self._initialized:
            return

        try:
            # Initialize cache manager
            try:
                redis_client = await get_redis_client()
                self.cache_manager = CacheManager(redis_client)
                logger.info("MessageHandler Redis connection established")
            except Exception as redis_error:
                logger.warning("Redis connection failed, using fallback", error=str(redis_error))
                self.cache_manager = CacheManager(None)

            # Initialize all components
            self.lock_manager = MessageLockManager(self.cache_manager)
            self.background_job_manager = BackgroundJobManager(self.cache_manager, self)
            self.history_processor = HistoryProcessor(self.cache_manager)

            self._initialized = True
            logger.info("Enhanced message handler initialized successfully",
                       redis_available=bool(self.cache_manager.primary))

        except Exception as e:
            logger.error("Failed to initialize message handler", error=str(e))
            self._initialized = True  # Allow degraded mode

    async def handle_message_request(
        self,
        conversation_id: str,
        bot_id: str,
        history: str,
        resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Main entry point for message handling."""
        if not self._initialized:
            await self.initialize()

        logger.info("Handling message request",
                   bot_id=bot_id,
                   conversation_id=conversation_id,
                   history_length=len(history))

        try:
            # Get or create conversation
            section_id = await self._get_or_create_conversation(conversation_id, bot_id)

            # Process history
            effective_history = await self.history_processor.cut_old_history(section_id, history)

            if len(effective_history) != len(history):
                logger.info("Cut old history from new history",
                           section_id=section_id,
                           original_length=len(history),
                           effective_length=len(effective_history))

            # Get configurations
            bot_config = await self.bot_config_service.get_bot_config(section_id)
            ai_config = await self.config_service.get_ai_config(bot_config.get("core_ai_id"))
            platform_config = await self.config_service.get_platform_config(bot_config.get("platform_id"))

            # Parse messages
            parsed_messages = self.history_processor.parse_history(effective_history, section_id)
            logger.info("Parsed messages", parsed_messages=parsed_messages)
            print("Parsed messages", json.dumps(parsed_messages, indent=4))

            # Handle locking and job creation
            return await self._handle_locking_and_processing(
                section_id, conversation_id, effective_history, parsed_messages, history,
                bot_config, ai_config, platform_config, resources
            )

        except Exception as e:
            logger.error("Message handling failed",
                        conversation_id=conversation_id, error=str(e))
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "message": f"Message processing failed: {str(e)}"
            }

    async def _get_or_create_conversation(self, conversation_id: str, bot_id: str) -> str:
        """Get or create conversation and return section_id."""
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            conversation = await conversation_crud.get_by_conversation_id(conversation_id)

            if not conversation:
                conversation = await conversation_crud.create_conversation_by_bot_and_conversation_id(
                    uuid.UUID(bot_id), conversation_id
                )

            return str(conversation.id)

    async def _handle_locking_and_processing(
        self,
        section_id: str,
        conversation_id: str,
        effective_history: str,
        parsed_messages: List[Dict[str, Any]],
        history: str,
        bot_config: Dict[str, Any],
        ai_config: Dict[str, Any],
        platform_config: Dict[str, Any],
        resources: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle message locking and processing logic."""
        # Check lock and consolidate messages
        lock_result = await self.lock_manager.check_and_acquire_lock(
            conversation_id=section_id,
            history=effective_history,
            resources=resources
        )

        logger.info("Lock check completed",
                   action=lock_result["action"],
                   should_call_ai=lock_result["should_call_ai"],
                   parsed_message_count=len(parsed_messages))

        # Handle job cancellation if needed
        if lock_result.get("should_cancel_previous") and lock_result.get("previous_ai_job_id"):
            await self._cancel_previous_job(lock_result["previous_ai_job_id"], section_id)

        if lock_result["should_call_ai"]:
            return await self._start_ai_processing_flow(
                section_id, conversation_id, lock_result,
                bot_config, ai_config, platform_config,
                parsed_messages, history, resources
            )
        else:
            return {
                "success": True,
                "status": "locked",
                "action": lock_result["action"],
                "message": "Message is being processed by another request"
            }

    async def _cancel_previous_job(self, previous_job_id: str, section_id: str):
        """Cancel previous job."""
        try:
            await self.background_job_manager.cancel_job(previous_job_id)
            logger.info("Previous AI job cancelled",
                       cancelled_job_id=previous_job_id,
                       conversation_id=section_id)
        except Exception as cancel_error:
            logger.warning("Failed to cancel previous job",
                          job_id=previous_job_id, error=str(cancel_error))

    async def _start_ai_processing_flow(
        self,
        section_id: str,
        conversation_id: str,
        lock_result: Dict[str, Any],
        bot_config: Dict[str, Any],
        ai_config: Dict[str, Any],
        platform_config: Dict[str, Any],
        parsed_messages: List[Dict[str, Any]],
        history: str,
        resources: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Start AI processing flow."""
        # await 2 seconds
        await asyncio.sleep(2)

        # Start AI processing
        ai_job_id = await self._start_ai_processing(
            section_id, conversation_id, lock_result["lock_data"],
            bot_config, ai_config, platform_config,
            parsed_messages, history, resources
        )

        # Update lock with job ID
        await self.lock_manager.update_lock_with_ai_job(section_id, ai_job_id)

        action_description = "Message received and AI processing started"
        if lock_result.get("should_cancel_previous"):
            action_description = "Previous job cancelled, reprocessing with new history"

        return {
            "success": True,
            "status": "ai_processing_started",
            "action": lock_result["action"],
            "ai_job_id": ai_job_id,
            "lock_id": lock_result["lock_data"]["lock_id"],
            "consolidated_messages": len(parsed_messages),
            "consolidated_count": lock_result.get("consolidated_message_count", 1),
            "bot_name": bot_config["name"],
            "message": action_description,
            "cancelled_previous_job": lock_result.get("previous_ai_job_id"),
            "reprocessing": lock_result.get("should_cancel_previous", False)
        }

    # Legacy method aliases for backward compatibility
    async def _get_cached_history(self, conversation_id: str) -> Optional[str]:
        """Legacy method for backward compatibility."""
        return await self.history_processor.get_cached_history(conversation_id)

    async def _set_cached_history(self, conversation_id: str, history: str) -> bool:
        """Legacy method for backward compatibility."""
        return await self.history_processor.set_cached_history(conversation_id, history)

    async def _save_history_to_database_from_platform(
        self,
        conversation_id: str,
        platform_conversation_id: str = None,
        platform_config: Dict[str, Any] = None
    ):
        """Save current history to database from platform actions context."""
        try:
            # Get current cached history
            current_history = await self.history_processor.get_cached_history(conversation_id)

            if not current_history and platform_conversation_id and platform_config:
                logger.info("No cached history found, attempting to fetch from platform",
                           conversation_id=conversation_id,
                           platform_conversation_id=platform_conversation_id)

                # Try to get history from platform as fallback
                try:
                    # Get platform client and fetch history
                    platform_client = get_platform_client()

                    history_result = await platform_client.get_conversation_history(
                        conversation_id=platform_conversation_id,
                        platform_config=platform_config
                    )

                    if history_result:
                        if history_result.get("history"):  # History is present and not empty
                            current_history = history_result["history"]
                            logger.info("Successfully fetched history from platform as fallback",
                                       conversation_id=conversation_id,
                                       platform_conversation_id=platform_conversation_id,
                                       history_length=len(current_history))

                            # Cache the history for future use
                            await self.history_processor.set_cached_history(conversation_id, current_history)
                        else:  # History key exists but is empty
                            logger.info("Platform returned empty history as fallback",
                                       conversation_id=conversation_id,
                                       platform_conversation_id=platform_conversation_id,
                                       platform_result=history_result)
                    else:
                        logger.warning("Failed to fetch history from platform as fallback",
                                     conversation_id=conversation_id,
                                     platform_conversation_id=platform_conversation_id,
                                     platform_result=history_result)

                except Exception as platform_error:
                    logger.warning("Error fetching history from platform as fallback",
                                 conversation_id=conversation_id,
                                 platform_conversation_id=platform_conversation_id,
                                 error=str(platform_error))
            elif not current_history:
                logger.info("No cached history found, attempting to fetch from platform",
                           conversation_id=conversation_id)

                # Try to get history from platform as fallback without provided context
                try:
                    # Get bot config to find platform
                    bot_config = await self.bot_config_service.get_bot_config(conversation_id)
                    platform_config_fallback = await self.config_service.get_platform_config(bot_config.get("platform_id"))

                    # Get platform conversation ID (assuming it's the same as conversation_id for now)
                    platform_conversation_id_fallback = platform_conversation_id

                    # Get platform client and fetch history
                    platform_client = get_platform_client()

                    history_result = await platform_client.get_conversation_history(
                        conversation_id=platform_conversation_id_fallback,
                        platform_config=platform_config_fallback
                    )

                    if history_result.get("success"):
                        if history_result.get("history"):  # History is present and not empty
                            current_history = history_result["history"]
                            logger.info("Successfully fetched history from platform as fallback (without context)",
                                       conversation_id=conversation_id,
                                       history_length=len(current_history))

                            # Cache the history for future use
                            await self.history_processor.set_cached_history(conversation_id, current_history)
                        else:  # History key exists but is empty
                            logger.info("Platform returned empty history as fallback (without context)",
                                       conversation_id=conversation_id,
                                       platform_result=history_result)
                    else:
                        logger.warning("Failed to fetch history from platform as fallback (without context)",
                                     conversation_id=conversation_id,
                                     platform_result=history_result)

                except Exception as platform_error:
                    logger.warning("Error fetching history from platform as fallback (without context)",
                                 conversation_id=conversation_id,
                                 error=str(platform_error))

            if not current_history:
                logger.warning("No history available to save to database (cached or platform)",
                             conversation_id=conversation_id)
                return

            # Update conversation history in database
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)

                # Create proper update request object
                update_request = UpdateConversationRequest(history=current_history)

                updated = await conversation_crud.update(
                    uuid.UUID(conversation_id),
                    update_request
                )

                if updated:
                    logger.info("Successfully saved history to database from platform context",
                               conversation_id=conversation_id,
                               history_length=len(current_history))
                else:
                    logger.warning("Failed to update conversation history from platform context",
                                 conversation_id=conversation_id)

        except Exception as e:
            logger.error("Error saving history to database from platform context",
                        conversation_id=conversation_id,
                        error=str(e))
            raise

    async def _remove_lock_from_platform_actions(self, conversation_id: str, job_id: str, ai_action: str):
        """Remove lock from platform actions context."""
        try:
            # Get current lock info for logging purposes
            lock_data = await self.lock_manager.get_lock_info(conversation_id)

            if not lock_data:
                logger.warning("No lock found to remove from platform actions context",
                             conversation_id=conversation_id,
                             job_id=job_id,
                             ai_action=ai_action)
                return

            # Log the lock information before removal
            logger.info("Removing lock from platform actions context",
                       conversation_id=conversation_id,
                       job_id=job_id,
                       ai_action=ai_action,
                       lock_id=lock_data.lock_id,
                       lock_created_at=lock_data.created_at,
                       processing_duration_seconds=time.time() - lock_data.created_at)

            # Remove the lock
            success = await self.lock_manager.release_lock(conversation_id)

            if success:
                logger.info("Lock successfully removed from platform actions context",
                           conversation_id=conversation_id,
                           job_id=job_id,
                           ai_action=ai_action,
                           lock_id=lock_data.lock_id)
            else:
                logger.warning("Failed to remove lock from platform actions - may have already been removed",
                             conversation_id=conversation_id,
                             job_id=job_id,
                             ai_action=ai_action,
                             lock_id=lock_data.lock_id)

        except Exception as e:
            logger.error("Error removing lock from platform actions context",
                        conversation_id=conversation_id,
                        job_id=job_id,
                        ai_action=ai_action,
                        error=str(e))
            raise

    # Public interface methods
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job processing status."""
        if not self._initialized:
            await self.initialize()
        return await self.background_job_manager.get_job_status(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job."""
        if not self._initialized:
            await self.initialize()
        return await self.background_job_manager.cancel_job(job_id)

    async def get_conversation_lock_info(self, conversation_id: str) -> Optional[Dict]:
        """Get current lock information for conversation."""
        if not self._initialized:
            await self.initialize()
        lock_data = await self.lock_manager.get_lock_info(conversation_id)
        return lock_data.to_dict() if lock_data else None

    async def release_conversation_lock(self, conversation_id: str) -> bool:
        """Manually release conversation lock."""
        if not self._initialized:
            await self.initialize()
        return await self.lock_manager.release_lock(conversation_id)

    async def _start_ai_processing(
        self,
        section_id: str,
        conversation_id: str,
        lock_data: Dict[str, Any],
        bot_config: Dict[str, Any],
        ai_config: Dict[str, Any],
        platform_config: Dict[str, Any],
        messages: List[Dict[str, Any]],
        history: str,
        resources: Optional[Dict[str, Any]]
    ) -> str:
        """Start background AI processing job."""
        ai_job_payload = {
            "conversation_id": section_id,
            "platform_conversation_id": conversation_id,
            "lock_id": lock_data["lock_id"],
            "messages": messages,
            "bot_config": bot_config,
            "ai_config": ai_config,
            "platform_config": platform_config,
            "resources": resources or {},
            "history": history
        }

        ai_job_id = await self.background_job_manager.create_ai_processing_job(ai_job_payload)

        logger.info("AI processing job created",
                   conversation_id=section_id,
                   ai_job_id=ai_job_id,
                   message_count=len(messages))

        return ai_job_id

    async def get_handler_status(self) -> Dict[str, Any]:
        """Get overall handler status."""
        if not self._initialized:
            return {
                "initialized": False,
                "components": {}
            }

        worker_status = await self.background_job_manager.get_worker_status()

        return {
            "initialized": self._initialized,
            "components": {
                "cache_manager": bool(self.cache_manager),
                "redis_connected": bool(self.cache_manager.primary) if self.cache_manager else False,
                "lock_manager": bool(self.lock_manager),
                "background_job_manager": worker_status
            },
            "status": "healthy" if all([
                self.lock_manager,
                worker_status.get("status") == "healthy"
            ]) else "degraded"
        }

    async def start_background_processing(self):
        """Start background job processing worker."""
        if not self._initialized:
            await self.initialize()

        logger.info("Starting background processing worker")
        await self.background_job_manager.start_background_worker()

    async def stop_background_processing(self):
        """Stop background job processing worker."""
        if self.background_job_manager:
            logger.info("Stopping background processing worker")
            await self.background_job_manager.stop_background_worker()

    async def cleanup_old_locks(self, max_age_hours: int = CLEANUP_MAX_AGE_HOURS) -> int:
        """Clean up old message locks."""
        if not self._initialized:
            await self.initialize()

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0

            # Get all lock keys
            lock_pattern = f"{self.lock_manager.lock_prefix}*"
            lock_keys = await self.cache_manager.keys(lock_pattern)

            for key in lock_keys:
                try:
                    lock_data = await self.cache_manager.get_json(key)
                    if lock_data:
                        created_at = lock_data.get("created_at", 0)
                        if current_time - created_at > max_age_seconds:
                            await self.cache_manager.delete(key)
                            cleaned_count += 1
                    else:
                        # Remove invalid lock data
                        await self.cache_manager.delete(key)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning("Error processing lock for cleanup", lock_key=key, error=str(e))
                    await self.cache_manager.delete(key)
                    cleaned_count += 1

            logger.info("Cleaned up old locks", count=cleaned_count)
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup old locks", error=str(e))
            return 0

    async def cleanup_old_jobs(self, max_age_hours: int = CLEANUP_MAX_AGE_HOURS) -> int:
        """Cleanup old jobs older than max_age_hours."""
        try:
            cleanup_count = 0
            cutoff_time = time.time() - (max_age_hours * 3600)

            # Get all job keys
            pattern = f"{self.background_job_manager.job_prefix}*"
            keys = await self.cache_manager.keys(pattern)

            for key in keys:
                try:
                    job_data = await self.cache_manager.get_json(key)
                    if job_data:
                        created_at = job_data.get("created_at", 0)
                        if created_at < cutoff_time:
                            await self.cache_manager.delete(key)
                            cleanup_count += 1
                    else:
                        # Delete corrupted job data
                        await self.cache_manager.delete(key)
                        cleanup_count += 1
                except Exception as e:
                    logger.warning("Error processing job for cleanup",
                                 job_key=key, error=str(e))
                    await self.cache_manager.delete(key)
                    cleanup_count += 1

            logger.info("Job cleanup completed",
                       cleanup_count=cleanup_count,
                       max_age_hours=max_age_hours)

            return cleanup_count

        except Exception as e:
            logger.error("Error during job cleanup", error=str(e))
            return 0

    async def _execute_platform_action(
        self,
        ai_action: str,
        ai_response: Dict[str, Any],
        conversation_id: str,
        platform_config: Dict[str, Any],
        job_id: str,
        platform_client: PlatformClient = None
    ):
        """Execute the AI action through the platform."""
        try:
            platform_id = platform_config.get("platform_id") or platform_config.get("id")
            platform_name = platform_config.get("name", "Unknown Platform")

            logger.info("Executing platform action",
                       job_id=job_id,
                       conversation_id=conversation_id,
                       ai_action=ai_action,
                       platform_id=platform_id,
                       platform_name=platform_name)

            action_executed = False
            platform_actions = platform_config.get("actions", [])

            # Build actions map
            actions_map = {}
            for action in platform_actions:
                actions_map[action.get("name")] = {
                    "path": action.get("path"),
                    "method": action.get("method"),
                    "meta_data": action.get("meta_data")
                }

            platform_action = actions_map.get(ai_action)

            if platform_action:
                path = platform_action.get("path")
                method = platform_action.get("method")
                meta_data = platform_action.get("meta_data")
                url = f"{platform_config.get('base_url')}{path}"

                await platform_client.execute_platform_action(
                    platform_config,
                    url,
                    method,
                    meta_data,
                    conversation_id,
                    ai_response,
                    ai_action
                )

                action_executed = True
            else:
                logger.warning("Unknown AI action type",
                             job_id=job_id,
                             conversation_id=conversation_id,
                             ai_action=ai_action,
                             platform_name=platform_name)

            # Update job status
            if action_executed:
                await self.background_job_manager._update_job_status(job_id, "completed", {
                    "ai_action": ai_action,
                    "platform_action_executed": True,
                    "platform_name": platform_name,
                    "completed_at": time.time()
                })
                logger.info("Platform action execution completed",
                           job_id=job_id,
                           ai_action=ai_action)
            else:
                await self.background_job_manager._update_job_status(job_id, "completed", {
                    "ai_action": ai_action,
                    "platform_action_executed": False,
                    "platform_name": platform_name,
                    "note": "Action logged but not executed (implementation pending)",
                    "completed_at": time.time()
                })

        except Exception as e:
            logger.error("Error executing platform action",
                        job_id=job_id,
                        conversation_id=conversation_id,
                        ai_action=ai_action,
                        error=str(e))

            await self.background_job_manager._update_job_status(job_id, "failed", {
                "error": f"Platform action execution failed: {str(e)}",
                "ai_action": ai_action,
                "completed_at": time.time()
            })

    async def close(self):
        """Clean up all resources."""
        logger.info("Closing enhanced message handler")

        if self.background_job_manager:
            await self.background_job_manager.close()

        self._initialized = False
        logger.info("Enhanced message handler closed")

    async def _remove_lock_after_completion(self, conversation_id: str, job_id: str, status: str, ai_result: Dict[str, Any]):
        """Remove lock after AI job completion (success or failure)."""
        try:
            # Get current lock info for logging purposes
            lock_data = await self.lock_manager.get_lock_info(conversation_id)

            if not lock_data:
                logger.warning("No lock found to remove after completion",
                             conversation_id=conversation_id,
                             job_id=job_id,
                             status=status)
                return

            # Log the lock information before removal
            logger.info("Removing lock after AI job completion",
                       conversation_id=conversation_id,
                       job_id=job_id,
                       status=status,
                       lock_id=lock_data.lock_id,
                       ai_action=ai_result.get("action", ""),
                       lock_created_at=lock_data.created_at,
                       processing_duration_seconds=time.time() - lock_data.created_at)

            # Remove the lock
            success = await self.lock_manager.release_lock(conversation_id)

            if success:
                logger.info("Lock successfully removed after AI processing",
                           conversation_id=conversation_id,
                           job_id=job_id,
                           status=status,
                           lock_id=lock_data.lock_id)
            else:
                logger.warning("Failed to remove lock - may have already been removed",
                             conversation_id=conversation_id,
                             job_id=job_id,
                             status=status,
                             lock_id=lock_data.lock_id)

        except Exception as e:
            logger.error("Error removing lock after completion",
                        conversation_id=conversation_id,
                        job_id=job_id,
                        status=status,
                        error=str(e))
            raise

    async def _update_lock_for_continuation(self, conversation_id: str, job_id: str, ai_result: Dict[str, Any]):
        """Update lock to allow conversation continuation after AI job failure."""
        try:
            # Get current lock info
            lock_data = await self.lock_manager.get_lock_info(conversation_id)

            if not lock_data:
                logger.warning("No lock found to update for continuation",
                             conversation_id=conversation_id,
                             job_id=job_id)
                return

            # Update lock to mark it as ready for retry/continuation
            lock_key = f"{self.lock_manager.lock_prefix}{conversation_id}"

            # Create updated lock that allows continuation
            updated_lock = LockData(
                conversation_id=lock_data.conversation_id,
                history_hash=lock_data.history_hash,
                created_at=lock_data.created_at,
                lock_id=LockData.generate_lock_id(),  # Generate new lock_id for retry
                consolidated_count=1,  # Reset count for new processing attempt
                updated_at=time.time(),
                ai_job_id=None,  # Clear failed job_id
                previous_ai_job_id=job_id  # Track the failed job
            )

            # Add failure information to lock data
            lock_dict = updated_lock.to_dict()
            lock_dict.update({
                "processing_status": "ready_for_retry",
                "last_ai_action": ai_result.get("action", ""),
                "last_failure_reason": ai_result.get("error", "Unknown error"),
                "last_failure_at": time.time(),
                "failed_job_id": job_id
            })

            await self.cache_manager.set_json(
                lock_key,
                lock_dict,
                LOCK_TTL_SECONDS
            )

            logger.info("Lock updated for conversation continuation",
                       conversation_id=conversation_id,
                       job_id=job_id,
                       new_lock_id=updated_lock.lock_id,
                       old_lock_id=lock_data.lock_id,
                       failure_reason=ai_result.get("error", "Unknown"))

        except Exception as e:
            logger.error("Error updating lock for continuation",
                        conversation_id=conversation_id,
                        job_id=job_id,
                        error=str(e))
            raise