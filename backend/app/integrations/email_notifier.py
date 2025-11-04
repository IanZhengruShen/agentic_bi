"""
Email Notifier for HITL Intervention Notifications.

Sends email notifications as a fallback when Slack is unavailable
or as a primary notification channel based on user preferences.
"""

import logging
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Email notifier for HITL intervention notifications.

    Sends HTML-formatted emails via SMTP when human intervention is required.
    Falls back to plain text if HTML rendering fails.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        """
        Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
        """
        self.smtp_host = smtp_host or getattr(settings, "smtp_host", None)
        self.smtp_port = smtp_port or getattr(settings, "smtp_port", 587)
        self.smtp_user = smtp_user or getattr(settings, "smtp_user", None)
        self.smtp_password = smtp_password or getattr(settings, "smtp_password", None)
        self.from_email = from_email or getattr(settings, "smtp_from_email", "noreply@agenticbi.com")

        self.enabled = bool(self.smtp_host and self.smtp_user and self.smtp_password)

        if self.enabled:
            logger.info(f"Email notifier initialized (SMTP: {self.smtp_host}:{self.smtp_port})")
        else:
            logger.info("Email notifier disabled (SMTP not configured)")

    async def notify_intervention_required(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        recipient_email: str,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """
        Send email notification that human intervention is required.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            recipient_email: Email address to send notification to
            dashboard_url: Optional URL to web dashboard

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifier disabled, skipping notification")
            return False

        if not recipient_email:
            logger.warning("No recipient email provided, skipping notification")
            return False

        try:
            # Build email message
            subject = f"Human Input Required: {intervention_type.replace('_', ' ').title()}"
            html_body = self._build_html_email(
                request_id=request_id,
                workflow_id=workflow_id,
                intervention_type=intervention_type,
                context=context,
                options=options,
                timeout_seconds=timeout_seconds,
                dashboard_url=dashboard_url,
            )
            text_body = self._build_text_email(
                request_id=request_id,
                workflow_id=workflow_id,
                intervention_type=intervention_type,
                context=context,
                options=options,
                timeout_seconds=timeout_seconds,
                dashboard_url=dashboard_url,
            )

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = recipient_email

            # Attach plain text and HTML parts
            part_text = MIMEText(text_body, "plain")
            part_html = MIMEText(html_body, "html")

            msg.attach(part_text)
            msg.attach(part_html)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipient_email, msg.as_string())

            logger.info(
                f"Email notification sent to {recipient_email} for HITL request {request_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _build_html_email(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        dashboard_url: Optional[str] = None,
    ) -> str:
        """
        Build HTML email body.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            dashboard_url: Optional dashboard URL

        Returns:
            HTML email body
        """
        intervention_display = intervention_type.replace("_", " ").title()
        context_summary = self._format_context_summary(context)
        options_html = "".join(
            [
                f"<li><strong>{opt.get('action', 'N/A')}</strong>: {opt.get('label', 'N/A')}</li>"
                for opt in options[:5]
            ]
        )

        dashboard_link = ""
        if dashboard_url:
            dashboard_link = f"""
            <p style="text-align: center; margin-top: 30px;">
                <a href="{dashboard_url}"
                   style="background-color: #007bff; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; font-weight: bold;">
                    Open Dashboard
                </a>
            </p>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 20px; margin-bottom: 20px;">
                <h2 style="margin-top: 0; color: #007bff;">🔔 Human Input Required</h2>
                <p style="font-size: 18px; font-weight: bold; margin-bottom: 0;">{intervention_display}</p>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Request ID:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-family: monospace;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Workflow ID:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-family: monospace;">{workflow_id}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Type:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{intervention_display}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Timeout:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{timeout_seconds} seconds</td>
                </tr>
            </table>

            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">Context:</h3>
                <p style="white-space: pre-wrap;">{context_summary}</p>
            </div>

            <div style="margin-bottom: 20px;">
                <h3>Available Options:</h3>
                <ul style="list-style-type: none; padding-left: 0;">
                    {options_html}
                </ul>
            </div>

            {dashboard_link}

            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">

            <p style="font-size: 12px; color: #6c757d; text-align: center;">
                This is an automated notification from Agentic BI Platform.<br>
                Please respond within {timeout_seconds} seconds to avoid timeout.
            </p>
        </body>
        </html>
        """

        return html

    def _build_text_email(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int,
        dashboard_url: Optional[str] = None,
    ) -> str:
        """
        Build plain text email body (fallback).

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            dashboard_url: Optional dashboard URL

        Returns:
            Plain text email body
        """
        intervention_display = intervention_type.replace("_", " ").title()
        context_summary = self._format_context_summary(context)
        options_text = "\n".join(
            [f"  - {opt.get('action', 'N/A')}: {opt.get('label', 'N/A')}" for opt in options[:5]]
        )

        dashboard_text = f"\n\nOpen Dashboard: {dashboard_url}\n" if dashboard_url else ""

        text = f"""
Human Input Required: {intervention_display}

Request ID: {request_id}
Workflow ID: {workflow_id}
Type: {intervention_display}
Timeout: {timeout_seconds} seconds

Context:
{context_summary}

Available Options:
{options_text}
{dashboard_text}
---
This is an automated notification from Agentic BI Platform.
Please respond within {timeout_seconds} seconds to avoid timeout.
        """

        return text.strip()

    def _format_context_summary(self, context: Dict[str, Any], max_length: int = 1000) -> str:
        """
        Format context dictionary into readable summary.

        Args:
            context: Context dictionary
            max_length: Maximum length of summary

        Returns:
            Formatted context summary
        """
        if not context:
            return "No additional context"

        summary_parts = []

        # SQL query
        if "sql" in context or "query" in context:
            sql = context.get("sql") or context.get("query")
            if sql:
                sql_preview = sql[:500] + "..." if len(sql) > 500 else sql
                summary_parts.append(f"SQL Query:\n{sql_preview}")

        # Database
        if "database" in context:
            summary_parts.append(f"Database: {context['database']}")

        # Table
        if "table" in context:
            summary_parts.append(f"Table: {context['table']}")

        # Description
        if "description" in context:
            desc = context["description"]
            desc_preview = desc[:300] + "..." if len(desc) > 300 else desc
            summary_parts.append(f"Description: {desc_preview}")

        summary = "\n\n".join(summary_parts)

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary or "No additional context"


# Global email notifier instance
_email_notifier = None


def get_email_notifier() -> EmailNotifier:
    """
    Get global email notifier instance.

    Returns:
        EmailNotifier instance
    """
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier
