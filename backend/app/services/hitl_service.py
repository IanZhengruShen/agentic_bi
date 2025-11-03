"""
Human-in-the-Loop (HITL) Service

Lightweight HITL service for PR#4 that provides:
- Synchronous human intervention requests
- WebSocket event broadcasting
- Timeout handling
- Response tracking
- Intervention logging

Note: This is a simplified version for PR#4. Full HITL implementation is in PR#12.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class HumanInputOption(BaseModel):
    """An option for human to choose from."""

    action: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None


class HumanInputRequest(BaseModel):
    """Request for human intervention."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    intervention_type: str
    context: Dict[str, Any]
    options: List[HumanInputOption]
    timeout_seconds: int = 300
    required: bool = True
    requested_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def timeout_at(self) -> datetime:
        """Calculate timeout timestamp."""
        return self.requested_at + timedelta(seconds=self.timeout_seconds)

    def is_expired(self) -> bool:
        """Check if request has expired."""
        return datetime.utcnow() > self.timeout_at


class HumanResponse(BaseModel):
    """Response from human."""

    request_id: str
    action: str
    data: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    modified_sql: Optional[str] = None
    responded_at: datetime = Field(default_factory=datetime.utcnow)


class InterventionOutcome(BaseModel):
    """Outcome of intervention with metadata."""

    request_id: str
    session_id: str
    intervention_type: str
    outcome: str  # approved, rejected, timeout, modified, aborted
    response: Optional[HumanResponse] = None
    response_time_ms: Optional[int] = None
    automated_fallback: bool = False
    timeout_occurred: bool = False


class HITLService:
    """
    Human-in-the-Loop service for agent confirmation requests.

    For PR#4, this provides basic synchronous intervention handling.
    Full async WebSocket-based implementation will be in PR#12.
    """

    def __init__(self):
        """Initialize HITL service."""
        self.enabled = settings.hitl.hitl_enabled
        self.default_timeout = settings.hitl.default_intervention_timeout
        self.timeout_fallback = settings.hitl.timeout_fallback

        # In-memory storage for pending requests
        # In production, this should be Redis or similar
        self._pending_requests: Dict[str, HumanInputRequest] = {}
        self._responses: Dict[str, HumanResponse] = {}

        # WebSocket connections (placeholder for PR#4)
        self._websocket_connections: Dict[str, Any] = {}

        logger.info(
            f"HITL Service initialized (enabled={self.enabled}, "
            f"default_timeout={self.default_timeout}s)"
        )

    async def request_human_input(
        self,
        session_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout: Optional[int] = None,
        required: bool = True,
    ) -> InterventionOutcome:
        """
        Request human input during agent execution.

        Flow:
        1. Create intervention request
        2. Broadcast via WebSocket (if available)
        3. Wait for response with timeout
        4. Return outcome

        Args:
            session_id: Session identifier
            intervention_type: Type of intervention
            context: Context data for decision
            options: List of available options
            timeout: Optional timeout override
            required: Whether intervention is required

        Returns:
            InterventionOutcome with response or fallback
        """
        if not self.enabled:
            logger.info("HITL disabled, auto-approving intervention")
            return InterventionOutcome(
                request_id=str(uuid4()),
                session_id=session_id,
                intervention_type=intervention_type,
                outcome="approved",
                automated_fallback=True,
            )

        timeout_seconds = timeout or self.default_timeout

        # Convert dict options to HumanInputOption models
        option_models = [HumanInputOption(**opt) for opt in options]

        # Create request
        request = HumanInputRequest(
            session_id=session_id,
            intervention_type=intervention_type,
            context=context,
            options=option_models,
            timeout_seconds=timeout_seconds,
            required=required,
        )

        # Store pending request
        self._pending_requests[request.request_id] = request

        logger.info(
            f"Created HITL request {request.request_id} for session {session_id}: "
            f"{intervention_type} (timeout: {timeout_seconds}s)"
        )

        # Broadcast via WebSocket (placeholder for PR#4)
        await self._broadcast_intervention_request(request)

        # Wait for response with timeout
        try:
            response = await self._wait_for_response(
                request.request_id,
                timeout_seconds=timeout_seconds,
            )

            # Calculate response time
            response_time = None
            if response:
                delta = response.responded_at - request.requested_at
                response_time = int(delta.total_seconds() * 1000)

            # Determine outcome
            if response:
                outcome = InterventionOutcome(
                    request_id=request.request_id,
                    session_id=session_id,
                    intervention_type=intervention_type,
                    outcome=response.action,
                    response=response,
                    response_time_ms=response_time,
                    automated_fallback=False,
                    timeout_occurred=False,
                )
            else:
                # Timeout occurred
                outcome = await self._handle_timeout(request)

            # Cleanup
            self._pending_requests.pop(request.request_id, None)
            self._responses.pop(request.request_id, None)

            logger.info(
                f"HITL request {request.request_id} completed: {outcome.outcome} "
                f"(response_time: {response_time}ms)"
            )

            return outcome

        except Exception as e:
            logger.error(f"Error during HITL request {request.request_id}: {e}")

            # Return fallback outcome
            return InterventionOutcome(
                request_id=request.request_id,
                session_id=session_id,
                intervention_type=intervention_type,
                outcome="error",
                automated_fallback=True,
            )

    async def submit_response(
        self,
        request_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
        modified_sql: Optional[str] = None,
    ) -> bool:
        """
        Submit human response to a pending request.

        This would typically be called by the WebSocket handler or API endpoint.

        Args:
            request_id: Request identifier
            action: Action taken (approve, reject, modify, etc.)
            data: Optional additional data
            feedback: Optional feedback text
            modified_sql: Optional modified SQL

        Returns:
            True if response was accepted, False otherwise
        """
        if request_id not in self._pending_requests:
            logger.warning(f"Response submitted for unknown request: {request_id}")
            return False

        request = self._pending_requests[request_id]

        if request.is_expired():
            logger.warning(f"Response submitted for expired request: {request_id}")
            return False

        # Create response
        response = HumanResponse(
            request_id=request_id,
            action=action,
            data=data,
            feedback=feedback,
            modified_sql=modified_sql,
        )

        # Store response
        self._responses[request_id] = response

        logger.info(f"Response submitted for request {request_id}: {action}")

        return True

    async def _wait_for_response(
        self,
        request_id: str,
        timeout_seconds: int,
    ) -> Optional[HumanResponse]:
        """
        Wait for human response with timeout.

        Args:
            request_id: Request identifier
            timeout_seconds: Timeout in seconds

        Returns:
            HumanResponse if received, None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        check_interval = 0.5  # Check every 500ms

        while True:
            # Check if response received
            if request_id in self._responses:
                return self._responses[request_id]

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout_seconds:
                logger.warning(f"HITL request {request_id} timed out after {timeout_seconds}s")
                return None

            # Wait before next check
            await asyncio.sleep(check_interval)

    async def _handle_timeout(self, request: HumanInputRequest) -> InterventionOutcome:
        """
        Handle timeout based on configured fallback behavior.

        Args:
            request: Original request

        Returns:
            InterventionOutcome with fallback decision
        """
        fallback = self.timeout_fallback

        logger.warning(
            f"HITL request {request.request_id} timed out, "
            f"applying fallback: {fallback}"
        )

        if fallback == "auto_approve":
            outcome_str = "approved"
        elif fallback == "continue":
            outcome_str = "approved"
        else:  # abort
            outcome_str = "aborted"

        return InterventionOutcome(
            request_id=request.request_id,
            session_id=request.session_id,
            intervention_type=request.intervention_type,
            outcome=outcome_str,
            automated_fallback=True,
            timeout_occurred=True,
        )

    async def notify_intervention_requested(
        self,
        session_id: str,
        context: Dict[str, Any],
    ):
        """
        Send notification that an intervention has been requested.

        This is a lightweight notification method for use with interrupt() pattern.
        It broadcasts to WebSocket if available, but doesn't block waiting for response.

        Args:
            session_id: Session identifier
            context: Context data to send to client
        """
        if session_id not in self._websocket_connections:
            logger.debug(
                f"No WebSocket connection for session {session_id}, "
                "skipping intervention notification"
            )
            return

        logger.info(f"Notifying intervention for session {session_id} (placeholder)")

        # TODO: Implement WebSocket notification in PR#8
        # websocket = self._websocket_connections[session_id]
        # await websocket.send_json({
        #     "type": "workflow_paused",
        #     "session_id": session_id,
        #     "context": context
        # })

    async def _broadcast_intervention_request(self, request: HumanInputRequest):
        """
        Broadcast intervention request via WebSocket.

        Placeholder for PR#4 - full implementation in PR#8/PR#12.

        Args:
            request: HumanInputRequest to broadcast
        """
        # Check if session has WebSocket connection
        if request.session_id not in self._websocket_connections:
            logger.warning(
                f"No WebSocket connection for session {request.session_id}, "
                "user cannot respond to intervention"
            )
            return

        # In PR#8, this will actually send WebSocket message
        # For now, just log
        logger.info(f"Broadcasting HITL request {request.request_id} (placeholder)")

        # TODO: Implement WebSocket broadcast in PR#8
        # websocket = self._websocket_connections[request.session_id]
        # await websocket.send_json({
        #     "type": "human_input_required",
        #     "data": request.model_dump()
        # })

    def register_websocket(self, session_id: str, websocket: Any):
        """
        Register WebSocket connection for session.

        Placeholder for PR#8.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        self._websocket_connections[session_id] = websocket
        logger.info(f"Registered WebSocket for session {session_id}")

    def unregister_websocket(self, session_id: str):
        """
        Unregister WebSocket connection.

        Args:
            session_id: Session identifier
        """
        if session_id in self._websocket_connections:
            del self._websocket_connections[session_id]
            logger.info(f"Unregistered WebSocket for session {session_id}")

    def get_pending_requests(self, session_id: str) -> List[HumanInputRequest]:
        """
        Get all pending requests for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of pending requests
        """
        return [
            req
            for req in self._pending_requests.values()
            if req.session_id == session_id and not req.is_expired()
        ]

    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.

        Args:
            request_id: Request identifier

        Returns:
            True if cancelled, False if not found
        """
        if request_id in self._pending_requests:
            self._pending_requests.pop(request_id)
            logger.info(f"Cancelled HITL request {request_id}")
            return True
        return False


# Global HITL service instance
hitl_service = HITLService()


def get_hitl_service() -> HITLService:
    """
    Get global HITL service instance.

    Returns:
        HITLService instance
    """
    return hitl_service
