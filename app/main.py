from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
import logging

from app.api.v1 import api_v1_router
from app.core.settings import settings
from app.core.database import init_db, close_db
from app.core.redis_client import _redis_conversation_state as redis_conversation_state
from app.services import _message_handler
# from app.services.job_processor import job_processor

# Tắt hoàn toàn SQLAlchemy logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.orm").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("aioredis").setLevel(logging.WARNING)

# Set root logger level based on settings
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.WARNING))

# Setup structured logging with minimal output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with Redis and PostgreSQL initialization"""

    # ========================================
    # 🚀 STARTUP
    # ========================================
    logger.info("🚀 Starting Chat Bot Backend...")

    try:
        # Initialize Redis connection
        await redis_conversation_state.connect()
        logger.info("✅ Redis connected")

        # Initialize PostgreSQL database
        await init_db()
        logger.info("✅ Database initialized")

        # Initialize MessageHandler and start background processing
        await _message_handler.initialize()
        await _message_handler.start_background_processing()
        logger.info("✅ MessageHandler started")

        logger.info("🎉 Chat Bot Backend ready!")

    except Exception as e:
        logger.error("❌ Failed to start application", error=str(e))
        raise

    yield

    # ========================================
    # 🛑 SHUTDOWN
    # ========================================
    logger.info("🛑 Shutting down...")

    try:
        # Stop MessageHandler background processing
        await _message_handler.stop_background_processing()
        await _message_handler.close()

        # Close Redis connection
        await redis_conversation_state.disconnect()

        # Close database connections
        await close_db()

        logger.info("👋 Shutdown complete")

    except Exception as e:
        logger.error("❌ Error during shutdown", error=str(e))

# 🚀 FastAPI App - Enhanced with Redis & PostgreSQL + Authentication
app = FastAPI(
    title="Enhanced Chat Bot Backend",
    description="Production-ready chat bot backend with Redis state management, PostgreSQL persistence, and dynamic authentication",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router)

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Enhanced Chat Bot Backend",
        "version": "2.0.0",
        "status": "active",
        "architecture": {
            "storage": "Redis + PostgreSQL",
            "race_condition_handling": "Distributed locks",
            "scalability": "Multi-instance ready",
            "authentication": "Dynamic Pancake-based auth"
        },
        "features": [
            "Enhanced race condition handling with Redis",
            "Persistent conversation state",
            "Distributed locks for scalability",
            "PostgreSQL for data persistence",
            "Action extraction and execution",
            "Dynamic authentication system",
            "Pancake endpoint configuration",
            "Admin management APIs"
        ],
        "endpoints": {
            "main_api": "/api/v1/enhanced-handle-message",
            "admin_apis": "/api/v1/admin/*",
            "auth_management": "/api/v1/auth/*",
            "health_check": "/api/v1/health",
            "documentation": "/docs" if settings.DEBUG else "disabled"
        },
        "authentication": {
            "types": ["API Key (X-API-KEY)", "Pancake Token (X-Pancake-Token)"],
            "admin_endpoints": "Require API key",
            "pancake_endpoints": "Dynamic config-based auth",
            "public_endpoints": "No auth required (health, docs)"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint - no auth required"""
    return {
        "status": "healthy",
        "service": "enhanced_chatbot_backend",
        "version": "2.0.0",
        "timestamp": "auto-generated"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )