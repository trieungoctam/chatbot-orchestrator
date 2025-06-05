import asyncio
import time
import uuid
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.redis_client import get_redis_client
from app.core.database import async_session_factory
from app.crud.bot_crud import BotCRUD
from app.crud.core_ai_crud import CoreAICRUD
from app.crud.platform_crud import PlatformCRUD
from app.crud.conversation_crud import ConversationCRUD
from app.utils.common import history_parser
from app.clients.core_ai_client import get_ai_service

logger = structlog.get_logger(__name__)


class MessageLockManager:
    """Simple message lock manager for preventing race conditions"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.lock_prefix = "msg_lock:"
        self.lock_ttl = 3600  # 1 hour
        self._fallback_locks = {}  # In-memory fallback for testing

    async def check_and_acquire_lock(
        self,
        conversation_id: str,
        history: str,
        resources: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if conversation needs lock and acquire if necessary"""
        lock_key = f"{self.lock_prefix}{conversation_id}"

        try:
            # First check if lock already exists
            existing_lock = None
            if self.redis:
                lock_data = await self.redis.get(lock_key)
                if lock_data:
                    try:
                        existing_lock = json.loads(lock_data)
                    except json.JSONDecodeError:
                        existing_lock = None
            else:
                # Fallback to in-memory locks
                existing_lock = self._fallback_locks.get(lock_key)

            if existing_lock:
                # Lock exists - need to cancel current job and reprocess with new history
                logger.info("Existing lock found, cancelling current job and reprocessing",
                           conversation_id=conversation_id,
                           existing_ai_job_id=existing_lock.get("ai_job_id"))

                updated_lock_data = {
                    "conversation_id": conversation_id,
                    "history_hash": hash(history),
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "lock_id": existing_lock.get("lock_id"),
                    "previous_ai_job_id": existing_lock.get("ai_job_id"),  # Track old job for cancellation
                    "consolidated_count": existing_lock.get("consolidated_count", 0) + 1
                }

                # Update the lock with new data
                try:
                    if self.redis:
                        await self.redis.set(lock_key, json.dumps(updated_lock_data), ex=self.lock_ttl)
                    else:
                        self._fallback_locks[lock_key] = updated_lock_data
                except Exception as e:
                    logger.warning("Failed to update lock, using fallback", error=str(e))
                    self._fallback_locks[lock_key] = updated_lock_data

                return {
                    "action": "lock_updated_cancel_and_reprocess",
                    "should_call_ai": True,
                    "should_cancel_previous": True,
                    "previous_ai_job_id": existing_lock.get("ai_job_id"),
                    "consolidated_message_count": updated_lock_data["consolidated_count"],
                    "lock_data": {
                        "lock_id": updated_lock_data["lock_id"],
                        "conversation_id": conversation_id,
                        "updated": True
                    }
                }
            else:
                # No existing lock - acquire new lock
                new_lock_id = str(uuid.uuid4())
                lock_data = {
                    "conversation_id": conversation_id,
                    "history_hash": hash(history),
                    "created_at": time.time(),
                    "lock_id": new_lock_id,
                    "consolidated_count": 1
                }

                try:
                    if self.redis:
                        # Try to acquire lock via Redis
                        lock_acquired = await self.redis.set(
                            lock_key,
                            json.dumps(lock_data),
                            ex=self.lock_ttl,
                            nx=True
                        )
                    else:
                        # Fallback to in-memory locks for testing
                        self._fallback_locks[lock_key] = lock_data
                        lock_acquired = True
                except Exception as e:
                    logger.warning("Redis operation failed, using fallback", error=str(e))
                    # Fallback to in-memory locks
                    self._fallback_locks[lock_key] = lock_data
                    lock_acquired = True

                if lock_acquired:
                    return {
                        "action": "lock_acquired",
                        "should_call_ai": True,
                        "should_cancel_previous": False,
                        "consolidated_message_count": 1,
                        "lock_data": {
                            "lock_id": new_lock_id,
                            "conversation_id": conversation_id,
                            "updated": False
                        }
                    }
                else:
                    # This shouldn't happen given our logic above, but just in case
                    return {
                        "action": "lock_exists",
                        "should_call_ai": False,
                        "should_cancel_previous": False,
                        "consolidated_message_count": 0,
                        "lock_data": None
                    }

        except Exception as e:
            logger.error("Error in lock check and acquire", error=str(e))
            # On error, try to acquire a simple lock
            new_lock_id = str(uuid.uuid4())
            fallback_lock_data = {
                "conversation_id": conversation_id,
                "history_hash": hash(history),
                "created_at": time.time(),
                "lock_id": new_lock_id,
                "consolidated_count": 1,
                "error_fallback": True
            }
            self._fallback_locks[lock_key] = fallback_lock_data

            return {
                "action": "lock_acquired_fallback",
                "should_call_ai": True,
                "should_cancel_previous": False,
                "consolidated_message_count": 1,
                "lock_data": {
                    "lock_id": new_lock_id,
                    "conversation_id": conversation_id,
                    "updated": False
                }
            }

    async def release_lock(self, conversation_id: str) -> bool:
        """Release conversation lock"""
        lock_key = f"{self.lock_prefix}{conversation_id}"
        try:
            if self.redis:
                result = await self.redis.delete(lock_key)
                return bool(result)
            else:
                # Fallback to in-memory locks
                return self._fallback_locks.pop(lock_key, None) is not None
        except Exception as e:
            logger.warning("Redis delete failed, using fallback", error=str(e))
            return self._fallback_locks.pop(lock_key, None) is not None

    async def get_lock_info(self, conversation_id: str) -> Optional[Dict]:
        """Get lock information for conversation"""
        lock_key = f"{self.lock_prefix}{conversation_id}"
        try:
            if self.redis:
                lock_data = await self.redis.get(lock_key)
                if lock_data:
                    try:
                        return json.loads(lock_data)
                    except json.JSONDecodeError:
                        return None
            else:
                # Fallback to in-memory locks
                return self._fallback_locks.get(lock_key)
        except Exception as e:
            logger.warning("Redis get failed, using fallback", error=str(e))
            return self._fallback_locks.get(lock_key)
        return None

    async def update_lock_with_ai_job(self, conversation_id: str, ai_job_id: str):
        """Update lock with AI job ID"""
        lock_key = f"{self.lock_prefix}{conversation_id}"
        try:
            if self.redis:
                lock_data = await self.redis.get(lock_key)
                if lock_data:
                    try:
                        data = json.loads(lock_data)
                        data["ai_job_id"] = ai_job_id
                        await self.redis.set(lock_key, json.dumps(data), ex=self.lock_ttl)
                    except json.JSONDecodeError:
                        pass
            else:
                # Fallback to in-memory locks
                if lock_key in self._fallback_locks:
                    self._fallback_locks[lock_key]["ai_job_id"] = ai_job_id
        except Exception as e:
            logger.warning("Redis update failed, using fallback", error=str(e))
            if lock_key in self._fallback_locks:
                self._fallback_locks[lock_key]["ai_job_id"] = ai_job_id


class BackgroundJobManager:
    """Simple background job manager for AI processing"""

    def __init__(self):
        self.redis = None
        self.job_prefix = "ai_job:"
        self.job_ttl = 3600  # 1 hour
        self._fallback_jobs = {}  # In-memory fallback for testing

    async def initialize(self):
        """Initialize job manager"""
        try:
            self.redis = await get_redis_client()
            logger.info("Background job manager initialized with Redis")
        except Exception as e:
            logger.warning("Redis connection failed, using fallback", error=str(e))
            self.redis = None
            logger.info("Background job manager initialized with fallback")

    async def create_ai_processing_job(self, payload: Dict[str, Any]) -> str:
        """Create an AI processing job"""
        job_id = str(uuid.uuid4())
        job_key = f"{self.job_prefix}{job_id}"

        job_data = {
            "job_id": job_id,
            "status": "pending",
            "created_at": time.time(),
            "payload": payload
        }

        try:
            if self.redis:
                await self.redis.set(job_key, json.dumps(job_data), ex=self.job_ttl)
            else:
                # Fallback to in-memory storage
                self._fallback_jobs[job_key] = job_data
        except Exception as e:
            logger.warning("Redis job creation failed, using fallback", error=str(e))
            self._fallback_jobs[job_key] = job_data

        # Start AI processing (in real implementation, this would queue to worker)
        asyncio.create_task(self._process_ai_job(job_id))

        return job_id

    async def _process_ai_job(self, job_id: str):
        """Process AI job using real AI service"""
        job_key = f"{self.job_prefix}{job_id}"

        # Update status to processing
        await self._update_job_status(job_id, "processing")

        try:
            # Get job data to extract payload
            job_data = None
            if self.redis:
                data = await self.redis.get(job_key)
                if data:
                    job_data = json.loads(data)
            else:
                job_data = self._fallback_jobs.get(job_key)

            if not job_data:
                await self._update_job_status(job_id, "failed", {
                    "error": "Job data not found",
                    "completed_at": time.time()
                })
                return

            payload = job_data.get("payload", {})
            conversation_id = payload.get("conversation_id")
            messages = payload.get("messages", [])
            bot_config = payload.get("bot_config", {})
            ai_config = payload.get("ai_config", {})

            # Get AI service instance
            ai_service = get_ai_service()

            # Process the job using real AI service with message array
            ai_result = await ai_service.process_job(
                job_id=job_id,
                conversation_id=conversation_id,
                messages=messages,  # Pass messages array directly
                context={
                    "bot_config": bot_config,
                    "ai_config": ai_config,
                    "resources": payload.get("resources", {})
                },
                core_ai_id=ai_config.get("core_ai_id")
            )

            # Update status based on AI processing result
            if ai_result.get("success"):
                await self._update_job_status(job_id, "completed", {
                    "ai_response": ai_result.get("response", ""),
                    "ai_actions": ai_result.get("actions", []),
                    "ai_intent": ai_result.get("intent"),
                    "ai_confidence": ai_result.get("confidence"),
                    "ai_provider": ai_result.get("ai_provider"),
                    "processing_time_ms": ai_result.get("processing_time_ms"),
                    "conversation_turns": ai_result.get("conversation_turns", 0),
                    "completed_at": time.time()
                })
                logger.info("AI job completed successfully",
                           job_id=job_id,
                           conversation_id=conversation_id,
                           ai_provider=ai_result.get("ai_provider"),
                           conversation_turns=ai_result.get("conversation_turns"))
            else:
                await self._update_job_status(job_id, "failed", {
                    "error": ai_result.get("error", "AI processing failed"),
                    "ai_provider": ai_result.get("ai_provider"),
                    "processing_time_ms": ai_result.get("processing_time_ms"),
                    "completed_at": time.time()
                })
                logger.error("AI job failed",
                            job_id=job_id,
                            conversation_id=conversation_id,
                            error=ai_result.get("error"))

        except Exception as e:
            logger.error("AI job processing error",
                        job_id=job_id,
                        error=str(e))
            await self._update_job_status(job_id, "failed", {
                "error": f"Job processing exception: {str(e)}",
                "completed_at": time.time()
            })

    async def _update_job_status(self, job_id: str, status: str, additional_data: Dict = None):
        """Update job status"""
        job_key = f"{self.job_prefix}{job_id}"

        try:
            if self.redis:
                job_data = await self.redis.get(job_key)
                if job_data:
                    try:
                        data = json.loads(job_data)
                        data["status"] = status
                        data["updated_at"] = time.time()
                        if additional_data:
                            data.update(additional_data)
                        await self.redis.set(job_key, json.dumps(data), ex=self.job_ttl)
                    except json.JSONDecodeError:
                        pass
            else:
                # Fallback to in-memory storage
                if job_key in self._fallback_jobs:
                    data = self._fallback_jobs[job_key]
                    data["status"] = status
                    data["updated_at"] = time.time()
                    if additional_data:
                        data.update(additional_data)
        except Exception as e:
            logger.warning("Redis job update failed, using fallback", error=str(e))
            if job_key in self._fallback_jobs:
                data = self._fallback_jobs[job_key]
                data["status"] = status
                data["updated_at"] = time.time()
                if additional_data:
                    data.update(additional_data)

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        job_key = f"{self.job_prefix}{job_id}"

        try:
            if self.redis:
                job_data = await self.redis.get(job_key)
                if job_data:
                    try:
                        return json.loads(job_data)
                    except json.JSONDecodeError:
                        pass
            else:
                # Fallback to in-memory storage
                return self._fallback_jobs.get(job_key, {
                    "job_id": job_id,
                    "status": "not_found",
                    "error": "Job not found"
                })
        except Exception as e:
            logger.warning("Redis job status failed, using fallback", error=str(e))
            return self._fallback_jobs.get(job_key, {
                "job_id": job_id,
                "status": "not_found",
                "error": "Job not found"
            })

        return {
            "job_id": job_id,
            "status": "not_found",
            "error": "Job not found"
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        await self._update_job_status(job_id, "cancelled")
        return True

    async def get_worker_status(self) -> Dict[str, Any]:
        """Get worker status"""
        return {
            "redis_connected": bool(self.redis),
            "status": "healthy",
            "active_jobs": len(self._fallback_jobs) if not self.redis else 0
        }

    async def start_background_worker(self):
        """Start background worker (placeholder)"""
        logger.info("Background worker started")

    async def stop_background_worker(self):
        """Stop background worker (placeholder)"""
        logger.info("Background worker stopped")

    async def close(self):
        """Close job manager"""
        logger.info("Background job manager closed")


class BotConfigService:
    """Service for retrieving bot configuration"""

    async def get_bot_config(self, conversation_id: str) -> Dict[str, Any]:
        """Get bot configuration for conversation"""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)
                bot_crud = BotCRUD(session)

                # Get conversation to find bot_id
                conversation = await conversation_crud.get_by_id(conversation_id)
                if not conversation:
                    # Return default bot config if conversation not found
                    return await self._get_default_bot_config()

                # Get bot configuration
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
        """Get default bot configuration"""
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


class MessageHandler:
    """Enhanced MessageHandler for production use with Redis state management"""

    def __init__(self):
        self.redis = None
        self.lock_manager = None
        self.background_job_manager = BackgroundJobManager()
        self.bot_config_service = BotConfigService()
        self._initialized = False

    async def initialize(self):
        """Initialize all components"""
        if self._initialized:
            return

        try:
            # Try to get Redis connection
            try:
                self.redis = await get_redis_client()
                logger.info("MessageHandler Redis connection established")
            except Exception as redis_error:
                logger.warning("Redis connection failed, continuing without Redis", error=str(redis_error))
                self.redis = None

            # Initialize components with Redis (or None for fallback)
            self.lock_manager = MessageLockManager(self.redis)
            await self.background_job_manager.initialize()

            self._initialized = True
            logger.info("Enhanced message handler initialized successfully",
                       redis_available=bool(self.redis))
        except Exception as e:
            logger.error("Failed to initialize message handler", error=str(e))
            # Don't raise the exception, allow the handler to work in degraded mode
            self._initialized = True

    async def handle_message_request(
        self,
        conversation_id: str,
        history: str,
        resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for message handling with lock management and AI processing
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Handling message request",
                   conversation_id=conversation_id,
                   history_length=len(history)
                   )

        try:
            # Step 1: Cut old history from new history to get only new part for processing
            effective_history = await self._cut_old_history(conversation_id, history)
            if len(effective_history) != len(history):
                logger.info("Cut old history from new history",
                           conversation_id=conversation_id,
                           original_length=len(history),
                           effective_length=len(effective_history),
                           cut_amount=len(history) - len(effective_history))

            # Step 2: Get bot configuration
            bot_config = await self.bot_config_service.get_bot_config(conversation_id)
            logger.info("Bot config retrieved", bot_name=bot_config.get("name"))

            # Step 3: Get AI core configuration
            ai_config = await self._get_ai_config(bot_config.get("core_ai_id"))

            # Step 4: Get platform configuration
            platform_config = await self._get_platform_config(bot_config.get("platform_id"))

            # Step 5: Parse the effective (new) history into structured messages
            parsed_messages = await self._chunk_and_parse_history(
                effective_history,
                conversation_id=conversation_id
            )

            # Step 6: Check lock and consolidate messages if needed
            lock_result = await self.lock_manager.check_and_acquire_lock(
                conversation_id=conversation_id,
                history=effective_history,  # Use effective history for lock
                resources=resources
            )

            logger.info("Lock check completed",
                       action=lock_result["action"],
                       should_call_ai=lock_result["should_call_ai"],
                       should_cancel_previous=lock_result.get("should_cancel_previous", False),
                       parsed_message_count=len(parsed_messages))

            # Handle job cancellation if needed
            if lock_result.get("should_cancel_previous") and lock_result.get("previous_ai_job_id"):
                try:
                    await self.background_job_manager.cancel_job(lock_result["previous_ai_job_id"])
                    logger.info("Previous AI job cancelled",
                               cancelled_job_id=lock_result["previous_ai_job_id"],
                               conversation_id=conversation_id)
                except Exception as cancel_error:
                    logger.warning("Failed to cancel previous job",
                                  job_id=lock_result["previous_ai_job_id"],
                                  error=str(cancel_error))

            if lock_result["should_call_ai"]:
                # Start AI processing with new history only
                ai_job_id = await self._start_ai_processing(
                    conversation_id=conversation_id,
                    lock_data=lock_result["lock_data"],
                    bot_config=bot_config,
                    ai_config=ai_config,
                    platform_config=platform_config,
                    messages=parsed_messages,
                    resources=resources
                )

                # Update lock with AI job ID
                await self.lock_manager.update_lock_with_ai_job(
                    conversation_id, ai_job_id
                )

                # Cache the current full history for next time
                await self._cache_processed_history(conversation_id, history)

                action_description = "Message received and AI processing started with new history only"
                if lock_result.get("should_cancel_previous"):
                    action_description = "Previous job cancelled, reprocessing with new history only"

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
            else:
                return {
                    "success": True,
                    "status": "locked",
                    "action": lock_result["action"],
                    "message": "Message is being processed by another request"
                }

        except Exception as e:
            logger.error("Message handling failed",
                        conversation_id=conversation_id,
                        error=str(e))

            # Release lock on error
            if self.lock_manager:
                try:
                    await self.lock_manager.release_lock(conversation_id)
                except Exception as lock_error:
                    logger.error("Failed to release lock", error=str(lock_error))

            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "message": f"Message processing failed: {str(e)}"
            }

    async def _cut_old_history(self, conversation_id: str, current_history: str) -> str:
        """Cut old history from new history and return only the new part for processing"""
        try:
            # Step 1: Get old processed history from Redis cache first
            old_history = await self._get_cached_history(conversation_id)
            # Step 2: If no cache, get last processed history from database
            if not old_history:
                old_history = await self._get_last_processed_history_from_db(conversation_id)

            # Step 3: Cut old history from current to get only new part
            if old_history:
                new_history_part = await self._cut_old_history(current_history, old_history)
                logger.debug("Cut old history from current",
                           conversation_id=conversation_id,
                           current_length=len(current_history),
                           old_length=len(old_history),
                           new_part_length=len(new_history_part))
                return new_history_part
            else:
                logger.debug("No old history found, using full history",
                           conversation_id=conversation_id,
                           current_length=len(current_history))
                return current_history

        except Exception as e:
            logger.warning("Failed to cut old history, using full history",
                          conversation_id=conversation_id,
                          error=str(e))
            return current_history

    async def _get_ai_config(self, core_ai_id: str) -> Dict[str, Any]:
        """Get AI core configuration"""
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

                # Return default AI config
                return {
                    "core_ai_id": "default",
                    "name": "Default AI",
                    "api_endpoint": "http://localhost:8000/ai",
                    "auth_required": False,
                    "timeout_seconds": 30,
                    "meta_data": {}
                }
        except Exception as e:
            logger.error("Error getting AI config", error=str(e))
            return {"core_ai_id": "default", "name": "Default AI"}

    async def _get_platform_config(self, platform_id: str) -> Dict[str, Any]:
        """Get platform configuration"""
        try:
            async with async_session_factory() as session:
                platform_crud = PlatformCRUD(session)

                if platform_id and platform_id != "default":
                    platform = await platform_crud.get_by_id(uuid.UUID(platform_id))
                    if platform and platform.is_active:
                        return {
                            "platform_id": str(platform.id),
                            "name": platform.name,
                            "description": platform.description,
                            "base_url": platform.base_url,
                            "auth_required": platform.auth_required,
                            "auth_token": platform.auth_token,
                            "meta_data": platform.meta_data
                        }

                # Return default platform config
                return {
                    "platform_id": "default",
                    "name": "Default Platform",
                    "description": "Default platform",
                    "base_url": "http://localhost:8000",
                    "auth_required": False,
                    "meta_data": {}
                }
        except Exception as e:
            logger.error("Error getting platform config", error=str(e))
            return {"platform_id": "default", "name": "Default Platform"}

    async def _chunk_and_parse_history(self, history: str, max_messages: int = 20, max_chars: int = 10000, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse and chunk history into structured messages"""
        try:
            if not history:
                return []

            # Parse the history into structured messages with chunking limits
            messages = await self._parse_chunked_history(history)

            logger.info("History chunked and parsed",
                       original_length=len(history),
                       message_count=len(messages),
                       max_messages=max_messages)

            return messages

        except Exception as e:
            logger.error("Error in history processing", error=str(e))
            # Fallback: try to parse original history with basic truncation
            truncated_history = history[-max_chars:] if len(history) > max_chars else history
            return [{"role": "user", "content": truncated_history, "timestamp": time.time()}]

    async def _get_cached_history(self, conversation_id: str) -> Optional[str]:
        """Get cached processed history from Redis"""
        try:
            cache_key = f"processed_history:{conversation_id}"

            if self.redis:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    try:
                        data = json.loads(cached_data)
                        return data.get("history", "")
                    except json.JSONDecodeError:
                        logger.warning("Invalid cached history data", conversation_id=conversation_id)
                        return None
            else:
                # Fallback to in-memory cache (for development)
                fallback_key = f"history_cache_{conversation_id}"
                if hasattr(self, '_history_cache'):
                    return self._history_cache.get(fallback_key)

            return None

        except Exception as e:
            logger.warning("Failed to get cached history",
                          conversation_id=conversation_id,
                          error=str(e))
            return None

    async def _get_processed_history(self, conversation_id: str) -> Optional[str]:
        """Get last processed history from database conversation record"""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)
                conversation = await conversation_crud.get_by_id_simple(uuid.UUID(conversation_id))

                if conversation and conversation.history:
                    logger.debug("Retrieved history from database",
                               conversation_id=conversation_id,
                               history_length=len(conversation.history))
                    return conversation.history

                logger.debug("No history found in database",
                           conversation_id=conversation_id)
                return None

        except Exception as e:
            logger.warning("Failed to get history from database",
                          conversation_id=conversation_id,
                          error=str(e))
            return None

    async def _cut_old_history(self, current_history: str, old_history: str) -> str:
        """Cut old history from current history to get only new messages"""
        try:
            if not old_history or old_history not in current_history:
                # Old history not found in current, return all as new
                logger.debug("Old history not found in current, treating all as new")
                return current_history

            # Find where old history ends and cut from there
            old_end_position = current_history.find(old_history) + len(old_history)
            new_part = current_history[old_end_position:].strip()

            logger.debug("Successfully cut old history",
                        old_history_length=len(old_history),
                        new_part_length=len(new_part),
                        cut_position=old_end_position)

            return new_part

        except Exception as e:
            logger.warning("Failed to cut old history, returning all as new", error=str(e))
            return current_history

    async def _cache_processed_history(self, conversation_id: str, history: str):
        """Cache the processed history for incremental processing"""
        try:
            cache_key = f"processed_history:{conversation_id}"
            cache_data = {
                "history": history,
                "processed_at": time.time(),
                "conversation_id": conversation_id
            }

            if self.redis:
                # Cache for 1 hour
                await self.redis.set(
                    cache_key,
                    json.dumps(cache_data),
                    ex=3600
                )
                logger.debug("Cached processed history in Redis",
                           conversation_id=conversation_id,
                           history_length=len(history))
            else:
                # Fallback to in-memory cache
                if not hasattr(self, '_history_cache'):
                    self._history_cache = {}
                fallback_key = f"history_cache_{conversation_id}"
                self._history_cache[fallback_key] = history
                logger.debug("Cached processed history in memory",
                           conversation_id=conversation_id,
                           history_length=len(history))

        except Exception as e:
            logger.warning("Failed to cache processed history",
                          conversation_id=conversation_id,
                          error=str(e))

    async def _update_conversation_history_in_db(self, conversation_id: str, new_history: str):
        """Update conversation history in database with new processed history"""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)

                # Update conversation with new history
                update_data = {"history": new_history}
                updated = await conversation_crud.update(
                    uuid.UUID(conversation_id),
                    update_data
                )

                if updated:
                    logger.debug("Updated conversation history in database",
                               conversation_id=conversation_id,
                               new_history_length=len(new_history))
                    return True
                else:
                    logger.warning("Failed to update conversation history",
                                 conversation_id=conversation_id)
                    return False

        except Exception as e:
            logger.error("Error updating conversation history in database",
                        conversation_id=conversation_id,
                        error=str(e))
            return False

    async def _start_ai_processing(
        self,
        conversation_id: str,
        lock_data: Dict[str, Any],
        bot_config: Dict[str, Any],
        ai_config: Dict[str, Any],
        platform_config: Dict[str, Any],
        messages: List[Dict[str, Any]],
        resources: Optional[Dict[str, Any]]
    ) -> str:
        """Start background AI processing job"""

        ai_job_payload = {
            "conversation_id": conversation_id,
            "lock_id": lock_data["lock_id"],
            "messages": messages,
            "bot_config": bot_config,
            "ai_config": ai_config,
            "platform_config": platform_config,
            "resources": resources or {},
        }

        # Create background job
        ai_job_id = await self.background_job_manager.create_ai_processing_job(
            ai_job_payload
        )

        logger.info("AI processing job created",
                   conversation_id=conversation_id,
                   ai_job_id=ai_job_id,
                   message_count=len(messages))

        return ai_job_id

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job processing status"""
        if not self._initialized:
            await self.initialize()

        return await self.background_job_manager.get_job_status(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job"""
        if not self._initialized:
            await self.initialize()

        return await self.background_job_manager.cancel_job(job_id)

    async def get_conversation_lock_info(self, conversation_id: str) -> Optional[Dict]:
        """Get current lock information for conversation"""
        if not self._initialized:
            await self.initialize()

        return await self.lock_manager.get_lock_info(conversation_id)

    async def release_conversation_lock(self, conversation_id: str) -> bool:
        """Manually release conversation lock (for admin/debug purposes)"""
        if not self._initialized:
            await self.initialize()

        return await self.lock_manager.release_lock(conversation_id)

    async def get_handler_status(self) -> Dict[str, Any]:
        """Get overall handler status"""
        if not self._initialized:
            return {
                "initialized": False,
                "components": {}
            }

        worker_status = await self.background_job_manager.get_worker_status()

        return {
            "initialized": self._initialized,
            "components": {
                "redis_connected": bool(self.redis),
                "lock_manager": bool(self.lock_manager),
                "background_job_manager": worker_status
            },
            "status": "healthy" if all([
                self.lock_manager,
                worker_status.get("status") == "healthy"
            ]) else "degraded"
        }

    async def start_background_processing(self):
        """Start background job processing worker"""
        if not self._initialized:
            await self.initialize()

        logger.info("Starting background processing worker")
        await self.background_job_manager.start_background_worker()

    async def stop_background_processing(self):
        """Stop background job processing worker"""
        if self.background_job_manager:
            logger.info("Stopping background processing worker")
            await self.background_job_manager.stop_background_worker()

    async def cleanup_old_locks(self, max_age_hours: int = 24) -> int:
        """Clean up old message locks"""
        if not self._initialized:
            await self.initialize()

        try:
            if not self.redis:
                # Clean up in-memory fallback locks
                current_time = time.time()
                max_age_seconds = max_age_hours * 3600
                cleaned_count = 0

                keys_to_remove = []
                for key, lock_data in self.lock_manager._fallback_locks.items():
                    if current_time - lock_data.get("created_at", 0) > max_age_seconds:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.lock_manager._fallback_locks[key]
                    cleaned_count += 1

                logger.info("Cleaned up old fallback locks", count=cleaned_count)
                return cleaned_count

            # Redis cleanup logic
            lock_pattern = f"{self.lock_manager.lock_prefix}*"
            lock_keys = await self.redis.keys(lock_pattern)

            cleaned_count = 0
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for key in lock_keys:
                lock_data = await self.redis.get(key)
                if lock_data:
                    try:
                        lock_info = json.loads(lock_data)
                        created_at = lock_info.get("created_at", 0)

                        if current_time - created_at > max_age_seconds:
                            await self.redis.delete(key)
                            cleaned_count += 1

                    except json.JSONDecodeError:
                        # Invalid lock data, remove it
                        await self.redis.delete(key)
                        cleaned_count += 1

            logger.info("Cleaned up old locks", count=cleaned_count)
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup old locks", error=str(e))
            return 0

    async def close(self):
        """Clean up all resources"""
        logger.info("Closing enhanced message handler")

        if self.background_job_manager:
            await self.background_job_manager.close()

        self._initialized = False
        logger.info("Enhanced message handler closed")

    async def _chunk_old_history(self, history: str, max_messages: int = 20, max_chars: int = 10000) -> str:
        """Chunk old history to keep only recent messages within limits"""
        try:
            import re

            # Find all message blocks with their positions
            message_pattern = r'(<(?:USER|BOT|SALE)>.*?</(?:USER|BOT|SALE)>(?:<br>|$))'
            matches = list(re.finditer(message_pattern, history, re.DOTALL))

            if not matches:
                # No structured messages found, truncate by characters
                logger.warning("No structured messages found in history, truncating by characters")
                return history[-max_chars:] if len(history) > max_chars else history

            logger.debug("Found message blocks",
                        total_messages=len(matches),
                        original_chars=len(history),
                        max_messages=max_messages,
                        max_chars=max_chars)

            # Strategy: Keep recent messages within both message count and character limits
            recent_messages = []
            total_chars = 0

            # Work backwards from the end to keep most recent messages
            for match in reversed(matches):
                message_text = match.group(1)

                # Check if adding this message would exceed limits
                if (len(recent_messages) >= max_messages or
                    total_chars + len(message_text) > max_chars):
                    logger.debug("Stopping message collection",
                                message_count=len(recent_messages),
                                chars_so_far=total_chars,
                                would_add_chars=len(message_text),
                                max_messages=max_messages,
                                max_chars=max_chars)
                    break

                recent_messages.append(message_text)
                total_chars += len(message_text)

            # Reverse to get chronological order
            recent_messages.reverse()

            # Join the recent messages
            chunked_history = ''.join(recent_messages)

            logger.info("History chunked",
                       original_messages=len(matches),
                       kept_messages=len(recent_messages),
                       original_chars=len(history),
                       chunked_chars=len(chunked_history))

            return chunked_history

        except Exception as e:
            logger.error("Error chunking history", error=str(e))
            # Fallback: simple character truncation
            return history[-max_chars:] if len(history) > max_chars else history

    async def _parse_chunked_history(self, chunked_history: str) -> List[Dict[str, Any]]:
        """Parse chunked history into structured messages with proper ordering"""
        try:
            if not chunked_history:
                return []

            import re

            # Find all message patterns with their positions in the text
            message_data = []

            patterns = [
                (r'<USER>(.*?)</USER>', 'user'),
                (r'<BOT>(.*?)</BOT>', 'bot'),
                (r'<SALE>(.*?)</SALE>', 'sale')
            ]

            for pattern, role in patterns:
                for match in re.finditer(pattern, chunked_history, re.DOTALL):
                    message_data.append({
                        "role": role,
                        "content": match.group(1).strip(),
                        "timestamp": time.time(),
                        "position": match.start()  # For proper ordering
                    })

            # Sort by position in original string to maintain chronological order
            message_data.sort(key=lambda x: x["position"])

            # Remove position field and return clean message list
            messages = []
            for msg in message_data:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"]
                })

            logger.debug("Parsed chunked history",
                        message_count=len(messages),
                        roles=[msg["role"] for msg in messages])

            return messages

        except Exception as e:
            logger.error("Error parsing chunked history", error=str(e))
            return [{"role": "user", "content": chunked_history, "timestamp": time.time()}]

    async def _parse_history(self, history: str) -> List[Dict[str, Any]]:
        """Parse conversation history into structured messages (legacy method)"""
        # Use the new chunking method with default limits
        return await self._chunk_and_parse_history(history, max_messages=20, max_chars=10000)