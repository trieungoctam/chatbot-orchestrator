"""
Presentation Layer - Chat Orchestrator

This layer contains the API endpoints and request/response handling:
- REST API endpoints using FastAPI
- Request/Response models (Pydantic)
- Controllers and routers
- Authentication and authorization
- API documentation
- Error handling middleware

Components:
- api: REST API routers and endpoints
- models: Request/Response Pydantic models
- middleware: Request/Response middleware
- auth: Authentication and authorization
- dependencies: Dependency injection
"""

from .api import create_app, get_app
from .api.main import app

__all__ = [
    "create_app",
    "get_app",
    "app"
]