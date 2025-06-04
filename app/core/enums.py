from enum import Enum, auto


class SenderType(str, Enum):
    """Type of sender (user or bot)."""

    USER = "USER"
    BOT = "BOT"


class Direction(str, Enum):
    """Direction of the message flow."""

    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"


class Action(str, Enum):
    """Actions that can be triggered based on conversation analysis."""

    # General interaction actions
    ASK = "ASK"  # General inquiry
    RESPOND = "RESPOND"  # Standard response

    # Support related actions
    NEED_SUPPORT = "NEED_SUPPORT"  # User needs technical support
    ESCALATE = "ESCALATE"  # Escalate to human agent

    # Sales related actions
    NEED_SALE = "NEED_SALE"  # User shows purchase intent
    NEED_PRICING = "NEED_PRICING"  # User asks about pricing
    ORDER_SIGNAL = "ORDER_SIGNAL"  # User indicates readiness to order