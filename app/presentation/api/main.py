"""
FastAPI Main Application
Main application setup with routers, middleware, and configuration using centralized config
"""
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time

from app.infrastructure.database.session import init_database, close_database
from app.infrastructure.config import get_settings, get_configuration_factory
from app.presentation.api.routers import (
    bots_router,
    conversations_router,
    messages_router,
    health_router
)
from app.presentation.middleware.error_handler import ErrorHandlerMiddleware
from app.presentation.middleware.request_logging import RequestLoggingMiddleware
from app.application.exceptions import ApplicationError

logger = structlog.get_logger(__name__)

# Global app instance
_app: Optional[FastAPI] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with configuration-based initialization"""
    # Startup
    settings = get_settings()
    logger.info("Starting Chat Orchestrator API",
                environment=settings.environment,
                debug=settings.debug)

    try:
        # Initialize infrastructure using configuration factory
        factory = get_configuration_factory()
        await factory.initialize_infrastructure()
        logger.info("Infrastructure initialized successfully")

        yield

    finally:
        # Shutdown
        logger.info("Shutting down Chat Orchestrator API")
        await close_database()
        logger.info("Application shutdown completed")


def create_app(
    title: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    debug: Optional[bool] = None,
    use_config: bool = True
) -> FastAPI:
    """
    Create FastAPI application with centralized configuration

    Args:
        title: API title (overrides config)
        description: API description (overrides config)
        version: API version (overrides config)
        debug: Enable debug mode (overrides config)
        use_config: Whether to use centralized configuration

    Returns:
        Configured FastAPI application
    """
    global _app

    # Get configuration
    if use_config:
        settings = get_settings()

        # Use config values with parameter overrides
        app_title = title or settings.app_name
        app_description = description or settings.app_description
        app_version = version or settings.app_version
        app_debug = debug if debug is not None else settings.debug

        # Configure docs based on environment
        docs_url = settings.docs_url if settings.enable_docs else None
        redoc_url = settings.redoc_url if settings.enable_docs else None
    else:
        # Fallback values
        app_title = title or "Chat Orchestrator API"
        app_description = description or "Chat Orchestrator Core Backend API"
        app_version = version or "1.0.0"
        app_debug = debug if debug is not None else False
        docs_url = "/docs" if app_debug else None
        redoc_url = "/redoc" if app_debug else None

    # Create FastAPI app
    app = FastAPI(
        title=app_title,
        description=app_description,
        version=app_version,
        debug=app_debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan
    )

    # Configure middleware based on settings
    setup_middleware(app, use_config)

    # Add routers
    setup_routers(app)

    # Add exception handlers
    setup_exception_handlers(app)

    _app = app
    logger.info("FastAPI application created",
                title=app_title,
                version=app_version,
                debug=app_debug,
                docs_enabled=bool(docs_url))

    return app


def setup_middleware(app: FastAPI, use_config: bool = True):
    """Setup application middleware using configuration"""

    if use_config:
        settings = get_settings()
        security_config = settings.security

        # CORS middleware with configuration
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_config.cors_origins_list,
            allow_credentials=security_config.cors_allow_credentials,
            allow_methods=security_config.cors_allow_methods.split(','),
            allow_headers=security_config.cors_allow_headers.split(','),
        )

        # Trusted host middleware with configuration
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=security_config.trusted_hosts_list
        )
    else:
        # Fallback middleware configuration
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]
        )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)


def setup_routers(app: FastAPI):
    """Setup API routers"""

    # Health check (no prefix)
    app.include_router(health_router, tags=["Health"])

    # API v1 routes
    api_prefix = "/api/v1"

    app.include_router(
        bots_router,
        prefix=f"{api_prefix}/bots",
        tags=["Bots"]
    )

    app.include_router(
        conversations_router,
        prefix=f"{api_prefix}/conversations",
        tags=["Conversations"]
    )

    app.include_router(
        messages_router,
        prefix=f"{api_prefix}/messages",
        tags=["Messages"]
    )


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError):
        """Handle application layer errors"""
        logger.error("Application error",
                    error_code=exc.error_code,
                    message=exc.message,
                    details=exc.details,
                    path=request.url.path)

        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        logger.warning("HTTP exception",
                      status_code=exc.status_code,
                      detail=exc.detail,
                      path=request.url.path)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail
                }
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle validation errors"""
        logger.error("Validation error",
                    error=str(exc),
                    path=request.url.path)

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc)
                }
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors"""
        logger.error("Unexpected error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    path=request.url.path)

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            }
        )


def get_app() -> FastAPI:
    """Get the current FastAPI application instance"""
    if _app is None:
        return create_app()
    return _app


# Create default app instance using configuration
settings = get_settings()
app = create_app(
    debug=settings.debug,
    use_config=True
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information from configuration"""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "docs": settings.docs_url if settings.enable_docs else None,
        "health": settings.health_check_path
    }


# API Info endpoint
@app.get("/info")
async def api_info():
    """Get API information and configuration details"""
    settings = get_settings()

    return {
        "api": {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": settings.app_description,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "endpoints": {
            "health": settings.health_check_path,
            "bots": "/api/v1/bots",
            "conversations": "/api/v1/conversations",
            "messages": "/api/v1/messages"
        },
        "documentation": {
            "swagger": settings.docs_url if settings.enable_docs else None,
            "redoc": settings.redoc_url if settings.enable_docs else None
        },
        "features": {
            "cors_enabled": bool(settings.security.cors_origins),
            "rate_limiting": settings.security.enable_rate_limiting,
            "content_filtering": settings.ai_service.enable_content_filtering
        }
    }