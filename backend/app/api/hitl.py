"""
Human-in-the-Loop (HITL) API Endpoints.

Provides REST API for responding to human intervention requests.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_user
from app.models.user import User
from app.services.hitl_service import get_hitl_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/hitl", tags=["hitl"])


class HITLResponseRequest(BaseModel):
    """Request to submit HITL response."""

    request_id: str = Field(..., description="HITL request ID")
    action: str = Field(..., description="Action taken (approve, reject, modify, etc.)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")
    feedback: Optional[str] = Field(None, description="Feedback text")
    modified_sql: Optional[str] = Field(None, description="Modified SQL (if applicable)")


class HITLResponseResponse(BaseModel):
    """Response after submitting HITL response."""

    success: bool
    message: str
    request_id: str


@router.post(
    "/respond",
    response_model=HITLResponseResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit human response",
    description="Submit response to a pending human intervention request",
)
async def submit_hitl_response(
    request: HITLResponseRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit human response to a pending HITL request.

    **Flow**:
    1. User receives `human_input.required` event via WebSocket
    2. User reviews the request context and options
    3. User submits response via this endpoint
    4. Workflow resumes with user's decision

    **Example Request**:
    ```json
    {
        "request_id": "hitl-req-12345",
        "action": "approve",
        "feedback": "Looks good!"
    }
    ```

    **Actions**:
    - `approve`: Approve and continue
    - `reject`: Reject and abort
    - `modify`: Modify and continue (requires modified_sql)
    - `abort`: Abort workflow

    **Permissions Required**: None (user can respond to their own requests)
    """
    logger.info(
        f"[API:hitl] User {current_user.id} responding to request {request.request_id}: "
        f"action={request.action}"
    )

    hitl_service = get_hitl_service()

    # Submit response
    success = await hitl_service.submit_response(
        request_id=request.request_id,
        action=request.action,
        data=request.data,
        feedback=request.feedback,
        modified_sql=request.modified_sql,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HITL request {request.request_id} not found or expired",
        )

    # Broadcast event that input was received
    from app.websocket.connection_manager import connection_manager
    from app.websocket.events import create_workflow_event, WorkflowEventType

    # Get the pending request to find workflow_id
    pending_requests = hitl_service._pending_requests
    if request.request_id in pending_requests:
        workflow_id = pending_requests[request.request_id].session_id

        event = create_workflow_event(
            WorkflowEventType.HUMAN_INPUT_RECEIVED,
            workflow_id=workflow_id,
            message=f"Human response received: {request.action}",
            data={
                "request_id": request.request_id,
                "action": request.action,
            },
        )

        await connection_manager.broadcast_to_workflow(workflow_id, event)

    logger.info(f"[API:hitl] Response submitted successfully: {request.request_id}")

    return HITLResponseResponse(
        success=True,
        message=f"Response submitted: {request.action}",
        request_id=request.request_id,
    )


@router.get(
    "/pending/{workflow_id}",
    summary="Get pending requests",
    description="Get all pending HITL requests for a workflow",
)
async def get_pending_requests(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all pending HITL requests for a workflow.

    Useful for:
    - Reconnecting after disconnect
    - Checking if any interventions are waiting
    - Displaying pending requests in UI

    **Returns**:
    List of pending HITL requests with context and options.
    """
    logger.info(
        f"[API:hitl] User {current_user.id} requesting pending requests for workflow {workflow_id}"
    )

    hitl_service = get_hitl_service()
    pending = hitl_service.get_pending_requests(workflow_id)

    return {
        "workflow_id": workflow_id,
        "count": len(pending),
        "requests": [req.model_dump() for req in pending],
    }
