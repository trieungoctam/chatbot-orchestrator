from .message_handler import MessageHandler

# Global enhanced message handler instance
_message_handler = MessageHandler()

async def get_message_handler():
    """Get message handler instance (initialized during application startup)"""
    return _message_handler

__all__ = [
    "MessageHandler",
    "get_message_handler",
    "_message_handler"  # Export for use in main.py
]