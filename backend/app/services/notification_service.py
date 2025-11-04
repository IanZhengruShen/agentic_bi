"""
Unified Notification Service for HITL Interventions.

Coordinates notifications across multiple channels (Slack, Email)
based on user preferences and availability. Handles fallback logic
and notification history.
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum

from app.integrations.slack_notifier import get_slack_notifier
from app.integrations.email_notifier import get_email_notifier

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channel enum."""

    SLACK = "slack"
    EMAIL = "email"
    BOTH = "both"


class NotificationPreferences:
    """
    User notification preferences.

    Defines how and when users want to receive HITL notifications.
    """

    def __init__(
        self,
        channels: List[NotificationChannel] = None,
        slack_enabled: bool = True,
        email_enabled: bool = True,
        intervention_types: List[str] = None,
    ):
        """
        Initialize notification preferences.

        Args:
            channels: Preferred notification channels
            slack_enabled: Whether Slack notifications are enabled
            email_enabled: Whether email notifications are enabled
            intervention_types: List of intervention types to notify about (None = all)
        """
        self.channels = channels or [NotificationChannel.SLACK, NotificationChannel.EMAIL]
        self.slack_enabled = slack_enabled
        self.email_enabled = email_enabled
        self.intervention_types = intervention_types  # None means all types

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationPreferences":
        """
        Create preferences from dictionary (from DB).

        Args:
            data: Preferences dictionary

        Returns:
            NotificationPreferences instance
        """
        if not data:
            return cls()

        return cls(
            channels=[NotificationChannel(ch) for ch in data.get("channels", ["slack", "email"])],
            slack_enabled=data.get("slack_enabled", True),
            email_enabled=data.get("email_enabled", True),
            intervention_types=data.get("intervention_types"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert preferences to dictionary (for DB storage).

        Returns:
            Preferences dictionary
        """
        return {
            "channels": [ch.value for ch in self.channels],
            "slack_enabled": self.slack_enabled,
            "email_enabled": self.email_enabled,
            "intervention_types": self.intervention_types,
        }

    def should_notify(self, intervention_type: str) -> bool:
        """
        Check if user wants notifications for this intervention type.

        Args:
            intervention_type: Type of intervention

        Returns:
            True if should notify, False otherwise
        """
        if self.intervention_types is None:
            return True
        return intervention_type in self.intervention_types


class NotificationService:
    """
    Unified notification service for HITL interventions.

    Coordinates sending notifications via Slack and/or Email based on
    user preferences. Handles fallback logic (Slack → Email) and tracks
    notification status.
    """

    def __init__(self):
        """Initialize notification service with Slack and Email notifiers."""
        self.slack_notifier = get_slack_notifier()
        self.email_notifier = get_email_notifier()

        logger.info(
            f"Notification service initialized "
            f"(Slack: {self.slack_notifier.enabled}, Email: {self.email_notifier.enabled})"
        )

    async def notify_intervention_required(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        user_email: Optional[str] = None,
        user_preferences: Optional[NotificationPreferences] = None,
        dashboard_url: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Send intervention notification via appropriate channels.

        Notification flow:
        1. Check user preferences
        2. Try primary channel (usually Slack)
        3. Fall back to secondary channel (Email) if primary fails
        4. Log notification status

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            user_email: User's email address
            user_preferences: User's notification preferences
            dashboard_url: Optional URL to dashboard

        Returns:
            Dictionary with notification status per channel:
            {"slack": True/False, "email": True/False}
        """
        # Default preferences if not provided
        if user_preferences is None:
            user_preferences = NotificationPreferences()

        # Check if user wants notifications for this intervention type
        if not user_preferences.should_notify(intervention_type):
            logger.info(
                f"User preferences exclude notifications for {intervention_type}, skipping"
            )
            return {"slack": False, "email": False}

        results = {"slack": False, "email": False}

        # Try Slack first if enabled
        if user_preferences.slack_enabled and self.slack_notifier.enabled:
            try:
                slack_success = await self.slack_notifier.notify_intervention_required(
                    request_id=request_id,
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    context=context,
                    options=options,
                    timeout_seconds=timeout_seconds,
                    dashboard_url=dashboard_url,
                )
                results["slack"] = slack_success

                if slack_success:
                    logger.info(f"Slack notification sent for HITL request {request_id}")
                else:
                    logger.warning(f"Slack notification failed for HITL request {request_id}")

            except Exception as e:
                logger.error(f"Slack notification error: {e}")
                results["slack"] = False

        # Try Email if:
        # 1. Email is enabled in preferences AND
        # 2. (Slack failed OR user wants both channels)
        should_send_email = (
            user_preferences.email_enabled
            and self.email_notifier.enabled
            and user_email
            and (
                not results["slack"]  # Slack failed (fallback)
                or NotificationChannel.BOTH in user_preferences.channels  # User wants both
                or NotificationChannel.EMAIL in user_preferences.channels  # User prefers email
            )
        )

        if should_send_email:
            try:
                email_success = await self.email_notifier.notify_intervention_required(
                    request_id=request_id,
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    context=context,
                    options=options,
                    timeout_seconds=timeout_seconds,
                    recipient_email=user_email,
                    dashboard_url=dashboard_url,
                )
                results["email"] = email_success

                if email_success:
                    logger.info(f"Email notification sent for HITL request {request_id}")
                else:
                    logger.warning(f"Email notification failed for HITL request {request_id}")

            except Exception as e:
                logger.error(f"Email notification error: {e}")
                results["email"] = False

        # Log overall notification status
        if any(results.values()):
            logger.info(
                f"Notification sent for HITL request {request_id}: {results}"
            )
        else:
            logger.warning(
                f"All notification channels failed for HITL request {request_id}"
            )

        return results


# Global notification service instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """
    Get global notification service instance.

    Returns:
        NotificationService instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
