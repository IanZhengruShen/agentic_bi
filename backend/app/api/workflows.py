"""
Unified Workflow API Endpoints.

Provides REST API for executing unified multi-agent workflows.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.workflow_schemas import (
    UnifiedWorkflowRequest,
    UnifiedWorkflowResponse,
    WorkflowStatusResponse,
    create_unified_workflow_response,
)
from app.workflows.orchestrator import create_unified_orchestrator
from app.core.llm import create_llm_client

try:
    from langfuse.langchain import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    CallbackHandler = None

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post(
    "/execute",
    response_model=UnifiedWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute unified workflow",
    description="Execute unified workflow: Query → Analysis → Visualization (auto)",
)
async def execute_unified_workflow(
    request: UnifiedWorkflowRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute unified multi-agent workflow.

    This endpoint orchestrates both AnalysisAgent and VisualizationAgent
    to provide complete query results with automatic visualization.

    **Workflow Flow:**
    1. AnalysisAgent: NL Query → SQL → Data → Analysis
    2. Decision: Should we create visualization?
    3. VisualizationAgent (conditional): Data → Chart Recommendation → Plotly Figure
    4. Return: Complete results with analysis + visualization

    **Request:**
    ```json
    {
        "query": "Show sales trends by region for last quarter",
        "database": "sales_db",
        "conversation_id": null,
        "options": {
            "auto_visualize": true,
            "include_insights": true,
            "chart_type": null,
            "limit_rows": 1000
        }
    }
    ```

    **Multi-turn Conversations:**
    For follow-up questions, provide the `conversation_id` from the previous response:

    ```json
    # First query
    POST /workflows/execute
    {"query": "Show sales by region", "database": "sales_db"}

    # Response includes conversation_id
    {"metadata": {"conversation_id": "conv-123", ...}, ...}

    # Follow-up query (reuse conversation_id)
    POST /workflows/execute
    {"query": "What about Q2?", "database": "sales_db", "conversation_id": "conv-123"}
    ```

    **Response:**
    - If successful: Analysis + Visualization + Combined insights
    - If visualization fails: Analysis only (partial success)
    - If analysis fails: Error response

    **Permissions Required:** `execute` on `workflow`
    """
    logger.info(
        f"[API:workflows] Execute unified workflow: "
        f"user={current_user.id}, query='{request.query[:50]}', "
        f"database={request.database}"
    )

    # Check permissions
    # Note: Using require_permission as a manual check here
    # You can also use it as a dependency: dependencies=[Depends(require_permission(...))]
    try:
        from app.services.opa_client import opa_client
        await opa_client.check_permission_or_raise(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id) if current_user.company_id else None,
            role=current_user.role,
            action="execute",
            resource_type="workflow",
            resource_data={
                "database": request.database,
                "query": request.query,
            }
        )
    except Exception as e:
        logger.warning(f"[API:workflows] Permission check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for workflow execution"
        )

    try:
        # Create Langfuse handler for this execution
        langfuse_handler = None
        if LANGFUSE_AVAILABLE:
            try:
                langfuse_handler = CallbackHandler()
            except Exception as e:
                logger.warning(f"[API:workflows] Langfuse handler creation failed: {e}")

        # Create LLM client
        llm_client = create_llm_client(langfuse_handler=langfuse_handler)

        # Create unified orchestrator
        # Note: Fresh instance per request to avoid shared state
        orchestrator = create_unified_orchestrator(
            llm_client=llm_client,
            langfuse_handler=langfuse_handler,
        )

        # Execute unified workflow
        workflow_result = await orchestrator.execute(
            user_query=request.query,
            database=request.database,
            user_id=str(current_user.id),
            company_id=str(current_user.company_id) if current_user.company_id else "default",
            workflow_id=request.workflow_id,  # Optional: allows client to subscribe before execution
            conversation_id=request.conversation_id,  # Pass through for conversation memory
            options=request.options.model_dump(),
        )

        # Convert to response schema
        response = create_unified_workflow_response(workflow_result)

        logger.info(
            f"[API:workflows] Workflow completed: "
            f"workflow_id={response.metadata.workflow_id}, "
            f"status={response.metadata.workflow_status}, "
            f"time={response.metadata.execution_time_ms}ms"
        )

        return response

    except Exception as e:
        logger.error(f"[API:workflows] Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.get(
    "/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow status",
    description="Get current status of a workflow execution",
)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get workflow execution status.

    **Note:** Status tracking is a future enhancement.
    For now, this endpoint returns a placeholder response.

    **Future Implementation:**
    - Persistent checkpointing (PostgreSQL, Redis)
    - Real-time status updates via WebSocket
    - Progress tracking per agent

    **Permissions Required:** `read` on `workflow`
    """
    logger.info(
        f"[API:workflows] Get status: workflow_id={workflow_id}, user={current_user.id}"
    )

    # TODO: Implement workflow status retrieval from persistent checkpointer
    # For now, return placeholder

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status="unknown",
        stage=None,
        progress={"message": "Status tracking not yet implemented"},
    )


@router.get(
    "/{workflow_id}",
    response_model=UnifiedWorkflowResponse,
    summary="Get workflow results",
    description="Get results of a completed workflow",
)
async def get_workflow_results(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get workflow execution results.

    **Note:** Result persistence is a future enhancement.
    For now, results are only available via the execute endpoint response.

    **Future Implementation:**
    - Store workflow results in database
    - Support result retrieval by workflow_id
    - Support workflow history pagination

    **Permissions Required:** `read` on `workflow`
    """
    logger.info(
        f"[API:workflows] Get results: workflow_id={workflow_id}, user={current_user.id}"
    )

    # TODO: Implement workflow result retrieval from database
    # For now, return error

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Workflow result retrieval not yet implemented. Results are only available via execute endpoint response."
    )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel workflow",
    description="Cancel a running workflow",
)
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Cancel a running workflow.

    **Note:** Workflow cancellation is a future enhancement.

    **Future Implementation:**
    - Track running workflows
    - Support graceful cancellation
    - Clean up resources

    **Permissions Required:** `cancel` on `workflow`
    """
    logger.info(
        f"[API:workflows] Cancel workflow: workflow_id={workflow_id}, user={current_user.id}"
    )

    # TODO: Implement workflow cancellation
    # For now, return error

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Workflow cancellation not yet implemented"
    )


# Future endpoints (placeholders for PR#8+)

# @router.get("/history", response_model=WorkflowListResponse)
# async def get_workflow_history(...):
#     """Get user's workflow execution history"""
#     pass

# @router.post("/{workflow_id}/resume")
# async def resume_workflow(...):
#     """Resume a paused workflow (HITL)"""
#     pass
