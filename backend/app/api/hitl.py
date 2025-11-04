"""
Human-in-the-Loop (HITL) API Endpoints.

Provides REST API for responding to human intervention requests.
Enhanced in PR#12 with database persistence.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db  # Use async get_db, not sync one from models
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
    workflow_id: str  # The workflow ID that was resumed


@router.post(
    "/respond",
    response_model=HITLResponseResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Submit human response",
    description="Submit response to a pending human intervention request",
)
async def submit_hitl_response(
    request: HITLResponseRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
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

    hitl_service = get_hitl_service(db_session=db)

    # Submit response
    success = await hitl_service.submit_response(
        request_id=request.request_id,
        action=request.action,
        data=request.data,
        feedback=request.feedback,
        modified_sql=request.modified_sql,
        responder_user_id=str(current_user.id),
        responder_name=current_user.full_name,
        responder_email=current_user.email,
    )

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"HITL request {request.request_id} not found or expired",
        )

    # Broadcast event that input was received
    from app.websocket.connection_manager import connection_manager
    from app.websocket.events import create_workflow_event, WorkflowEventType
    from app.repositories.hitl_repository import HITLRepository

    # Get the pending request from database to find workflow_id and conversation_id
    repository = HITLRepository(db)
    db_request = await repository.get_request(request.request_id, include_response=False)

    if not db_request:
        logger.warning(f"[API:hitl] Request {request.request_id} not found in database")
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"HITL request {request.request_id} not found",
        )

    workflow_id = db_request.workflow_id
    conversation_id = db_request.conversation_id or workflow_id  # Fallback to workflow_id if no conversation_id

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

    # Resume the workflow if it's paused
    # CRITICAL: Use conversation_id as thread_id for checkpointer (not workflow_id!)
    # The orchestrator uses conversation_id as the thread_id for checkpointing
    resume_result = None
    try:
        from app.workflows.orchestrator import resume_workflow

        logger.info(
            f"[API:hitl] Resuming workflow {workflow_id} (conversation_id={conversation_id}) "
            f"with action: {request.action}"
        )

        # Resume with user's response
        # CRITICAL: Use conversation_id as thread_id (matches orchestrator config)
        # Pass workflow_id explicitly for correct WebSocket broadcasting
        resume_result = await resume_workflow(
            thread_id=conversation_id,  # Use conversation_id for checkpointing
            resume_value={
                "action": request.action,
                "feedback": request.feedback,
                "modified_sql": request.modified_sql,
                "data": request.data,
            },
            workflow_id=workflow_id,  # Original workflow_id for WebSocket events
        )

        logger.info(f"[API:hitl] Workflow {workflow_id} resumed successfully")
    except Exception as resume_error:
        logger.error(f"[API:hitl] Failed to resume workflow: {resume_error}", exc_info=True)
        # Don't fail the response - user's input is already saved
        # But we should still tell the frontend there was an error
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(resume_error)}",
        )

    return HITLResponseResponse(
        success=True,
        message=f"Response submitted: {request.action}",
        request_id=request.request_id,
        workflow_id=workflow_id,  # Return the original workflow_id to frontend
    )


@router.get(
    "/pending/{workflow_id}",
    summary="Get pending requests",
    description="Get all pending HITL requests for a workflow",
)
async def get_pending_requests(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
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

    hitl_service = get_hitl_service(db_session=db)
    pending = await hitl_service.get_pending_requests(workflow_id)

    return {
        "workflow_id": workflow_id,
        "count": len(pending),
        "requests": [req.model_dump() for req in pending],
    }


@router.get(
    "/history",
    summary="Get intervention history",
    description="Get HITL intervention history for the current user",
)
async def get_hitl_history(
    intervention_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get HITL intervention history with optional filters.

    **Query Parameters:**
    - intervention_type: Filter by type (sql_review, data_modification, etc.)
    - status: Filter by status (approved, rejected, etc.)
    - date_from: ISO date string for start date
    - date_to: ISO date string for end date
    - search: Search in context fields

    **Returns:**
    List of historical HITL requests with responses.
    """
    logger.info(
        f"[API:hitl] User {current_user.id} requesting history with filters: "
        f"type={intervention_type}, status={status}"
    )

    from app.repositories.hitl_repository import HITLRepository
    from app.models.hitl_models import HITLRequest, HITLResponse
    from sqlalchemy import select, and_, or_
    from sqlalchemy.orm import selectinload
    from datetime import datetime

    try:
        # Build query
        # Note: Ensure user ID is proper UUID type for comparison
        from uuid import UUID as PyUUID
        user_id = current_user.id if isinstance(current_user.id, PyUUID) else PyUUID(str(current_user.id))

        stmt = (
            select(HITLRequest)
            .options(selectinload(HITLRequest.response))  # Eagerly load response relationship
            .where(HITLRequest.requester_user_id == user_id)
            .order_by(HITLRequest.requested_at.desc())
        )

        # Apply filters
        filters = []
        if intervention_type:
            filters.append(HITLRequest.intervention_type == intervention_type)
        if status:
            filters.append(HITLRequest.status == status)
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            filters.append(HITLRequest.requested_at >= date_from_dt)
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            filters.append(HITLRequest.requested_at <= date_to_dt)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Execute query
        result = await db.execute(stmt)
        requests = result.scalars().all()

        # Format response
        history = []
        for req in requests:
            item = {
                "id": str(req.id),
                "request_id": req.request_id,
                "workflow_id": req.workflow_id,
                "conversation_id": req.conversation_id,
                "intervention_type": req.intervention_type,
                "status": req.status,
                "requested_at": req.requested_at.isoformat(),
                "responded_at": req.responded_at.isoformat() if req.responded_at else None,
                "response_time_ms": req.response_time_ms,
                "context": req.context,
            }

            # Add response details if available
            if req.response:
                item["action"] = req.response.action
                item["responder_name"] = req.response.responder_name
                item["responder_email"] = req.response.responder_email
                item["feedback"] = req.response.feedback

            history.append(item)

        logger.info(f"[API:hitl] Returning {len(history)} history items")
        return history

    except Exception as e:
        logger.error(f"[API:hitl] Failed to fetch history: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}",
        )
