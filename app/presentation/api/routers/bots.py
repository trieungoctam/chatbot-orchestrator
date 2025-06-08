"""
Bots API Router
FastAPI router for bot management endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.application.use_cases.bot_use_cases import BotUseCases
from app.application.dtos.bot_dtos import (
    CreateBotDTO, UpdateBotDTO, BotDTO, BotListDTO,
    BotStatsDTO, BotOperationDTO, BotSearchDTO,
    BotTypeDTO, BotStatusDTO, BotConfigDTO
)
from app.presentation.models.bot_models import (
    CreateBotRequest, UpdateBotRequest, BotResponse,
    BotListResponse, BotStatsResponse, BotOperationRequest,
    BotSearchRequest
)
from app.presentation.dependencies import get_bot_use_cases
from app.application.exceptions import ApplicationError

router = APIRouter()


@router.post(
    "/",
    response_model=BotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new bot",
    description="Create a new chatbot with specified configuration"
)
async def create_bot(
    request: CreateBotRequest,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotResponse:
    """Create a new bot"""
    try:
        # Convert request to DTO
        create_dto = CreateBotDTO(
            name=request.name,
            description=request.description,
            bot_type=BotTypeDTO(request.bot_type),
            language=request.language,
            core_ai_id=request.core_ai_id,
            platform_id=request.platform_id,
            config=BotConfigDTO(
                ai_provider=request.config.ai_provider,
                ai_model=request.config.ai_model,
                ai_temperature=request.config.ai_temperature,
                ai_max_tokens=request.config.ai_max_tokens,
                platform_type=request.config.platform_type,
                max_concurrent_users=request.config.max_concurrent_users,
                max_conversation_length=request.config.max_conversation_length,
                enable_sentiment_analysis=request.config.enable_sentiment_analysis,
                enable_intent_recognition=request.config.enable_intent_recognition,
                response_timeout_seconds=request.config.response_timeout_seconds,
                supported_languages=request.config.supported_languages
            )
        )

        # Execute use case
        bot_dto = await bot_use_cases.create_bot(create_dto)

        # Convert to response model
        return BotResponse.from_dto(bot_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/{bot_id}",
    response_model=BotResponse,
    summary="Get bot by ID",
    description="Retrieve a specific bot by its ID"
)
async def get_bot(
    bot_id: UUID,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotResponse:
    """Get bot by ID"""
    try:
        bot_dto = await bot_use_cases.get_bot_by_id(bot_id)

        if not bot_dto:
            raise HTTPException(
                status_code=404,
                detail={"code": "BOT_NOT_FOUND", "message": f"Bot with ID {bot_id} not found"}
            )

        return BotResponse.from_dto(bot_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.put(
    "/{bot_id}",
    response_model=BotResponse,
    summary="Update bot",
    description="Update an existing bot's configuration"
)
async def update_bot(
    bot_id: UUID,
    request: UpdateBotRequest,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotResponse:
    """Update bot"""
    try:
        # Convert request to DTO
        update_dto = UpdateBotDTO(
            name=request.name,
            description=request.description,
            bot_type=BotTypeDTO(request.bot_type) if request.bot_type else None,
            language=request.language,
            config=BotConfigDTO(
                ai_provider=request.config.ai_provider,
                ai_model=request.config.ai_model,
                ai_temperature=request.config.ai_temperature,
                ai_max_tokens=request.config.ai_max_tokens,
                platform_type=request.config.platform_type,
                max_concurrent_users=request.config.max_concurrent_users,
                max_conversation_length=request.config.max_conversation_length,
                enable_sentiment_analysis=request.config.enable_sentiment_analysis,
                enable_intent_recognition=request.config.enable_intent_recognition,
                response_timeout_seconds=request.config.response_timeout_seconds,
                supported_languages=request.config.supported_languages
            ) if request.config else None
        )

        # Execute use case
        bot_dto = await bot_use_cases.update_bot(bot_id, update_dto)

        return BotResponse.from_dto(bot_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.delete(
    "/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete bot",
    description="Soft delete a bot (deactivate)"
)
async def delete_bot(
    bot_id: UUID,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
):
    """Delete bot"""
    try:
        success = await bot_use_cases.delete_bot(bot_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail={"code": "BOT_NOT_FOUND", "message": f"Bot with ID {bot_id} not found"}
            )

        return JSONResponse(
            status_code=204,
            content={"message": "Bot deleted successfully"}
        )

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post(
    "/search",
    response_model=BotListResponse,
    summary="Search bots",
    description="Search bots with filters and pagination"
)
async def search_bots(
    request: BotSearchRequest,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotListResponse:
    """Search bots"""
    try:
        # Convert request to DTO
        search_dto = BotSearchDTO(
            query=request.query,
            bot_type=BotTypeDTO(request.bot_type) if request.bot_type else None,
            status=BotStatusDTO(request.status) if request.status else None,
            language=request.language,
            platform_id=request.platform_id,
            is_active=request.is_active,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )

        # Execute use case
        bot_list_dto = await bot_use_cases.search_bots(search_dto)

        return BotListResponse.from_dto(bot_list_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/",
    response_model=BotListResponse,
    summary="List bots",
    description="Get paginated list of bots with optional filters"
)
async def list_bots(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    bot_type: Optional[str] = Query(None, description="Filter by bot type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotListResponse:
    """List bots with filters"""
    try:
        # Create search DTO
        search_dto = BotSearchDTO(
            bot_type=BotTypeDTO(bot_type) if bot_type else None,
            status=BotStatusDTO(status) if status else None,
            is_active=is_active,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Execute use case
        bot_list_dto = await bot_use_cases.search_bots(search_dto)

        return BotListResponse.from_dto(bot_list_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post(
    "/{bot_id}/operations",
    response_model=BotResponse,
    summary="Perform bot operation",
    description="Perform operations like activate, deactivate, start/end maintenance"
)
async def perform_bot_operation(
    bot_id: UUID,
    request: BotOperationRequest,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotResponse:
    """Perform bot operation"""
    try:
        # Convert request to DTO
        operation_dto = BotOperationDTO(
            bot_id=bot_id,
            operation=request.operation,
            parameters=request.parameters
        )

        # Execute use case
        bot_dto = await bot_use_cases.perform_bot_operation(operation_dto)

        return BotResponse.from_dto(bot_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/{bot_id}/statistics",
    response_model=BotStatsResponse,
    summary="Get bot statistics",
    description="Get detailed statistics for a bot"
)
async def get_bot_statistics(
    bot_id: UUID,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
) -> BotStatsResponse:
    """Get bot statistics"""
    try:
        stats_dto = await bot_use_cases.get_bot_statistics(bot_id)

        if not stats_dto:
            raise HTTPException(
                status_code=404,
                detail={"code": "BOT_NOT_FOUND", "message": f"Bot with ID {bot_id} not found"}
            )

        return BotStatsResponse.from_dto(stats_dto)

    except ApplicationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )