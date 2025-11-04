"""
Langfuse Tracing for HITL (Human-in-the-Loop) Operations.

This module provides tracing utilities for all HITL interventions,
enabling observability, analytics, and insights via Langfuse.

Key Metrics Tracked:
- Intervention type and context
- Response time (ms)
- Outcome (approved, rejected, timeout, etc.)
- User who responded
- Intervention frequency by type
- Approval/rejection rates
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from app.core.config import settings

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

logger = logging.getLogger(__name__)


class HITLTracer:
    """
    Tracer for HITL operations using Langfuse.

    Provides context managers and decorators for tracing HITL requests,
    responses, and outcomes. All traces are linked to the parent workflow trace.
    """

    def __init__(self):
        """Initialize HITL tracer with Langfuse client."""
        self.enabled = LANGFUSE_AVAILABLE and settings.langfuse.langfuse_enabled

        if self.enabled:
            try:
                self.langfuse = Langfuse(
                    public_key=settings.langfuse.langfuse_public_key,
                    secret_key=settings.langfuse.langfuse_secret_key,
                    host=settings.langfuse.langfuse_host,
                )
                logger.info("HITL Langfuse tracer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse client: {e}")
                self.enabled = False
                self.langfuse = None
        else:
            self.langfuse = None
            logger.info("HITL Langfuse tracing disabled")

    @asynccontextmanager
    async def trace_intervention(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        trace_id: Optional[str] = None,
    ):
        """
        Context manager for tracing a complete HITL intervention.

        Usage:
        ```python
        async with hitl_tracer.trace_intervention(
            request_id="req-123",
            workflow_id="wf-456",
            intervention_type="sql_approval",
            context={"sql": "SELECT ..."},
        ) as span:
            # Wait for human response
            response = await wait_for_response()
            span.end(output=response)
        ```

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context (anonymized if sensitive)
            trace_id: Optional parent trace ID to link to

        Yields:
            Langfuse span object for updating metadata
        """
        if not self.enabled:
            # No-op context manager when tracing is disabled
            class DummySpan:
                def end(self, **kwargs):
                    pass
                def update(self, **kwargs):
                    pass

            yield DummySpan()
            return

        # Create or get trace
        trace = None
        if trace_id:
            # Link to existing trace
            trace = self.langfuse.trace(id=trace_id)
        else:
            # Create new trace for standalone HITL operation
            trace = self.langfuse.trace(
                name=f"hitl_{intervention_type}",
                user_id=workflow_id,
                metadata={
                    "workflow_id": workflow_id,
                    "request_id": request_id,
                },
            )

        # Create span for intervention
        span = trace.span(
            name=f"hitl_intervention_{intervention_type}",
            input={
                "request_id": request_id,
                "workflow_id": workflow_id,
                "intervention_type": intervention_type,
                "context": self._anonymize_context(context),
            },
            metadata={
                "intervention_type": intervention_type,
                "request_id": request_id,
                "workflow_id": workflow_id,
            },
        )

        try:
            yield span
        finally:
            # Ensure span is ended
            if span:
                span.end()

    def trace_request(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: list,
        timeout_seconds: int,
        required: bool,
        trace_id: Optional[str] = None,
    ):
        """
        Trace HITL request creation.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            context: Intervention context
            options: Available options
            timeout_seconds: Timeout duration
            required: Whether intervention is required
            trace_id: Optional parent trace ID
        """
        if not self.enabled:
            return

        try:
            # Create or get trace
            if trace_id:
                trace = self.langfuse.trace(id=trace_id)
            else:
                trace = self.langfuse.trace(
                    name=f"hitl_request_{intervention_type}",
                    user_id=workflow_id,
                )

            # Create event for request
            trace.event(
                name="hitl_request_created",
                input={
                    "request_id": request_id,
                    "intervention_type": intervention_type,
                    "context": self._anonymize_context(context),
                    "options_count": len(options),
                    "timeout_seconds": timeout_seconds,
                    "required": required,
                },
                metadata={
                    "intervention_type": intervention_type,
                    "request_id": request_id,
                    "workflow_id": workflow_id,
                },
            )

            logger.debug(f"Traced HITL request creation: {request_id}")
        except Exception as e:
            logger.error(f"Failed to trace HITL request: {e}")

    def trace_response(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        action: str,
        response_time_ms: int,
        responder_user_id: Optional[str] = None,
        feedback: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Trace HITL response submission.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            action: Action taken (approve, reject, etc.)
            response_time_ms: Response time in milliseconds
            responder_user_id: User ID who responded
            feedback: Optional feedback text
            trace_id: Optional parent trace ID
        """
        if not self.enabled:
            return

        try:
            # Create or get trace
            if trace_id:
                trace = self.langfuse.trace(id=trace_id)
            else:
                trace = self.langfuse.trace(
                    name=f"hitl_response_{intervention_type}",
                    user_id=workflow_id,
                )

            # Determine response time category
            if response_time_ms < 5000:
                response_category = "fast"
            elif response_time_ms < 30000:
                response_category = "medium"
            else:
                response_category = "slow"

            # Create event for response
            trace.event(
                name="hitl_response_submitted",
                output={
                    "request_id": request_id,
                    "action": action,
                    "response_time_ms": response_time_ms,
                    "responder_user_id": responder_user_id,
                    "feedback": feedback[:200] if feedback else None,  # Truncate long feedback
                },
                metadata={
                    "intervention_type": intervention_type,
                    "intervention_outcome": action,
                    "response_time_category": response_category,
                    "request_id": request_id,
                    "workflow_id": workflow_id,
                },
            )

            logger.debug(f"Traced HITL response: {request_id} → {action}")
        except Exception as e:
            logger.error(f"Failed to trace HITL response: {e}")

    def trace_timeout(
        self,
        request_id: str,
        workflow_id: str,
        intervention_type: str,
        timeout_seconds: int,
        fallback_action: str,
        trace_id: Optional[str] = None,
    ):
        """
        Trace HITL timeout event.

        Args:
            request_id: HITL request identifier
            workflow_id: Parent workflow identifier
            intervention_type: Type of intervention
            timeout_seconds: Timeout duration
            fallback_action: Fallback action taken
            trace_id: Optional parent trace ID
        """
        if not self.enabled:
            return

        try:
            # Create or get trace
            if trace_id:
                trace = self.langfuse.trace(id=trace_id)
            else:
                trace = self.langfuse.trace(
                    name=f"hitl_timeout_{intervention_type}",
                    user_id=workflow_id,
                )

            # Create event for timeout
            trace.event(
                name="hitl_timeout",
                output={
                    "request_id": request_id,
                    "timeout_seconds": timeout_seconds,
                    "fallback_action": fallback_action,
                },
                metadata={
                    "intervention_type": intervention_type,
                    "intervention_outcome": "timeout",
                    "timeout_occurred": "true",
                    "request_id": request_id,
                    "workflow_id": workflow_id,
                },
            )

            logger.debug(f"Traced HITL timeout: {request_id}")
        except Exception as e:
            logger.error(f"Failed to trace HITL timeout: {e}")

    def _anonymize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize sensitive data in context before tracing.

        Removes or masks:
        - Passwords
        - API keys
        - Personal information
        - Large data payloads (>1000 chars)

        Args:
            context: Original context dictionary

        Returns:
            Anonymized context dictionary
        """
        if not context:
            return {}

        anonymized = {}
        sensitive_keys = ["password", "api_key", "secret", "token", "auth"]

        for key, value in context.items():
            # Mask sensitive keys
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                anonymized[key] = "***REDACTED***"
            # Truncate large strings
            elif isinstance(value, str) and len(value) > 1000:
                anonymized[key] = value[:1000] + "... (truncated)"
            # Keep other values as-is
            else:
                anonymized[key] = value

        return anonymized


# Global HITL tracer instance
hitl_tracer = HITLTracer()


# Convenience functions for direct use
def trace_hitl_request(
    request_id: str,
    workflow_id: str,
    intervention_type: str,
    context: Dict[str, Any],
    options: list,
    timeout_seconds: int,
    required: bool = True,
    trace_id: Optional[str] = None,
):
    """
    Trace HITL request creation.

    Convenience function that uses the global hitl_tracer instance.
    """
    hitl_tracer.trace_request(
        request_id=request_id,
        workflow_id=workflow_id,
        intervention_type=intervention_type,
        context=context,
        options=options,
        timeout_seconds=timeout_seconds,
        required=required,
        trace_id=trace_id,
    )


def trace_hitl_response(
    request_id: str,
    workflow_id: str,
    intervention_type: str,
    action: str,
    response_time_ms: int,
    responder_user_id: Optional[str] = None,
    feedback: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    """
    Trace HITL response submission.

    Convenience function that uses the global hitl_tracer instance.
    """
    hitl_tracer.trace_response(
        request_id=request_id,
        workflow_id=workflow_id,
        intervention_type=intervention_type,
        action=action,
        response_time_ms=response_time_ms,
        responder_user_id=responder_user_id,
        feedback=feedback,
        trace_id=trace_id,
    )


def trace_hitl_timeout(
    request_id: str,
    workflow_id: str,
    intervention_type: str,
    timeout_seconds: int,
    fallback_action: str,
    trace_id: Optional[str] = None,
):
    """
    Trace HITL timeout event.

    Convenience function that uses the global hitl_tracer instance.
    """
    hitl_tracer.trace_timeout(
        request_id=request_id,
        workflow_id=workflow_id,
        intervention_type=intervention_type,
        timeout_seconds=timeout_seconds,
        fallback_action=fallback_action,
        trace_id=trace_id,
    )
