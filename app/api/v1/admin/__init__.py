from fastapi import APIRouter
from .bot_api import router as bot_api_router
from .platform_api import router as platform_api_router
from .core_ai_api import router as core_ai_api_router
from .conversation_api import router as conversation_api_router
# from .monitor_api import router as monitor_api_router

# 🔥 CLEAN API V1 - Only Essential Endpoints (removed redundant APIs)
router = APIRouter(prefix="/admin")

# 🔐 Authentication Management (Essential for system management)
router.include_router(bot_api_router, tags=["Bot API"])
router.include_router(platform_api_router, tags=["Platform API"])
router.include_router(core_ai_api_router, tags=["Core AI API"])
router.include_router(conversation_api_router, tags=["Conversation API"])
# router.include_router(monitor_api_router, tags=["Monitor API"])