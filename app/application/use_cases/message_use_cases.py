"""
Message Use Cases
Application services for Message processing and management operations
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import structlog

from app.domain.entities.message import Message
from app.domain.entities.conversation import Conversation
from app.domain.repositories.conversation_repository import IConversationRepository
from app.domain.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    InvalidOperationError
)
from app.application.dtos.message_dtos import (
    CreateMessageDTO,
    UpdateMessageDTO,
    MessageDTO,
    MessageListDTO,
    ProcessMessageDTO,
    RetryMessageDTO,
    MessageStatsDTO,
    MessageSearchDTO,
    BulkMessageOperationDTO,
    MessageAnalyticsDTO,
    MessageExportDTO,
    MessageRoleDTO,
    MessageStatusDTO,
    MessageTypeDTO
)
from app.application.interfaces.ai_service_interface import IAIService, AIRequest
from app.application.interfaces.platform_service_interface import IPlatformService, SendMessageRequest
from app.application.exceptions import (
    UseCaseError,
    ResourceNotFoundError,
    ValidationError,
    ExternalServiceError
)

logger = structlog.get_logger(__name__)


class MessageUseCases:
    """
    Application services for Message processing and management

    Handles message lifecycle, processing, and analytics
    """

    def __init__(
        self,
        conversation_repository: IConversationRepository,
        ai_service: IAIService,
        platform_service: Optional[IPlatformService] = None
    ):
        self.conversation_repository = conversation_repository
        self.ai_service = ai_service
        self.platform_service = platform_service

    async def create_message(self, create_dto: CreateMessageDTO) -> MessageDTO:
        """
        Create new message in conversation

        Args:
            create_dto: Message creation data

        Returns:
            MessageDTO: Created message
        """
        try:
            logger.info("Creating new message",
                       conversation_id=str(create_dto.conversation_id))

            # Get conversation
            conversation = await self.conversation_repository.get_by_id(create_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", str(create_dto.conversation_id))

            # Create message through conversation
            message = conversation.add_message(
                content=create_dto.content,
                role=self._dto_to_domain_role(create_dto.role),
                metadata=create_dto.metadata
            )

            # Update conversation
            updated_conversation = conversation._replace(
                messages=conversation.messages + [message]
            )

            # Persist
            await self.conversation_repository.update(updated_conversation)

            logger.info("Message created successfully",
                       message_id=str(message.id))

            return self._domain_to_dto(message)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during message creation", error=str(e))
            raise UseCaseError("create_message", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during message creation", error=str(e))
            raise UseCaseError("create_message", f"Failed to create message: {str(e)}")

    async def update_message_status(self, update_dto: UpdateMessageDTO) -> MessageDTO:
        """
        Update message status and metadata

        Args:
            update_dto: Message update data

        Returns:
            MessageDTO: Updated message
        """
        try:
            logger.info("Updating message status",
                       message_id=str(update_dto.message_id))

            # Find conversation containing the message
            conversation = await self._find_conversation_by_message_id(update_dto.message_id)
            if not conversation:
                raise ResourceNotFoundError("Message", str(update_dto.message_id))

            # Find and update message
            updated_messages = []
            target_message = None

            for message in conversation.messages:
                if message.id == update_dto.message_id:
                    # Update message
                    updated_message = message

                    if update_dto.status is not None:
                        status = self._dto_to_domain_status(update_dto.status)
                        if update_dto.status == MessageStatusDTO.PROCESSING:
                            updated_message = updated_message.mark_as_processing(update_dto.ai_model)
                        elif update_dto.status == MessageStatusDTO.SENT:
                            updated_message = updated_message.mark_as_sent(
                                update_dto.processing_time_ms,
                                update_dto.confidence_score
                            )
                        elif update_dto.status == MessageStatusDTO.FAILED:
                            updated_message = updated_message.mark_as_failed(update_dto.error_reason)

                    if update_dto.retry_count is not None:
                        updated_message = updated_message._replace(retry_count=update_dto.retry_count)

                    target_message = updated_message
                    updated_messages.append(updated_message)
                else:
                    updated_messages.append(message)

            if not target_message:
                raise ResourceNotFoundError("Message", str(update_dto.message_id))

            # Update conversation
            updated_conversation = conversation._replace(messages=updated_messages)
            await self.conversation_repository.update(updated_conversation)

            logger.info("Message status updated successfully",
                       message_id=str(update_dto.message_id))

            return self._domain_to_dto(target_message)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during message update", error=str(e))
            raise UseCaseError("update_message_status", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during message update", error=str(e))
            raise UseCaseError("update_message_status", f"Failed to update message: {str(e)}")

    async def process_message_for_ai(self, process_dto: ProcessMessageDTO) -> MessageDTO:
        """
        Process message through AI service

        Args:
            process_dto: Message processing data

        Returns:
            MessageDTO: Processed message
        """
        try:
            logger.info("Processing message for AI",
                       message_id=str(process_dto.message_id))

            # Mark message as processing
            update_dto = UpdateMessageDTO(
                message_id=process_dto.message_id,
                status=MessageStatusDTO.PROCESSING,
                ai_model=process_dto.ai_model
            )
            processing_message = await self.update_message_status(update_dto)

            try:
                # Generate AI response
                ai_request = AIRequest(
                    message=processing_message.content,
                    context=process_dto.context_data,
                    model=process_dto.ai_model,
                    temperature=process_dto.temperature,
                    max_tokens=process_dto.max_tokens,
                    timeout_seconds=process_dto.timeout_seconds
                )

                ai_response = await self.ai_service.generate_response(ai_request)

                # Mark as sent with results
                success_update = UpdateMessageDTO(
                    message_id=process_dto.message_id,
                    status=MessageStatusDTO.SENT,
                    confidence_score=ai_response.confidence_score,
                    processing_time_ms=ai_response.processing_time_ms
                )

                return await self.update_message_status(success_update)

            except Exception as ai_error:
                # Mark as failed
                error_update = UpdateMessageDTO(
                    message_id=process_dto.message_id,
                    status=MessageStatusDTO.FAILED,
                    error_reason=str(ai_error)
                )

                await self.update_message_status(error_update)
                raise ExternalServiceError("AI Service", "generate_response", str(ai_error))

        except Exception as e:
            logger.error("Error processing message for AI",
                        message_id=str(process_dto.message_id),
                        error=str(e))
            raise UseCaseError("process_message_for_ai", f"Failed to process message: {str(e)}")

    async def retry_failed_message(self, retry_dto: RetryMessageDTO) -> MessageDTO:
        """
        Retry failed message processing

        Args:
            retry_dto: Retry data

        Returns:
            MessageDTO: Retried message
        """
        try:
            logger.info("Retrying failed message",
                       message_id=str(retry_dto.message_id))

            # Find and validate message
            conversation = await self._find_conversation_by_message_id(retry_dto.message_id)
            if not conversation:
                raise ResourceNotFoundError("Message", str(retry_dto.message_id))

            target_message = None
            for message in conversation.messages:
                if message.id == retry_dto.message_id:
                    target_message = message
                    break

            if not target_message:
                raise ResourceNotFoundError("Message", str(retry_dto.message_id))

            # Check if message can be retried
            if not target_message.can_retry():
                raise BusinessRuleViolationError(
                    "MESSAGE_CANNOT_RETRY",
                    f"Message has reached max retry limit or is not in failed state"
                )

            # Retry message
            retried_message = target_message.retry()

            # Update conversation
            updated_messages = [
                retried_message if msg.id == retry_dto.message_id else msg
                for msg in conversation.messages
            ]

            updated_conversation = conversation._replace(messages=updated_messages)
            await self.conversation_repository.update(updated_conversation)

            logger.info("Message retry initiated successfully",
                       message_id=str(retry_dto.message_id))

            return self._domain_to_dto(retried_message)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during message retry", error=str(e))
            raise UseCaseError("retry_failed_message", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during message retry", error=str(e))
            raise UseCaseError("retry_failed_message", f"Failed to retry message: {str(e)}")

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> MessageListDTO:
        """
        Get messages for a conversation with pagination

        Args:
            conversation_id: Conversation identifier
            page: Page number
            page_size: Number of messages per page

        Returns:
            MessageListDTO: List of messages
        """
        try:
            conversation = await self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", str(conversation_id))

            # Apply pagination
            total_count = len(conversation.messages)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            paginated_messages = conversation.messages[start_idx:end_idx]
            message_dtos = [self._domain_to_dto(msg) for msg in paginated_messages]

            return MessageListDTO(
                messages=message_dtos,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=end_idx < total_count,
                has_previous=page > 1
            )

        except Exception as e:
            logger.error("Error getting conversation messages",
                        conversation_id=str(conversation_id),
                        error=str(e))
            raise UseCaseError("get_conversation_messages", f"Failed to get messages: {str(e)}")

    async def search_messages(self, search_dto: MessageSearchDTO) -> MessageListDTO:
        """
        Search messages with filters

        Args:
            search_dto: Search criteria

        Returns:
            MessageListDTO: List of matching messages
        """
        try:
            logger.info("Searching messages", query=search_dto.content_query)

            # Get messages from repository
            messages, total_count = await self.conversation_repository.search_messages(
                conversation_id=search_dto.conversation_id,
                role=self._dto_to_domain_role(search_dto.role) if search_dto.role else None,
                status=self._dto_to_domain_status(search_dto.status) if search_dto.status else None,
                content_query=search_dto.content_query,
                date_from=search_dto.date_from,
                date_to=search_dto.date_to,
                min_confidence=search_dto.min_confidence,
                max_confidence=search_dto.max_confidence,
                page=search_dto.page,
                page_size=search_dto.page_size,
                sort_by=search_dto.sort_by,
                sort_order=search_dto.sort_order
            )

            # Convert to DTOs
            message_dtos = [self._domain_to_dto(msg) for msg in messages]

            return MessageListDTO(
                messages=message_dtos,
                total_count=total_count,
                page=search_dto.page,
                page_size=search_dto.page_size,
                has_next=(search_dto.page * search_dto.page_size) < total_count,
                has_previous=search_dto.page > 1
            )

        except Exception as e:
            logger.error("Error searching messages", error=str(e))
            raise UseCaseError("search_messages", f"Failed to search messages: {str(e)}")

    async def get_message_statistics(
        self,
        conversation_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> MessageStatsDTO:
        """
        Get message statistics

        Args:
            conversation_id: Optional conversation filter
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            MessageStatsDTO: Message statistics
        """
        try:
            stats = await self.conversation_repository.get_message_statistics(
                conversation_id=conversation_id,
                date_from=date_from,
                date_to=date_to
            )

            return MessageStatsDTO(**stats)

        except Exception as e:
            logger.error("Error getting message statistics", error=str(e))
            raise UseCaseError("get_message_statistics", f"Failed to get statistics: {str(e)}")

    async def perform_bulk_operation(self, bulk_dto: BulkMessageOperationDTO) -> Dict[str, Any]:
        """
        Perform bulk operation on multiple messages

        Args:
            bulk_dto: Bulk operation data

        Returns:
            Dict containing operation results
        """
        try:
            logger.info("Performing bulk message operation",
                       operation=bulk_dto.operation,
                       message_count=len(bulk_dto.message_ids))

            results = {
                "successful": [],
                "failed": [],
                "total_processed": len(bulk_dto.message_ids)
            }

            for message_id in bulk_dto.message_ids:
                try:
                    if bulk_dto.operation == "retry":
                        retry_dto = RetryMessageDTO(
                            message_id=message_id,
                            retry_reason=bulk_dto.parameters.get("reason", "Bulk retry"),
                            max_retries=bulk_dto.parameters.get("max_retries", 3)
                        )
                        await self.retry_failed_message(retry_dto)

                    elif bulk_dto.operation == "mark_sent":
                        update_dto = UpdateMessageDTO(
                            message_id=message_id,
                            status=MessageStatusDTO.SENT
                        )
                        await self.update_message_status(update_dto)

                    elif bulk_dto.operation == "mark_failed":
                        update_dto = UpdateMessageDTO(
                            message_id=message_id,
                            status=MessageStatusDTO.FAILED,
                            error_reason=bulk_dto.parameters.get("reason", "Bulk failure")
                        )
                        await self.update_message_status(update_dto)

                    results["successful"].append(str(message_id))

                except Exception as e:
                    results["failed"].append({
                        "message_id": str(message_id),
                        "error": str(e)
                    })

            logger.info("Bulk operation completed",
                       successful=len(results["successful"]),
                       failed=len(results["failed"]))

            return results

        except Exception as e:
            logger.error("Error performing bulk operation", error=str(e))
            raise UseCaseError("perform_bulk_operation", f"Failed to perform bulk operation: {str(e)}")

    async def send_message_to_platform(
        self,
        message_id: UUID,
        external_user_id: str
    ) -> bool:
        """
        Send message to external platform

        Args:
            message_id: Message identifier
            external_user_id: External user identifier

        Returns:
            True if sent successfully
        """
        try:
            if not self.platform_service:
                raise ExternalServiceError("Platform Service", "send_message", "Platform service not available")

            # Find message
            conversation = await self._find_conversation_by_message_id(message_id)
            if not conversation:
                raise ResourceNotFoundError("Message", str(message_id))

            target_message = None
            for message in conversation.messages:
                if message.id == message_id:
                    target_message = message
                    break

            if not target_message:
                raise ResourceNotFoundError("Message", str(message_id))

            # Send to platform
            send_request = SendMessageRequest(
                external_user_id=external_user_id,
                content=target_message.content
            )

            response = await self.platform_service.send_message(send_request)

            # Update message status
            if response.status == "sent":
                update_dto = UpdateMessageDTO(
                    message_id=message_id,
                    status=MessageStatusDTO.SENT
                )
                await self.update_message_status(update_dto)
                return True
            else:
                update_dto = UpdateMessageDTO(
                    message_id=message_id,
                    status=MessageStatusDTO.FAILED,
                    error_reason=response.error_message
                )
                await self.update_message_status(update_dto)
                return False

        except Exception as e:
            logger.error("Error sending message to platform",
                        message_id=str(message_id),
                        error=str(e))
            raise UseCaseError("send_message_to_platform", f"Failed to send message: {str(e)}")

    # === PRIVATE HELPER METHODS ===

    async def _find_conversation_by_message_id(self, message_id: UUID) -> Optional[Conversation]:
        """Find conversation containing specific message"""
        # This would need to be implemented in the repository
        # For now, this is a placeholder
        return await self.conversation_repository.find_by_message_id(message_id)

    def _domain_to_dto(self, message: Message) -> MessageDTO:
        """Convert Domain Message to DTO"""
        return MessageDTO(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            role=MessageRoleDTO(message.role.value),
            message_type=MessageTypeDTO.TEXT,  # Default
            status=MessageStatusDTO(message.status.value),
            confidence_score=message.confidence_score,
            ai_model=message.ai_model,
            processing_time_ms=message.processing_time_ms,
            error_reason=message.error_reason,
            retry_count=message.retry_count,
            metadata=message.metadata,
            created_at=message.created_at,
            updated_at=message.updated_at,
            sent_at=message.sent_at
        )

    def _dto_to_domain_role(self, dto_role: MessageRoleDTO):
        """Convert DTO role to Domain role"""
        from app.domain.entities.message import MessageRole
        return MessageRole(dto_role.value)

    def _dto_to_domain_status(self, dto_status: MessageStatusDTO):
        """Convert DTO status to Domain status"""
        from app.domain.entities.message import MessageStatus
        return MessageStatus(dto_status.value)