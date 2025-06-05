from fastapi import APIRouter
from .admin import router as admin_api_router
from .chat_api import router as chat_api_router

# 🔥 CLEAN API V1 - Only Essential Endpoints (removed redundant APIs)
api_v1_router = APIRouter(prefix="/api/v1")

# 🔐 Authentication Management (Essential for system management)
api_v1_router.include_router(admin_api_router)

# 🚀 Enhanced Message Processing (New consolidated lock management system)
api_v1_router.include_router(chat_api_router, tags=["Chat API"])