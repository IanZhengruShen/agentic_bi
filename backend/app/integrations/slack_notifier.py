"""
Slack Notifier for HITL Intervention Notifications.

Sends real-time notifications to Slack when human intervention is required.
Supports interactive buttons for quick approve/reject actions.
"""

import logging
from typing import Optional, Dict, Any, List
import json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Slack notifier for HITL intervention notifications.

    Sends formatted messages to Slack channels or users via webhook
    or Slack Web API. Supports interactive buttons for quick responses.
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack incoming webhook URL
            bot_token: Slack bot token for Web API (optional, for advanced features)
        """
        self.webhook_url = webhook_url or getattr(settings, "slack_webhook_url", None)
        self.bot_token = bot_token or getattr(settings, "slack_bot_token", None)
        self.enabled = bool(self.webhook_url or self.bot_token) and HTTPX_AVAILABLE

        if not HTTPX_AVAILABLE:
            logger.warning("httpx not installed, Slack notifications disabled")
            self.enabled = False

        if self.enabled:
            logger.info("Slack notifier initialized")
        else:
            logger.info("Slack notifier disabled (no webhook/token configured)")

    async def notify_intervention_required(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """
        Send notification that human intervention is required.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context (summary)
            options: Available options
            timeout_seconds: Timeout duration
            dashboard_url: Optional URL to web dashboard

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Slack disabled, skipping notification")
            return False

        try:
            # Build Slack message
            message = self._build_intervention_message(
                request_id=request_id,
                workflow_id=workflow_id,
                intervention_type=intervention_type,
                context=context,
                options=options,
                timeout_seconds=timeout_seconds,
                dashboard_url=dashboard_url,
            )

            # Send via webhook
            if self.webhook_url:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json=message,
                        timeout=10.0,
                    )

                    if response.status_code == 200:
                        logger.info(
                            f"Slack notification sent for HITL request {request_id}"
                        )
                        return True
                    else:
                        logger.error(
                            f"Slack webhook failed: {response.status_code} - {response.text}"
                        )
                        return False

            return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _build_intervention_message(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        dashboard_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build Slack message payload with blocks and attachments.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            dashboard_url: Optional dashboard URL

        Returns:
            Slack message payload
        """
        # Format intervention type for display
        intervention_display = intervention_type.replace("_", " ").title()

        # Build context summary (limit to key fields)
        context_summary = self._format_context_summary(context)

        # Build options list
        options_text = "\n".join(
            [f"• *{opt.get('action', 'N/A')}*: {opt.get('label', 'N/A')}" for opt in options[:5]]
        )

        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 Human Input Required: {intervention_display}",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Request ID:*\n`{request_id[:16]}...`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Workflow ID:*\n`{workflow_id[:16]}...`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{intervention_display}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timeout:*\n{timeout_seconds} seconds",
                    },
                ],
            },
        ]

        # Add context summary if available
        if context_summary:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Context:*\n{context_summary}",
                    },
                }
            )

        # Add options
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Available Options:*\n{options_text}",
                },
            }
        )

        # Add dashboard link if available
        if dashboard_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open Dashboard",
                                "emoji": True,
                            },
                            "url": dashboard_url,
                            "style": "primary",
                        }
                    ],
                }
            )

        # Build final message
        message = {
            "text": f"Human input required for {intervention_display}",
            "blocks": blocks,
        }

        return message

    def _format_context_summary(self, context: Dict[str, Any], max_length: int = 500) -> str:
        """
        Format context dictionary into readable summary.

        Args:
            context: Context dictionary
            max_length: Maximum length of summary

        Returns:
            Formatted context summary
        """
        if not context:
            return ""

        # Extract key fields
        summary_parts = []

        # SQL query (common in HITL)
        if "sql" in context or "query" in context:
            sql = context.get("sql") or context.get("query")
            if sql:
                sql_preview = sql[:200] + "..." if len(sql) > 200 else sql
                summary_parts.append(f"```sql\n{sql_preview}\n```")

        # Database
        if "database" in context:
            summary_parts.append(f"Database: `{context['database']}`")

        # Table
        if "table" in context:
            summary_parts.append(f"Table: `{context['table']}`")

        # Description
        if "description" in context:
            desc = context["description"]
            desc_preview = desc[:200] + "..." if len(desc) > 200 else desc
            summary_parts.append(desc_preview)

        # Combine summary
        summary = "\n".join(summary_parts)

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary or "No additional context"


# Global Slack notifier instance
_slack_notifier = None


def get_slack_notifier() -> SlackNotifier:
    """
    Get global Slack notifier instance.

    Returns:
        SlackNotifier instance
    """
    global _slack_notifier
    if _slack_notifier is None:
        _slack_notifier = SlackNotifier()
    return _slack_notifier
