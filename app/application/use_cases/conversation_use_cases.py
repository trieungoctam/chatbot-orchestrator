"""
Conversation Use Cases
Application services for Conversation management operations
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import structlog

from app.domain.entities.conversation import Conversation
from app.domain.entities.bot import Bot
from app.domain.entities.message import Message
from app.domain.repositories.conversation_repository import IConversationRepository
from app.domain.repositories.bot_repository import IBotRepository
from app.domain.services.conversation_orchestrator import ConversationOrchestrator
from app.domain.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    InvalidOperationError
)
from app.application.dtos.conversation_dtos import (
    StartConversationDTO,
    ProcessMessageDTO,
    AddBotResponseDTO,
    ConversationDTO,
    ConversationListDTO,
    EscalateConversationDTO,
    TransferConversationDTO,
    EndConversationDTO,
    ConversationStatsDTO,
    ConversationSearchDTO,
    UpdateContextDTO,
    ConversationStatusDTO,
    ConversationPriorityDTO,
    ConversationContextDTO
)
from app.application.dtos.message_dtos import MessageDTO, MessageRoleDTO, MessageStatusDTO
from app.application.interfaces.ai_service_interface import IAIService, AIRequest
from app.application.interfaces.platform_service_interface import IPlatformService
from app.application.exceptions import (
    UseCaseError,
    ResourceNotFoundError,
    ValidationError,
    ExternalServiceError
)

logger = structlog.get_logger(__name__)


class ConversationUseCases:
    """
    Application services for Conversation management

    Orchestrates conversation operations and coordinates between Domain and external services
    """

    def __init__(
        self,
        conversation_repository: IConversationRepository,
        bot_repository: IBotRepository,
        ai_service: IAIService,
        platform_service: Optional[IPlatformService] = None
    ):
        self.conversation_repository = conversation_repository
        self.bot_repository = bot_repository
        self.ai_service = ai_service
        self.platform_service = platform_service
        self.orchestrator = ConversationOrchestrator()

    async def start_conversation(self, start_dto: StartConversationDTO) -> Tuple[ConversationDTO, MessageDTO]:
        """
        Start new conversation with business validation

        Args:
            start_dto: Conversation start data

        Returns:
            Tuple[ConversationDTO, MessageDTO]: Created conversation and initial message

        Raises:
            UseCaseError: If conversation creation fails
            ResourceNotFoundError: If bot not found
        """
        try:
            logger.info("Starting new conversation",
                       bot_id=str(start_dto.bot_id),
                       external_user_id=start_dto.external_user_id)

            # Get bot
            bot = await self.bot_repository.get_by_id(start_dto.bot_id)
            if not bot:
                raise ResourceNotFoundError("Bot", str(start_dto.bot_id))

            # Get external user info if platform service available
            external_user_data = start_dto.external_user_data or {}
            if self.platform_service and start_dto.external_user_id:
                try:
                    platform_user = await self.platform_service.get_user_info(start_dto.external_user_id)
                    external_user_data.update({
                        'first_name': platform_user.first_name,
                        'last_name': platform_user.last_name,
                        'username': platform_user.username,
                        'language_code': platform_user.language_code,
                        'is_premium': platform_user.is_premium
                    })
                except Exception as e:
                    logger.warning("Failed to get external user info", error=str(e))

            # Use domain orchestrator to start conversation
            conversation, initial_message = self.orchestrator.start_conversation(
                bot=bot,
                initial_message=start_dto.initial_message,
                external_user_id=start_dto.external_user_id,
                platform=start_dto.platform,
                external_user_data=external_user_data,
                platform_data=start_dto.platform_data
            )

            # Persist conversation
            saved_conversation = await self.conversation_repository.create(conversation)

            # Update bot conversation count
            updated_bot = bot.start_conversation()
            await self.bot_repository.update(updated_bot)

            logger.info("Conversation started successfully",
                       conversation_id=saved_conversation.conversation_id)

            return (
                self._domain_to_dto(saved_conversation),
                self._message_domain_to_dto(initial_message)
            )

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during conversation start", error=str(e))
            raise UseCaseError("start_conversation", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during conversation start", error=str(e))
            raise UseCaseError("start_conversation", f"Failed to start conversation: {str(e)}")

    async def process_user_message(self, process_dto: ProcessMessageDTO) -> Tuple[ConversationDTO, MessageDTO, MessageDTO]:
        """
        Process incoming user message and generate AI response

        Args:
            process_dto: Message processing data

        Returns:
            Tuple[ConversationDTO, MessageDTO, MessageDTO]: Updated conversation, user message, bot response
        """
        try:
            logger.info("Processing user message",
                       conversation_id=process_dto.conversation_id,
                       external_user_id=process_dto.external_user_id)

            # Get conversation
            conversation = await self.conversation_repository.get_by_external_id(process_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", process_dto.conversation_id)

            # Get bot
            bot = await self.bot_repository.get_by_id(conversation.bot_id)
            if not bot:
                raise ResourceNotFoundError("Bot", str(conversation.bot_id))

            # Process user message through orchestrator
            updated_conversation, user_message = self.orchestrator.process_user_message(
                conversation=conversation,
                message_content=process_dto.message_content,
                external_user_id=process_dto.external_user_id,
                metadata=process_dto.metadata
            )

            # Generate AI response
            ai_request = AIRequest(
                message=process_dto.message_content,
                context=updated_conversation.context.get_context_summary(),
                model=bot.config.ai_model,
                temperature=bot.config.ai_temperature,
                max_tokens=bot.config.ai_max_tokens
            )

            ai_response = await self.ai_service.generate_response(ai_request)

            # Add bot response through orchestrator
            final_conversation, bot_message = self.orchestrator.add_bot_response(
                conversation=updated_conversation,
                response_content=ai_response.content,
                confidence_score=ai_response.confidence_score,
                ai_model=ai_response.model,
                processing_time_ms=ai_response.processing_time_ms
            )

            # Persist updates
            saved_conversation = await self.conversation_repository.update(final_conversation)

            # Send response to platform if available
            if self.platform_service:
                try:
                    from app.application.interfaces.platform_service_interface import SendMessageRequest
                    send_request = SendMessageRequest(
                        external_user_id=process_dto.external_user_id,
                        content=ai_response.content
                    )
                    await self.platform_service.send_message(send_request)
                except Exception as e:
                    logger.warning("Failed to send message to platform", error=str(e))

            logger.info("User message processed successfully",
                       conversation_id=process_dto.conversation_id)

            return (
                self._domain_to_dto(saved_conversation),
                self._message_domain_to_dto(user_message),
                self._message_domain_to_dto(bot_message)
            )

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during message processing", error=str(e))
            raise UseCaseError("process_user_message", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during message processing", error=str(e))
            raise UseCaseError("process_user_message", f"Failed to process message: {str(e)}")

    async def escalate_conversation(self, escalate_dto: EscalateConversationDTO) -> ConversationDTO:
        """
        Escalate conversation to human agent

        Args:
            escalate_dto: Escalation data

        Returns:
            ConversationDTO: Updated conversation
        """
        try:
            logger.info("Escalating conversation",
                       conversation_id=escalate_dto.conversation_id)

            # Get conversation
            conversation = await self.conversation_repository.get_by_external_id(escalate_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", escalate_dto.conversation_id)

            # Escalate through orchestrator
            escalated_conversation = self.orchestrator.escalate_conversation(
                conversation=conversation,
                reason=escalate_dto.reason,
                escalated_by=escalate_dto.escalated_by
            )

            # Update priority if specified
            if escalate_dto.new_priority:
                priority = self._dto_to_domain_priority(escalate_dto.new_priority)
                escalated_conversation = escalated_conversation.escalate_priority(priority, escalate_dto.reason)

            # Persist
            saved_conversation = await self.conversation_repository.update(escalated_conversation)

            logger.info("Conversation escalated successfully",
                       conversation_id=escalate_dto.conversation_id)

            return self._domain_to_dto(saved_conversation)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during escalation", error=str(e))
            raise UseCaseError("escalate_conversation", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during escalation", error=str(e))
            raise UseCaseError("escalate_conversation", f"Failed to escalate: {str(e)}")

    async def transfer_conversation(self, transfer_dto: TransferConversationDTO) -> ConversationDTO:
        """
        Transfer conversation to different bot

        Args:
            transfer_dto: Transfer data

        Returns:
            ConversationDTO: Updated conversation
        """
        try:
            logger.info("Transferring conversation",
                       conversation_id=transfer_dto.conversation_id,
                       target_bot_id=str(transfer_dto.target_bot_id))

            # Get conversation
            conversation = await self.conversation_repository.get_by_external_id(transfer_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", transfer_dto.conversation_id)

            # Get target bot
            target_bot = await self.bot_repository.get_by_id(transfer_dto.target_bot_id)
            if not target_bot:
                raise ResourceNotFoundError("Bot", str(transfer_dto.target_bot_id))

            # Get current bot for conversation count updates
            current_bot = await self.bot_repository.get_by_id(conversation.bot_id)

            # Transfer through orchestrator
            transferred_conversation = self.orchestrator.transfer_conversation(
                conversation=conversation,
                target_bot=target_bot,
                reason=transfer_dto.reason,
                transferred_by=transfer_dto.transferred_by
            )

            # Persist
            saved_conversation = await self.conversation_repository.update(transferred_conversation)

            # Update bot conversation counts
            if current_bot:
                updated_current_bot = current_bot.end_conversation()
                await self.bot_repository.update(updated_current_bot)

            updated_target_bot = target_bot.start_conversation()
            await self.bot_repository.update(updated_target_bot)

            logger.info("Conversation transferred successfully",
                       conversation_id=transfer_dto.conversation_id)

            return self._domain_to_dto(saved_conversation)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during transfer", error=str(e))
            raise UseCaseError("transfer_conversation", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during transfer", error=str(e))
            raise UseCaseError("transfer_conversation", f"Failed to transfer: {str(e)}")

    async def end_conversation(self, end_dto: EndConversationDTO) -> ConversationDTO:
        """
        End conversation with proper cleanup

        Args:
            end_dto: End conversation data

        Returns:
            ConversationDTO: Ended conversation
        """
        try:
            logger.info("Ending conversation", conversation_id=end_dto.conversation_id)

            # Get conversation
            conversation = await self.conversation_repository.get_by_external_id(end_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", end_dto.conversation_id)

            # End through orchestrator
            ended_conversation = self.orchestrator.end_conversation(
                conversation=conversation,
                reason=end_dto.reason,
                ended_by=end_dto.ended_by
            )

            # Persist
            saved_conversation = await self.conversation_repository.update(ended_conversation)

            # Update bot conversation count
            bot = await self.bot_repository.get_by_id(conversation.bot_id)
            if bot:
                updated_bot = bot.end_conversation()
                await self.bot_repository.update(updated_bot)

            logger.info("Conversation ended successfully",
                       conversation_id=end_dto.conversation_id)

            return self._domain_to_dto(saved_conversation)

        except BusinessRuleViolationError as e:
            logger.error("Business rule violation during conversation end", error=str(e))
            raise UseCaseError("end_conversation", str(e), e.error_code)
        except Exception as e:
            logger.error("Unexpected error during conversation end", error=str(e))
            raise UseCaseError("end_conversation", f"Failed to end conversation: {str(e)}")

    async def get_conversation_by_id(self, conversation_id: str) -> ConversationDTO:
        """
        Get conversation by external ID

        Args:
            conversation_id: External conversation ID

        Returns:
            ConversationDTO: Conversation information
        """
        try:
            conversation = await self.conversation_repository.get_by_external_id(conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", conversation_id)

            return self._domain_to_dto(conversation)

        except Exception as e:
            logger.error("Error getting conversation", conversation_id=conversation_id, error=str(e))
            raise UseCaseError("get_conversation_by_id", f"Failed to get conversation: {str(e)}")

    async def search_conversations(self, search_dto: ConversationSearchDTO) -> ConversationListDTO:
        """
        Search conversations with filters

        Args:
            search_dto: Search criteria

        Returns:
            ConversationListDTO: List of matching conversations
        """
        try:
            logger.info("Searching conversations", query=search_dto.query)

            # Convert DTO filters to repository format
            filters = {}
            if search_dto.bot_id:
                filters['bot_id'] = search_dto.bot_id
            if search_dto.status:
                filters['status'] = self._dto_to_domain_status(search_dto.status)
            if search_dto.priority:
                filters['priority'] = self._dto_to_domain_priority(search_dto.priority)
            if search_dto.platform:
                filters['platform'] = search_dto.platform
            if search_dto.external_user_id:
                filters['external_user_id'] = search_dto.external_user_id
            if search_dto.date_from:
                filters['date_from'] = search_dto.date_from
            if search_dto.date_to:
                filters['date_to'] = search_dto.date_to

            # Search
            conversations, total_count = await self.conversation_repository.search(
                query=search_dto.query,
                filters=filters,
                page=search_dto.page,
                page_size=search_dto.page_size,
                sort_by=search_dto.sort_by,
                sort_order=search_dto.sort_order
            )

            # Convert to DTOs
            conversation_dtos = [self._domain_to_dto(conv) for conv in conversations]

            return ConversationListDTO(
                conversations=conversation_dtos,
                total_count=total_count,
                page=search_dto.page,
                page_size=search_dto.page_size,
                has_next=(search_dto.page * search_dto.page_size) < total_count,
                has_previous=search_dto.page > 1
            )

        except Exception as e:
            logger.error("Error searching conversations", error=str(e))
            raise UseCaseError("search_conversations", f"Failed to search conversations: {str(e)}")

    async def update_conversation_context(self, update_dto: UpdateContextDTO) -> ConversationDTO:
        """
        Update conversation context

        Args:
            update_dto: Context update data

        Returns:
            ConversationDTO: Updated conversation
        """
        try:
            logger.info("Updating conversation context",
                       conversation_id=update_dto.conversation_id)

            # Get conversation
            conversation = await self.conversation_repository.get_by_external_id(update_dto.conversation_id)
            if not conversation:
                raise ResourceNotFoundError("Conversation", update_dto.conversation_id)

            # Update context
            updated_context = conversation.context

            if update_dto.external_user_data:
                updated_context = updated_context.update_external_user_data(update_dto.external_user_data)

            if update_dto.intent and update_dto.intent_confidence:
                updated_context = updated_context.add_intent(update_dto.intent, update_dto.intent_confidence)

            if update_dto.entities:
                for entity_type, entity_value in update_dto.entities.items():
                    updated_context = updated_context.add_entity(entity_type, entity_value)

            if update_dto.sentiment and update_dto.sentiment_score is not None:
                updated_context = updated_context.update_sentiment(update_dto.sentiment, update_dto.sentiment_score)

            if update_dto.system_note:
                updated_context = updated_context.add_system_note(update_dto.system_note)

            if update_dto.flags_to_add:
                for flag in update_dto.flags_to_add:
                    updated_context = updated_context.add_flag(flag)

            if update_dto.flags_to_remove:
                for flag in update_dto.flags_to_remove:
                    updated_context = updated_context.remove_flag(flag)

            # Update conversation
            updated_conversation = conversation._replace(context=updated_context)

            # Persist
            saved_conversation = await self.conversation_repository.update(updated_conversation)

            logger.info("Conversation context updated successfully",
                       conversation_id=update_dto.conversation_id)

            return self._domain_to_dto(saved_conversation)

        except Exception as e:
            logger.error("Error updating conversation context",
                        conversation_id=update_dto.conversation_id,
                        error=str(e))
            raise UseCaseError("update_conversation_context", f"Failed to update context: {str(e)}")

    # === PRIVATE HELPER METHODS ===

    def _domain_to_dto(self, conversation: Conversation) -> ConversationDTO:
        """Convert Domain Conversation to DTO"""
        return ConversationDTO(
            id=conversation.id,
            conversation_id=conversation.conversation_id,
            bot_id=conversation.bot_id,
            status=self._domain_to_dto_status(conversation.status),
            priority=self._domain_to_dto_priority(conversation.priority),
            context=self._context_domain_to_dto(conversation.context),
            participants=conversation.participants,
            message_count=len(conversation.messages),
            max_messages=conversation.max_messages,
            timeout_minutes=conversation.timeout_minutes,
            max_idle_minutes=conversation.max_idle_minutes,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            last_activity_at=conversation.last_activity_at
        )

    def _context_domain_to_dto(self, context) -> ConversationContextDTO:
        """Convert Domain ConversationContext to DTO"""
        return ConversationContextDTO(
            external_user_id=context.external_user_id,
            platform=context.platform,
            external_user_data=context.external_user_data,
            user_preferences=context.user_preferences,
            intent_history=context.intent_history,
            entity_storage=context.entity_storage,
            conversation_summary=context.conversation_summary,
            current_sentiment=context.current_sentiment,
            sentiment_score=context.sentiment_score,
            confidence_levels=context.confidence_levels,
            system_notes=context.system_notes,
            flags=context.flags,
            metadata=context.metadata
        )

    def _message_domain_to_dto(self, message: Message) -> MessageDTO:
        """Convert Domain Message to DTO"""
        from app.application.dtos.message_dtos import MessageTypeDTO

        return MessageDTO(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            role=MessageRoleDTO(message.role.value),
            message_type=MessageTypeDTO.TEXT,  # Default to text
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

    def _dto_to_domain_status(self, dto_status: ConversationStatusDTO):
        """Convert DTO status to Domain status"""
        from app.domain.entities.conversation import ConversationStatus
        return ConversationStatus(dto_status.value)

    def _domain_to_dto_status(self, domain_status) -> ConversationStatusDTO:
        """Convert Domain status to DTO status"""
        return ConversationStatusDTO(domain_status.value)

    def _dto_to_domain_priority(self, dto_priority: ConversationPriorityDTO):
        """Convert DTO priority to Domain priority"""
        from app.domain.entities.conversation import ConversationPriority
        return ConversationPriority(dto_priority.value)

    def _domain_to_dto_priority(self, domain_priority) -> ConversationPriorityDTO:
        """Convert Domain priority to DTO priority"""
        return ConversationPriorityDTO(domain_priority.value)