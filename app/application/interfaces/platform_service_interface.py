"""
Platform Service Interface
Contract for external platform integrations (Telegram, Facebook, etc.)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class PlatformType(Enum):
    """Supported platform types"""
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WEBCHAT = "webchat"


@dataclass
class PlatformMessage:
    """Platform message structure"""
    external_message_id: str
    external_user_id: str
    content: str
    message_type: str  # text, image, audio, etc.
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class PlatformUser:
    """Platform user information"""
    external_user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: bool = False
    metadata: Dict[str, Any] = None


@dataclass
class SendMessageRequest:
    """Request to send message to platform"""
    external_user_id: str
    content: str
    message_type: str = "text"
    reply_to_message_id: Optional[str] = None
    keyboard: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SendMessageResponse:
    """Response from platform message send"""
    external_message_id: str
    status: str
    sent_at: str
    error_message: Optional[str] = None


class IPlatformService(ABC):
    """Interface for platform service integrations"""

    @abstractmethod
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """
        Send message to platform user

        Args:
            request: Message send request

        Returns:
            SendMessageResponse: Result of message send

        Raises:
            ExternalServiceError: If platform service fails
        """
        pass

    @abstractmethod
    async def get_user_info(self, external_user_id: str) -> PlatformUser:
        """
        Get user information from platform

        Args:
            external_user_id: Platform-specific user ID

        Returns:
            PlatformUser: User information
        """
        pass

    @abstractmethod
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set webhook URL for receiving messages

        Args:
            webhook_url: URL to receive webhooks

        Returns:
            True if webhook set successfully
        """
        pass

    @abstractmethod
    async def delete_webhook(self) -> bool:
        """
        Delete webhook configuration

        Returns:
            True if webhook deleted successfully
        """
        pass

    @abstractmethod
    async def get_webhook_info(self) -> Dict[str, Any]:
        """
        Get current webhook configuration

        Returns:
            Dict containing webhook information
        """
        pass

    @abstractmethod
    async def send_typing_action(self, external_user_id: str) -> bool:
        """
        Send typing indicator to user

        Args:
            external_user_id: Platform-specific user ID

        Returns:
            True if typing action sent successfully
        """
        pass

    @abstractmethod
    async def send_read_receipt(self, external_message_id: str) -> bool:
        """
        Mark message as read

        Args:
            external_message_id: Platform-specific message ID

        Returns:
            True if read receipt sent successfully
        """
        pass

    @abstractmethod
    async def upload_media(
        self,
        file_path: str,
        media_type: str
    ) -> Dict[str, Any]:
        """
        Upload media file to platform

        Args:
            file_path: Path to media file
            media_type: Type of media (image, audio, video, document)

        Returns:
            Dict containing media upload information
        """
        pass

    @abstractmethod
    async def download_media(
        self,
        external_file_id: str,
        destination_path: str
    ) -> bool:
        """
        Download media file from platform

        Args:
            external_file_id: Platform-specific file ID
            destination_path: Local path to save file

        Returns:
            True if download successful
        """
        pass

    @abstractmethod
    async def get_chat_info(self, external_chat_id: str) -> Dict[str, Any]:
        """
        Get chat/group information

        Args:
            external_chat_id: Platform-specific chat ID

        Returns:
            Dict containing chat information
        """
        pass

    @abstractmethod
    async def get_chat_members(self, external_chat_id: str) -> List[PlatformUser]:
        """
        Get chat members list

        Args:
            external_chat_id: Platform-specific chat ID

        Returns:
            List of chat members
        """
        pass

    @abstractmethod
    async def ban_user(
        self,
        external_chat_id: str,
        external_user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Ban user from chat

        Args:
            external_chat_id: Platform-specific chat ID
            external_user_id: Platform-specific user ID
            reason: Ban reason

        Returns:
            True if user banned successfully
        """
        pass

    @abstractmethod
    async def unban_user(
        self,
        external_chat_id: str,
        external_user_id: str
    ) -> bool:
        """
        Unban user from chat

        Args:
            external_chat_id: Platform-specific chat ID
            external_user_id: Platform-specific user ID

        Returns:
            True if user unbanned successfully
        """
        pass

    @abstractmethod
    async def delete_message(
        self,
        external_chat_id: str,
        external_message_id: str
    ) -> bool:
        """
        Delete message from chat

        Args:
            external_chat_id: Platform-specific chat ID
            external_message_id: Platform-specific message ID

        Returns:
            True if message deleted successfully
        """
        pass

    @abstractmethod
    async def edit_message(
        self,
        external_chat_id: str,
        external_message_id: str,
        new_content: str
    ) -> bool:
        """
        Edit existing message

        Args:
            external_chat_id: Platform-specific chat ID
            external_message_id: Platform-specific message ID
            new_content: New message content

        Returns:
            True if message edited successfully
        """
        pass

    @abstractmethod
    async def get_platform_capabilities(self) -> Dict[str, Any]:
        """
        Get platform capabilities and features

        Returns:
            Dict containing platform capabilities
        """
        pass

    @abstractmethod
    async def validate_external_user_id(self, external_user_id: str) -> bool:
        """
        Validate if external user ID is valid for this platform

        Args:
            external_user_id: Platform-specific user ID

        Returns:
            True if user ID is valid
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if platform service is healthy

        Returns:
            True if service is healthy
        """
        pass

    @abstractmethod
    def get_platform_type(self) -> PlatformType:
        """
        Get platform type

        Returns:
            PlatformType: Type of this platform
        """
        pass

    @abstractmethod
    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get platform rate limits

        Returns:
            Dict containing rate limit information
        """
        pass