import asyncio
from typing import Dict, Any, Optional, List, Union
import structlog
import json
import time
import uuid
import re

from app.core.redis_client import get_redis_client
from app.core.database import async_session_factory
from app.crud.bot_crud import BotCRUD
from app.crud.core_ai_crud import CoreAICRUD
from app.crud.platform_crud import PlatformCRUD
from app.crud.conversation_crud import ConversationCRUD
from app.utils.common import history_parser
from app.clients.core_ai_client import get_ai_service
from app.clients.platform_client import PlatformClient, get_platform_client

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

    def __init__(self, parent_handler=None):
        self.redis = None
        self.job_prefix = "ai_job:"
        self.job_ttl = 3600  # 1 hour
        self._fallback_jobs = {}  # In-memory fallback for testing
        self._worker_task = None
        self._worker_running = False
        self._processing_queue = asyncio.Queue()
        self.parent_handler = parent_handler  # Reference to parent MessageHandler

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
        job_id = str(time.time())
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

        # Queue the job for processing by background worker
        if self._worker_running:
            await self._queue_job_for_processing(job_id)
        else:
            # Fallback: process immediately if worker not running
            logger.warning("Background worker not running, processing job immediately", job_id=job_id)
            asyncio.create_task(self._process_ai_job(job_id))

        return job_id

    async def _process_ai_job(self, job_id: str):
        """Process AI job using real AI service"""
        job_key = f"{self.job_prefix}{job_id}"

        # Check if job was cancelled before we even start processing
        if await self._check_job_cancellation(job_id):
            logger.info("Job was cancelled before processing started", job_id=job_id)
            return

        # Update status to processing
        await self._update_job_status(job_id, "processing", {
            "processing_started_at": time.time()
        })

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

            # Check for cancellation again after fetching job data
            if await self._check_job_cancellation(job_id):
                logger.info("Job was cancelled during data fetching", job_id=job_id)
                return

            payload = job_data.get("payload", {})
            conversation_id = payload.get("conversation_id")
            platform_conversation_id = payload.get("platform_conversation_id", "")
            messages = payload.get("messages", [])
            bot_config = payload.get("bot_config", {})
            ai_config = payload.get("ai_config", {})
            platform_config = payload.get("platform_config", {})
            resources = payload.get("resources", {})
            lock_id = payload.get("lock_id", "")

            # Get AI service instance
            ai_service = get_ai_service()
            platform_client = get_platform_client()

            # Final check for cancellation before starting AI processing
            if await self._check_job_cancellation(job_id):
                logger.info("Job was cancelled before AI processing", job_id=job_id)
                return

            # Process the job using real AI service with message array
            ai_result = await ai_service.process_job(
                job_id=job_id,
                conversation_id=conversation_id,
                messages=messages,  # Pass messages array directly
                context={
                    "bot_config": bot_config,
                    "ai_config": ai_config,
                    "resources": resources,
                    "lock_id": lock_id
                },
                core_ai_id=ai_config.get("core_ai_id")
            )

            # Check if job was cancelled during AI processing
            if await self._check_job_cancellation(job_id):
                logger.info("Job was cancelled during AI processing",
                           job_id=job_id,
                           conversation_id=conversation_id)
                return

            # Update status based on AI processing result
            if ai_result.get("success"):
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
                           ai_action=ai_result.get("action", ""),
                           conversation_turns=ai_result.get("conversation_turns"))

                ai_action = ai_result.get("action", "")
                ai_response = ai_result.get("data", {})

                print("=========== AI ACTION ===========")
                print(ai_action)
                print("=========== AI RESPONSE ===========")
                print(ai_response)

                if ai_action == "OUT_OF_SCOPE":
                    ai_action = "NOTIFY"

                # Implement platform history check and action execution
                try:
                    # Get the platform configuration for this job
                    platform_id = platform_config.get("id")

                    logger.info("Starting platform history validation",
                               job_id=job_id,
                               conversation_id=conversation_id,
                               platform_id=platform_id)

                    latest_history = await platform_client.get_conversation_history(
                        conversation_id=platform_conversation_id,
                        platform_config=platform_config
                    )

                    print("=========== LATEST HISTORY ===========")
                    print(latest_history)
                    print("=========== LATEST HISTORY ===========")

                    old_history = await self.parent_handler._get_cached_history(platform_conversation_id)
                    print("=========== OLD HISTORY ===========")
                    print(old_history)
                    print("=========== OLD HISTORY ===========")

                    logger.info("Proceeding with platform action execution",
                               job_id=job_id,
                               conversation_id=platform_conversation_id)

                    # Execute the AI action through platform
                    await self.parent_handler._execute_platform_action(
                        ai_action, ai_response, platform_conversation_id, platform_config, job_id, platform_client
                    )

                except Exception as e:
                    logger.error("Error during platform action execution",
                               job_id=job_id,
                               conversation_id=conversation_id,
                               error=str(e))
                    # Mark job as completed but with error in platform action
                    await self._update_job_status(job_id, "completed_with_error", {
                        "ai_action": ai_action,
                        "platform_error": str(e),
                        "completed_at": time.time()
                    })

            else:
                await self._update_job_status(job_id, "failed", {
                    "error": ai_result.get("error", "AI processing failed"),
                    "ai_action": ai_result.get("action", ""),
                    "processing_time_ms": ai_result.get("processing_time_ms"),
                    "completed_at": time.time()
                })
                logger.error("AI job failed",
                            job_id=job_id,
                            conversation_id=conversation_id,
                            error=ai_result.get("error"))

        except Exception as e:
            # Check if the exception was due to cancellation
            if await self._check_job_cancellation(job_id):
                logger.info("Job was cancelled during exception handling", job_id=job_id)
                return

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

            logger.info("Job status updated",
                       job_id=job_id,
                       status=status,
                       additional_data=additional_data)

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
        try:
            # First update the job status to cancelled
            await self._update_job_status(job_id, "cancelled", {
                "cancelled_at": time.time(),
                "reason": "cancelled_by_user"
            })

            logger.info("Job cancelled successfully", job_id=job_id)
            return True

        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            return False

    async def _check_job_cancellation(self, job_id: str) -> bool:
        """Check if a job has been cancelled"""
        try:
            job_status = await self.get_job_status(job_id)
            return job_status.get("status") == "cancelled"
        except Exception as e:
            logger.warning("Failed to check job cancellation status", job_id=job_id, error=str(e))
            return False

    async def get_worker_status(self) -> Dict[str, Any]:
        """Get worker status"""
        return {
            "redis_connected": bool(self.redis),
            "worker_running": self._worker_running,
            "worker_task_active": bool(self._worker_task and not self._worker_task.done()),
            "queue_size": self._processing_queue.qsize(),
            "fallback_jobs": len(self._fallback_jobs) if not self.redis else 0,
            "status": "healthy" if self._worker_running else "stopped"
        }

    async def start_background_worker(self):
        """Start background worker"""
        if self._worker_running:
            logger.warning("Background worker already running")
            return

        self._worker_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Background worker started")

    async def stop_background_worker(self):
        """Stop background worker"""
        if not self._worker_running:
            logger.warning("Background worker not running")
            return

        self._worker_running = False

        if self._worker_task:
            try:
                # Cancel the worker task
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
        """Main worker loop that processes jobs from the queue"""
        logger.info("Background worker loop started")

        while self._worker_running:
            try:
                # Wait for job with timeout to allow periodic health checks
                try:
                    job_id = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=10.0
                    )

                    if job_id:
                        logger.debug("Processing job from queue", job_id=job_id)
                        await self._process_ai_job(job_id)
                        self._processing_queue.task_done()

                except asyncio.TimeoutError:
                    # Timeout is normal, continue the loop
                    continue

            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error("Error in worker loop", error=str(e))
                # Continue running despite errors
                await asyncio.sleep(1)

        logger.info("Background worker loop stopped")

    async def _queue_job_for_processing(self, job_id: str):
        """Queue a job for background processing"""
        try:
            await self._processing_queue.put(job_id)
            logger.debug("Job queued for processing", job_id=job_id)
        except Exception as e:
            logger.error("Failed to queue job", job_id=job_id, error=str(e))
            # If queueing fails, process immediately as fallback
            asyncio.create_task(self._process_ai_job(job_id))

    async def close(self):
        """Close job manager"""
        logger.info("Closing background job manager")

        # Stop the worker
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
    """Service for retrieving bot configuration"""

    async def get_bot_config(self, section_id: str) -> Dict[str, Any]:
        """Get bot configuration for conversation"""
        try:
            async with async_session_factory() as session:
                conversation_crud = ConversationCRUD(session)
                bot_crud = BotCRUD(session)

                # Get conversation to find bot_id
                conversation = await conversation_crud.get_by_id(section_id)
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
        self.bot_config_service = BotConfigService()
        self.background_job_manager = None  # Will be set after initialization
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
            self.background_job_manager = BackgroundJobManager(self)
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
        bot_id: str,
        history: str,
        resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for message handling with lock management and AI processing
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Handling message request",
                   bot_id=bot_id,
                   conversation_id=conversation_id,
                   history_length=len(history)
                   )

        # Get conversation by conversation ID
        async with async_session_factory() as session:
            conversation_crud = ConversationCRUD(session)
            conversation = await conversation_crud.get_by_conversation_id(conversation_id)
            if not conversation:
                conversation = await conversation_crud.create_conversation_by_bot_and_conversation_id(uuid.UUID(bot_id), conversation_id)
            section_id = str(conversation.id)

        try:
            # Step 1: Cut old history from new history to get only new part for processing
            effective_history = await self._cut_old_history(section_id, history)
            if len(effective_history) != len(history):
                logger.info("Cut old history from new history",
                           section_id=section_id,
                           original_length=len(history),
                           effective_length=len(effective_history),
                           cut_amount=len(history) - len(effective_history))
            # if len(effective_history) == 0:
            #     return {
            #         "success": True,
            #         "status": "no_history",
            #         "message": "No history to process"
            #     }

            # Step 2: Get bot configuration
            bot_config = await self.bot_config_service.get_bot_config(section_id)
            logger.info("Bot config retrieved", bot_name=bot_config.get("name"))

            # Step 3: Get AI core configuration
            ai_config = await self._get_ai_config(bot_config.get("core_ai_id"))

            # Step 4: Get platform configuration
            platform_config = await self._get_platform_config(bot_config.get("platform_id"))

            # Step 5: Parse the effective (new) history into structured messages
            parsed_messages = await self._parse_history(
                effective_history,
                conversation_id=section_id
            )
            # Step 6: Check lock and consolidate messages if needed
            lock_result = await self.lock_manager.check_and_acquire_lock(
                conversation_id=section_id,
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
                               conversation_id=section_id)
                except Exception as cancel_error:
                    logger.warning("Failed to cancel previous job",
                                  job_id=lock_result["previous_ai_job_id"],
                                  error=str(cancel_error))

            if lock_result["should_call_ai"]:
                # Start AI processing with new history only
                ai_job_id = await self._start_ai_processing(
                    section_id=section_id,
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
                    section_id, ai_job_id
                )

                # Cache the current full history for next time
                await self._cache_processed_history(section_id, history)

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
                    await self.lock_manager.release_lock(section_id)
                except Exception as lock_error:
                    logger.error("Failed to release lock", error=str(lock_error))

            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "message": f"Message processing failed: {str(e)}"
            }

    async def _cut_old_history(self, section_id: str, current_history: str) -> str:
        """Cut old history from new history and return only the new part for processing"""
        try:
            # Step 1: Get old processed history from Redis cache first
            old_history = await self._get_cached_history(section_id)
            # Step 2: If no cache, get last processed history from database
            if not old_history:
                old_history = await self._get_processed_history(section_id)
            # Step 3: Cut old history from current to get only new part
            if old_history:
                new_history_part = await self._cut_history(current_history, old_history)
                logger.debug("Cut old history from current",
                           section_id=section_id,
                           current_length=len(current_history),
                           old_length=len(old_history),
                           new_part_length=len(new_history_part))
                return new_history_part
            else:
                logger.debug("No old history found, using full history",
                           section_id=section_id,
                           current_length=len(current_history))
                return current_history

        except Exception as e:
            logger.warning("Failed to cut old history, using full history",
                          section_id=section_id,
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
                    "api_endpoint": "http://localhost:8000",
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
                    platform = await platform_crud.get_by_id_with_actions(uuid.UUID(platform_id))
                    if platform and platform.is_active:
                        if platform.actions:
                            actions = [action.model_dump() for action in platform.actions]
                        else:
                            actions = []
                        return {
                            "platform_id": str(platform.id),
                            "name": platform.name,
                            "description": platform.description,
                            "base_url": platform.base_url,
                            "auth_required": platform.auth_required,
                            "auth_token": platform.auth_token,
                            "meta_data": platform.meta_data,
                            "actions": actions
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

    async def _parse_history(self, history: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse and chunk history into structured messages"""
        try:
            if not history:
                return []

            # Find all message patterns with their positions in the text
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
                        "position": match.start()  # For proper ordering
                    })

            # Sort by position in original string to maintain chronological order
            message_data.sort(key=lambda x: x["position"])

            # Remove position field and return clean message list
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

    async def _cut_history(self, current_history: str, old_history: str) -> str:
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
        section_id: str,
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
            "conversation_id": section_id,
            "platform_conversation_id": conversation_id,
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
                   conversation_id=section_id,
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

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Cleanup old jobs older than max_age_hours"""
        try:
            cleanup_count = 0
            cutoff_time = time.time() - (max_age_hours * 3600)

            if self.redis:
                # Get all job keys
                pattern = f"{self.background_job_manager.job_prefix}*"
                keys = await self.redis.keys(pattern)

                for key in keys:
                    try:
                        job_data = await self.redis.get(key)
                        if job_data:
                            data = json.loads(job_data)
                            created_at = data.get("created_at", 0)

                            if created_at < cutoff_time:
                                await self.redis.delete(key)
                                cleanup_count += 1
                                logger.debug("Cleaned up old job",
                                           job_key=key,
                                           age_hours=(time.time() - created_at) / 3600)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning("Error processing job for cleanup",
                                     job_key=key, error=str(e))
                        # Delete corrupted job data
                        await self.redis.delete(key)
                        cleanup_count += 1
            else:
                # Fallback cleanup for in-memory jobs
                keys_to_remove = []
                for key, data in self.background_job_manager._fallback_jobs.items():
                    created_at = data.get("created_at", 0)
                    if created_at < cutoff_time:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.background_job_manager._fallback_jobs[key]
                    cleanup_count += len(keys_to_remove)

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
        """Execute the AI action through the platform"""
        try:
            platform_id = platform_config.get("platform_id") or platform_config.get("id")
            platform_name = platform_config.get("name", "Unknown Platform")

            logger.info("Executing platform action",
                       job_id=job_id,
                       conversation_id=conversation_id,
                       ai_action=ai_action,
                       platform_id=platform_id,
                       platform_name=platform_name)

            # For now, we'll implement a simplified action execution
            # In a full implementation, this would make HTTP calls to the platform's API
            action_executed = False

            platform_actions = platform_config.get("actions", [])

            actions_map = {}
            for action in platform_actions:
                actions_map[action.get("name")] = {
                    "path": action.get("path"),
                    "method": action.get("method"),
                    "meta_data": action.get("meta_data")
                }

            platform_action = actions_map.get(ai_action, None)

            if platform_action:
                # Log bot response that would be sent to platform
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

            # Update job status with action execution results
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

            # Update job status as failed
            await self.background_job_manager._update_job_status(job_id, "failed", {
                "error": f"Platform action execution failed: {str(e)}",
                "ai_action": ai_action,
                "completed_at": time.time()
            })

    async def close(self):
        """Clean up all resources"""
        logger.info("Closing enhanced message handler")

        if self.background_job_manager:
            await self.background_job_manager.close()

        self._initialized = False
        logger.info("Enhanced message handler closed")