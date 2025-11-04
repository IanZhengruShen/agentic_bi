"""
Human-in-the-Loop (HITL) Service

Enhanced HITL service with persistent storage (PR#12) that provides:
- Persistent database storage for requests/responses
- Synchronous human intervention requests
- WebSocket event broadcasting
- Timeout handling
- Response tracking
- Intervention logging
- Audit trail and history

Updated in PR#12 to use PostgreSQL for persistence.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.hitl_repository import HITLRepository
from app.observability.hitl_tracing import (
    trace_hitl_request,
    trace_hitl_response,
    trace_hitl_timeout,
)

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

    Enhanced in PR#12 with persistent database storage, replacing in-memory
    storage with PostgreSQL for reliability, audit trails, and analytics.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize HITL service.

        Args:
            db_session: Optional database session for persistence.
                       If None, falls back to in-memory storage (for backward compatibility).
        """
        self.enabled = settings.hitl.hitl_enabled
        self.default_timeout = settings.hitl.default_intervention_timeout
        self.timeout_fallback = settings.hitl.timeout_fallback

        # Database session and repository
        self.db_session = db_session
        self.repository = HITLRepository(db_session) if db_session else None

        # In-memory fallback storage (for backward compatibility)
        # Used when db_session is None or for temporary caching
        self._pending_requests: Dict[str, HumanInputRequest] = {}
        self._responses: Dict[str, HumanResponse] = {}

        # WebSocket connections (for real-time notifications)
        self._websocket_connections: Dict[str, Any] = {}

        storage_mode = "database" if self.repository else "in-memory"
        logger.info(
            f"HITL Service initialized (enabled={self.enabled}, "
            f"default_timeout={self.default_timeout}s, storage={storage_mode})"
        )

    async def request_human_input(
        self,
        session_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout: Optional[int] = None,
        required: bool = True,
        conversation_id: Optional[str] = None,
        requester_user_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> InterventionOutcome:
        """
        Request human input during agent execution.

        Flow:
        1. Create intervention request (stored in DB if available)
        2. Broadcast via WebSocket (if available)
        3. Wait for response with timeout
        4. Update status in DB
        5. Return outcome

        Args:
            session_id: Session identifier (workflow_id)
            intervention_type: Type of intervention
            context: Context data for decision
            options: List of available options
            timeout: Optional timeout override
            required: Whether intervention is required
            conversation_id: Optional conversation ID
            requester_user_id: Optional user ID who requested intervention
            company_id: Optional company ID for multi-tenancy

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

        # Create request (persist to DB if available)
        if self.repository:
            # Store in database
            db_request = await self.repository.create_request(
                workflow_id=session_id,
                intervention_type=intervention_type,
                context=context,
                options=[opt.model_dump() for opt in option_models],
                timeout_seconds=timeout_seconds,
                conversation_id=conversation_id,
                requester_user_id=requester_user_id,
                company_id=company_id,
                required=required,
            )
            await self.db_session.commit()

            request_id = db_request.request_id
            requested_at = db_request.requested_at
            timeout_at = db_request.timeout_at

            # Create Pydantic model for in-memory tracking
            request = HumanInputRequest(
                request_id=request_id,
                session_id=session_id,
                intervention_type=intervention_type,
                context=context,
                options=option_models,
                timeout_seconds=timeout_seconds,
                required=required,
                requested_at=requested_at,
            )
        else:
            # Fallback to in-memory storage
            request = HumanInputRequest(
                session_id=session_id,
                intervention_type=intervention_type,
                context=context,
                options=option_models,
                timeout_seconds=timeout_seconds,
                required=required,
            )
            request_id = request.request_id
            requested_at = request.requested_at
            timeout_at = request.timeout_at

        # Store in memory for fast lookup during wait
        self._pending_requests[request_id] = request

        logger.info(
            f"Created HITL request {request_id} for session {session_id}: "
            f"{intervention_type} (timeout: {timeout_seconds}s)"
        )

        # Trace request creation in Langfuse
        trace_hitl_request(
            request_id=request_id,
            workflow_id=session_id,
            intervention_type=intervention_type,
            context=context,
            options=[opt.model_dump() for opt in option_models],
            timeout_seconds=timeout_seconds,
            required=required,
        )

        # Broadcast via WebSocket
        await self._broadcast_intervention_request(request)

        # Wait for response with timeout
        try:
            response = await self._wait_for_response(
                request_id,
                timeout_seconds=timeout_seconds,
            )

            # Calculate response time
            response_time = None
            if response:
                delta = response.responded_at - requested_at
                response_time = int(delta.total_seconds() * 1000)

            # Determine outcome
            if response:
                outcome = InterventionOutcome(
                    request_id=request_id,
                    session_id=session_id,
                    intervention_type=intervention_type,
                    outcome=response.action,
                    response=response,
                    response_time_ms=response_time,
                    automated_fallback=False,
                    timeout_occurred=False,
                )

                # Trace response in Langfuse
                trace_hitl_response(
                    request_id=request_id,
                    workflow_id=session_id,
                    intervention_type=intervention_type,
                    action=response.action,
                    response_time_ms=response_time,
                    feedback=response.feedback,
                )

                # Update status in DB
                if self.repository:
                    await self.repository.update_request_status(
                        request_id=request_id,
                        status=response.action,
                        responded_at=response.responded_at,
                        response_time_ms=response_time,
                    )
                    await self.db_session.commit()
            else:
                # Timeout occurred
                outcome = await self._handle_timeout(request)

                # Trace timeout in Langfuse
                trace_hitl_timeout(
                    request_id=request_id,
                    workflow_id=session_id,
                    intervention_type=intervention_type,
                    timeout_seconds=timeout_seconds,
                    fallback_action=outcome.outcome,
                )

                # Update status in DB
                if self.repository:
                    await self.repository.update_request_status(
                        request_id=request_id,
                        status="timeout",
                        responded_at=datetime.utcnow(),
                    )
                    await self.db_session.commit()

            # Cleanup in-memory cache
            self._pending_requests.pop(request_id, None)
            self._responses.pop(request_id, None)

            logger.info(
                f"HITL request {request_id} completed: {outcome.outcome} "
                f"(response_time: {response_time}ms)"
            )

            return outcome

        except Exception as e:
            logger.error(f"Error during HITL request {request_id}: {e}")

            # Update status in DB
            if self.repository:
                try:
                    await self.repository.update_request_status(
                        request_id=request_id,
                        status="error",
                        responded_at=datetime.utcnow(),
                    )
                    await self.db_session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update error status in DB: {db_error}")

            # Return fallback outcome
            return InterventionOutcome(
                request_id=request_id,
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
        responder_user_id: Optional[str] = None,
        responder_name: Optional[str] = None,
        responder_email: Optional[str] = None,
    ) -> bool:
        """
        Submit human response to a pending request.

        This is typically called by the WebSocket handler or API endpoint.
        Response is persisted to database if available.

        Args:
            request_id: Request identifier
            action: Action taken (approve, reject, modify, etc.)
            data: Optional additional data
            feedback: Optional feedback text
            modified_sql: Optional modified SQL
            responder_user_id: Optional user ID of responder
            responder_name: Optional name of responder
            responder_email: Optional email of responder

        Returns:
            True if response was accepted, False otherwise
        """
        # Check if request exists (in memory or DB)
        request = None
        if request_id in self._pending_requests:
            request = self._pending_requests[request_id]
        elif self.repository:
            db_request = await self.repository.get_request(request_id)
            if db_request:
                # Convert DB model to Pydantic model
                request = HumanInputRequest(
                    request_id=db_request.request_id,
                    session_id=db_request.workflow_id,
                    intervention_type=db_request.intervention_type,
                    context=db_request.context,
                    options=[HumanInputOption(**opt) for opt in db_request.options],
                    timeout_seconds=db_request.timeout_seconds,
                    required=db_request.required,
                    requested_at=db_request.requested_at,
                )

        if not request:
            logger.warning(f"Response submitted for unknown request: {request_id}")
            return False

        if request.is_expired():
            logger.warning(f"Response submitted for expired request: {request_id}")
            return False

        # Create response (Pydantic model)
        response = HumanResponse(
            request_id=request_id,
            action=action,
            data=data,
            feedback=feedback,
            modified_sql=modified_sql,
        )

        # Store response in memory for immediate lookup
        self._responses[request_id] = response

        # Persist to database if available
        if self.repository:
            try:
                await self.repository.create_response(
                    request_id=request_id,
                    action=action,
                    data=data,
                    feedback=feedback,
                    modified_sql=modified_sql,
                    responder_user_id=responder_user_id,
                    responder_name=responder_name,
                    responder_email=responder_email,
                )
                await self.db_session.commit()
            except Exception as e:
                logger.error(f"Failed to persist response to database: {e}")
                # Continue anyway - response is in memory

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

        Args:
            request: HumanInputRequest to broadcast
        """
        from app.websocket.connection_manager import connection_manager
        from app.websocket.events import create_workflow_event, WorkflowEventType

        logger.info(
            f"Broadcasting HITL request {request.request_id} for workflow {request.session_id}"
        )

        # Use session_id as workflow_id for broadcast
        # (In the workflow, session_id = workflow_id)
        event = create_workflow_event(
            WorkflowEventType.HUMAN_INPUT_REQUIRED,
            workflow_id=request.session_id,
            message=f"Human input required: {request.intervention_type}",
            data={
                "request_id": request.request_id,
                "intervention_type": request.intervention_type,
                "context": request.context,
                "options": [opt.model_dump() for opt in request.options],
                "timeout_seconds": request.timeout_seconds,
                "timeout_at": request.timeout_at.isoformat(),
            },
        )

        await connection_manager.broadcast_to_workflow(request.session_id, event)

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

    async def get_pending_requests(self, session_id: str) -> List[HumanInputRequest]:
        """
        Get all pending requests for a session.

        Checks database first if available, falls back to in-memory storage.

        Args:
            session_id: Session identifier (workflow_id)

        Returns:
            List of pending HumanInputRequest instances
        """
        if self.repository:
            # Get from database
            db_requests = await self.repository.get_pending_requests(
                workflow_id=session_id,
                include_expired=False,
            )

            # Convert to Pydantic models
            return [
                HumanInputRequest(
                    request_id=req.request_id,
                    session_id=req.workflow_id,
                    intervention_type=req.intervention_type,
                    context=req.context,
                    options=[HumanInputOption(**opt) for opt in req.options],
                    timeout_seconds=req.timeout_seconds,
                    required=req.required,
                    requested_at=req.requested_at,
                )
                for req in db_requests
            ]
        else:
            # Fallback to in-memory storage
            return [
                req
                for req in self._pending_requests.values()
                if req.session_id == session_id and not req.is_expired()
            ]

    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.

        Updates status in database if available, otherwise removes from memory.

        Args:
            request_id: Request identifier

        Returns:
            True if cancelled, False if not found
        """
        # Cancel in database if available
        if self.repository:
            success = await self.repository.cancel_request(request_id)
            if success:
                await self.db_session.commit()
                # Also remove from memory cache
                self._pending_requests.pop(request_id, None)
                logger.info(f"Cancelled HITL request {request_id}")
                return True
            return False
        else:
            # Fallback to in-memory storage
            if request_id in self._pending_requests:
                self._pending_requests.pop(request_id)
                logger.info(f"Cancelled HITL request {request_id}")
                return True
            return False


# Global HITL service instance (without DB - for backward compatibility)
_global_hitl_service = HITLService()


def get_hitl_service(db_session: Optional[AsyncSession] = None) -> HITLService:
    """
    Get HITL service instance.

    If db_session is provided, returns a new instance with database persistence.
    Otherwise, returns the global instance with in-memory storage.

    Args:
        db_session: Optional database session for persistence

    Returns:
        HITLService instance
    """
    if db_session:
        return HITLService(db_session=db_session)
    return _global_hitl_service
