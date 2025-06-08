"""
FastAPI Application Factory
Creates and configures the FastAPI application
"""

from .main import create_app, get_app

__all__ = ["create_app", "get_app"]