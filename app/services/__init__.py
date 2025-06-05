from .message_handler import MessageHandler

# Global enhanced message handler instance
_message_handler = MessageHandler()

async def get_message_handler():
    return _message_handler

__all__ = [
    "MessageHandler",
    "get_message_handler"
]