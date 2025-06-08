"""
Notification Service Interface
Contract for notification services (email, SMS, push notifications, etc.)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    """Notification types"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationPriority(Enum):
    """Notification priorities"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationRequest:
    """Notification request"""
    recipient: str
    subject: str
    content: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None


@dataclass
class NotificationResponse:
    """Notification response"""
    notification_id: str
    status: str
    sent_at: str
    error_message: Optional[str] = None
    delivery_status: Optional[str] = None


@dataclass
class NotificationTemplate:
    """Notification template"""
    template_id: str
    name: str
    subject_template: str
    content_template: str
    notification_type: NotificationType
    variables: List[str]
    is_active: bool


class INotificationService(ABC):
    """Interface for notification services"""

    @abstractmethod
    async def send_notification(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send notification

        Args:
            request: Notification request

        Returns:
            NotificationResponse: Result of notification send

        Raises:
            ExternalServiceError: If notification service fails
        """
        pass

    @abstractmethod
    async def send_bulk_notifications(
        self,
        requests: List[NotificationRequest]
    ) -> List[NotificationResponse]:
        """
        Send multiple notifications

        Args:
            requests: List of notification requests

        Returns:
            List of notification responses
        """
        pass

    @abstractmethod
    async def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """
        Get notification delivery status

        Args:
            notification_id: Notification ID

        Returns:
            Dict containing notification status
        """
        pass

    @abstractmethod
    async def cancel_notification(self, notification_id: str) -> bool:
        """
        Cancel pending notification

        Args:
            notification_id: Notification ID

        Returns:
            True if notification cancelled successfully
        """
        pass

    @abstractmethod
    async def schedule_notification(
        self,
        request: NotificationRequest,
        send_at: str
    ) -> NotificationResponse:
        """
        Schedule notification for later delivery

        Args:
            request: Notification request
            send_at: ISO datetime string for when to send

        Returns:
            NotificationResponse: Scheduled notification info
        """
        pass

    @abstractmethod
    async def create_template(self, template: NotificationTemplate) -> bool:
        """
        Create notification template

        Args:
            template: Template definition

        Returns:
            True if template created successfully
        """
        pass

    @abstractmethod
    async def update_template(
        self,
        template_id: str,
        template: NotificationTemplate
    ) -> bool:
        """
        Update notification template

        Args:
            template_id: Template ID
            template: Updated template definition

        Returns:
            True if template updated successfully
        """
        pass

    @abstractmethod
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete notification template

        Args:
            template_id: Template ID

        Returns:
            True if template deleted successfully
        """
        pass

    @abstractmethod
    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """
        Get notification template

        Args:
            template_id: Template ID

        Returns:
            NotificationTemplate if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_templates(
        self,
        notification_type: Optional[NotificationType] = None
    ) -> List[NotificationTemplate]:
        """
        List notification templates

        Args:
            notification_type: Filter by notification type

        Returns:
            List of templates
        """
        pass

    @abstractmethod
    async def validate_recipient(
        self,
        recipient: str,
        notification_type: NotificationType
    ) -> bool:
        """
        Validate recipient address/ID

        Args:
            recipient: Recipient address/ID
            notification_type: Type of notification

        Returns:
            True if recipient is valid
        """
        pass

    @abstractmethod
    async def get_delivery_statistics(
        self,
        date_from: str,
        date_to: str
    ) -> Dict[str, Any]:
        """
        Get notification delivery statistics

        Args:
            date_from: Start date (ISO format)
            date_to: End date (ISO format)

        Returns:
            Dict containing delivery statistics
        """
        pass

    @abstractmethod
    async def subscribe_to_topic(
        self,
        recipient: str,
        topic: str,
        notification_type: NotificationType
    ) -> bool:
        """
        Subscribe recipient to notification topic

        Args:
            recipient: Recipient address/ID
            topic: Topic name
            notification_type: Type of notification

        Returns:
            True if subscribed successfully
        """
        pass

    @abstractmethod
    async def unsubscribe_from_topic(
        self,
        recipient: str,
        topic: str,
        notification_type: NotificationType
    ) -> bool:
        """
        Unsubscribe recipient from notification topic

        Args:
            recipient: Recipient address/ID
            topic: Topic name
            notification_type: Type of notification

        Returns:
            True if unsubscribed successfully
        """
        pass

    @abstractmethod
    async def send_to_topic(
        self,
        topic: str,
        subject: str,
        content: str,
        notification_type: NotificationType
    ) -> List[NotificationResponse]:
        """
        Send notification to all topic subscribers

        Args:
            topic: Topic name
            subject: Notification subject
            content: Notification content
            notification_type: Type of notification

        Returns:
            List of notification responses
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if notification service is healthy

        Returns:
            True if service is healthy
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> List[NotificationType]:
        """
        Get supported notification types

        Returns:
            List of supported notification types
        """
        pass

    @abstractmethod
    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get notification rate limits

        Returns:
            Dict containing rate limit information
        """
        pass