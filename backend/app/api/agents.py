"""
FastAPI endpoints for Agent operations.

Endpoints:
- POST /api/agents/query - Execute natural language query
- POST /api/agents/query/stream - Execute query with streaming
- POST /api/agents/sessions/{session_id}/resume - Resume paused workflow
- GET /api/agents/status/{session_id} - Get workflow status
- GET /api/agents/results/{session_id} - Get query results
- GET /api/agents/sessions - List user sessions
- GET /api/agents/interventions/{session_id} - Get pending interventions
- POST /api/agents/interventions/{request_id}/respond - Submit HITL response
- DELETE /api/agents/sessions/{session_id} - Cancel/delete session
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents import create_analysis_agent, AnalysisAgentLangGraph
from app.services.hitl_service import get_hitl_service, HITLService
from app.models import get_db
from app.core.config import settings
from app.schemas import (
    QueryExecutionRequest,
    QueryExecutionResponse,
    WorkflowStatusResponse,
    QueryResultsResponse,
    SessionListResponse,
    PendingInterventionsResponse,
    HITLResponseSubmission,
    ErrorResponse,
)

# Dependency for HITL service
def get_hitl_service_dependency() -> HITLService:
    """
    Dependency function to get HITL service instance.

    Returns in-memory HITL service (without database persistence).
    For database persistence, endpoints should use get_db() separately.
    """
    return get_hitl_service()

# Import Langfuse if available
try:
    from langfuse.langchain import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    CallbackHandler = None

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])

# Global agent instance (in production, consider dependency injection or caching)
_agent_instance: Optional[AnalysisAgentLangGraph] = None
_langfuse_handler: Optional[CallbackHandler] = None


def get_langfuse_handler() -> Optional[CallbackHandler]:
    """
    Get or create Langfuse callback handler for LangChain/LangGraph.

    Uses the modern langfuse.langchain.CallbackHandler which is compatible
    with LangGraph's callback system.

    Returns:
        Langfuse callback handler or None if unavailable
    """
    global _langfuse_handler

    if not LANGFUSE_AVAILABLE:
        logger.warning("Langfuse library not available")
        return None

    if not settings.langfuse.langfuse_enabled:
        logger.info("Langfuse tracing is disabled in settings")
        return None

    if _langfuse_handler is None:
        try:
            # Modern Langfuse integration with LangChain/LangGraph
            # Uses environment variables: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
            # These are already set in docker-compose.yml
            _langfuse_handler = CallbackHandler()
            logger.info(f"Langfuse handler initialized (using env vars)")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse handler: {e}")
            return None

    return _langfuse_handler


def get_agent() -> AnalysisAgentLangGraph:
    """
    Get or create agent instance.

    In production, this could be a dependency that manages
    agent lifecycle, connection pools, etc.
    """
    global _agent_instance
    if _agent_instance is None:
        langfuse_handler = get_langfuse_handler()
        _agent_instance = create_analysis_agent(
            langfuse_handler=langfuse_handler,
            enable_checkpointing=True
        )
    return _agent_instance


# ============================================
# Endpoint: Execute Query
# ============================================


@router.post("/query", response_model=QueryExecutionResponse)
async def execute_query(
    request: QueryExecutionRequest,
    background_tasks: BackgroundTasks,
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Execute a natural language query through the analysis workflow.

    This endpoint:
    1. Initiates the workflow
    2. Returns immediately with session ID
    3. Continues execution in background
    4. Client can poll /status/{session_id} or use WebSocket for updates

    Args:
        request: Query execution request
        background_tasks: FastAPI background tasks
        agent: Analysis agent instance

    Returns:
        QueryExecutionResponse with session ID and status
    """
    logger.info(f"Received query execution request: '{request.query[:100]}...'")

    try:
        # Validate database exists before starting workflow
        from app.services.mindsdb_service import create_mindsdb_service
        mindsdb_service = create_mindsdb_service()

        try:
            databases = await mindsdb_service.get_databases()
            database_names = [
                db.get("name") if isinstance(db, dict) else str(db)
                for db in databases
            ]

            if request.database not in database_names:
                await mindsdb_service.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Database '{request.database}' not found. Available databases: {', '.join(database_names)}"
                )

            logger.info(f"Database '{request.database}' validated successfully")
        finally:
            await mindsdb_service.close()

        # For MVP, we'll execute synchronously
        # In production with WebSocket (PR#8), this would be async/background
        final_state = await agent.execute(
            query=request.query,
            database=request.database,
            session_id=request.session_id,
            options=request.options,
        )

        return QueryExecutionResponse(
            session_id=final_state["session_id"],
            status=final_state.get("workflow_status", "unknown"),
            message="Query execution completed",
            websocket_url=None,  # Will be added in PR#8
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}",
        )


# ============================================
# Endpoint: Execute Query with Streaming
# ============================================


@router.post("/query/stream")
async def execute_query_stream(
    request: QueryExecutionRequest,
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Execute a natural language query with real-time streaming updates.

    This endpoint uses Server-Sent Events (SSE) to stream workflow progress
    in real-time. Each event contains node updates as they occur.

    Args:
        request: Query execution request
        agent: Analysis agent instance

    Returns:
        StreamingResponse with SSE events
    """
    logger.info(f"Received streaming query request: '{request.query[:100]}...'")

    async def event_generator():
        """Generate SSE events from workflow stream."""
        try:
            async for event in agent.stream(
                query=request.query,
                database=request.database,
                user_id=request.user_id,
                company_id=request.company_id,
                session_id=request.session_id,
                options=request.options,
                stream_mode="updates",  # Only send node updates
            ):
                # Format as SSE event
                # Each event is: data: {json}\n\n
                event_data = json.dumps(event, default=str)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            error_event = {
                "error": str(e),
                "type": "error",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ============================================
# Endpoint: Resume Workflow
# ============================================


@router.post("/sessions/{session_id}/resume")
async def resume_workflow(
    session_id: str,
    response: HITLResponseSubmission,
    stream: bool = False,
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Resume a paused workflow with human response.

    This endpoint uses LangGraph's Command pattern to resume from an interrupt().

    Args:
        session_id: Session to resume
        response: Human response data
        stream: Whether to stream the resumption (default: False)
        agent: Analysis agent instance

    Returns:
        Final state (if stream=False) or streaming response (if stream=True)
    """
    logger.info(f"Resuming workflow for session: {session_id}")

    try:
        # Prepare human response in the format expected by interrupt()
        human_response = {
            "action": response.action,
            "modified_sql": response.modified_sql,
            "feedback": response.feedback,
            "data": response.data,
        }

        if stream:
            # Stream the resumption
            async def event_generator():
                try:
                    async for event in agent.resume_stream(
                        session_id=session_id,
                        human_response=human_response,
                        stream_mode="updates",
                    ):
                        event_data = json.dumps(event, default=str)
                        yield f"data: {event_data}\n\n"

                except Exception as e:
                    logger.error(f"Resume streaming failed: {e}")
                    error_event = {"error": str(e), "type": "error"}
                    yield f"data: {json.dumps(error_event)}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-streaming resumption
            final_state = await agent.resume(
                session_id=session_id,
                human_response=human_response,
            )

            return JSONResponse(
                content={
                    "session_id": session_id,
                    "status": final_state.get("workflow_status"),
                    "message": "Workflow resumed successfully",
                    "final_state": final_state,
                }
            )

    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume workflow: {str(e)}",
        )


# ============================================
# Endpoint: Get Workflow Status
# ============================================


@router.get("/status/{session_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    session_id: str,
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Get current status of a workflow execution.

    Args:
        session_id: Session identifier
        agent: Analysis agent instance

    Returns:
        WorkflowStatusResponse with current state
    """
    logger.info(f"Getting status for session: {session_id}")

    try:
        state = agent.get_state(session_id)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found",
            )

        return WorkflowStatusResponse(
            session_id=state["session_id"],
            workflow_status=state.get("workflow_status", "unknown"),
            query=state.get("query"),
            database=state.get("database"),
            generated_sql=state.get("generated_sql"),
            intent=state.get("intent"),
            confidence=state.get("confidence"),
            explanation=state.get("explanation"),
            query_success=state.get("query_success", False),
            row_count=state.get("row_count", 0),
            execution_time_ms=state.get("execution_time_ms", 0),
            query_error=state.get("query_error"),
            insights=state.get("insights", []),
            recommendations=state.get("recommendations", []),
            human_interventions_count=len(state.get("human_interventions", [])),
            total_tokens_used=state.get("total_tokens_used", 0),
            errors=state.get("errors", []),
            started_at=state.get("started_at"),
            completed_at=state.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}",
        )


# ============================================
# Endpoint: Get Query Results
# ============================================


@router.get("/results/{session_id}", response_model=QueryResultsResponse)
async def get_query_results(
    session_id: str,
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Get detailed query results including data.

    Args:
        session_id: Session identifier
        agent: Analysis agent instance

    Returns:
        QueryResultsResponse with data and analysis
    """
    logger.info(f"Getting results for session: {session_id}")

    try:
        state = agent.get_state(session_id)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found",
            )

        # Check if workflow is complete
        if state.get("workflow_status") not in ["completed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Workflow not complete. Current status: {state.get('workflow_status')}",
            )

        return QueryResultsResponse(
            session_id=state["session_id"],
            success=state.get("query_success", False),
            sql=state.get("generated_sql"),
            intent=state.get("intent"),
            confidence=state.get("confidence"),
            data=state.get("query_data"),
            row_count=state.get("row_count", 0),
            execution_time_ms=state.get("execution_time_ms", 0),
            analysis=state.get("analysis_results"),
            insights=state.get("insights", []),
            recommendations=state.get("recommendations", []),
            error=state.get("query_error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get results: {str(e)}",
        )


# ============================================
# Endpoint: List Sessions
# ============================================


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
):
    """
    List analysis sessions for current user.

    Note: This is a placeholder. In production, this would query
    the database for sessions filtered by user_id.

    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination

    Returns:
        SessionListResponse with session list
    """
    logger.info(f"Listing sessions: limit={limit}, offset={offset}")

    # Placeholder response
    # In production, query AnalysisSession table with user filter
    return SessionListResponse(
        total=0,
        sessions=[],
    )


# ============================================
# Endpoint: Get Pending Interventions
# ============================================


@router.get("/interventions/{session_id}", response_model=PendingInterventionsResponse)
async def get_pending_interventions(
    session_id: str,
    hitl_service: HITLService = Depends(get_hitl_service_dependency),
):
    """
    Get pending human intervention requests for a session.

    Args:
        session_id: Session identifier
        hitl_service: HITL service instance

    Returns:
        PendingInterventionsResponse with pending requests
    """
    logger.info(f"Getting pending interventions for session: {session_id}")

    try:
        pending_requests = hitl_service.get_pending_requests(session_id)

        interventions = [
            {
                "request_id": req.request_id,
                "intervention_type": req.intervention_type,
                "context": req.context,
                "options": [opt.model_dump() for opt in req.options],
                "requested_at": req.requested_at.isoformat(),
                "timeout_at": req.timeout_at.isoformat(),
            }
            for req in pending_requests
        ]

        return PendingInterventionsResponse(
            session_id=session_id,
            pending_count=len(interventions),
            interventions=interventions,
        )

    except Exception as e:
        logger.error(f"Failed to get pending interventions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending interventions: {str(e)}",
        )


# ============================================
# Endpoint: Submit HITL Response
# ============================================


@router.post("/interventions/{request_id}/respond")
async def submit_hitl_response(
    request_id: str,
    response: HITLResponseSubmission,
    hitl_service: HITLService = Depends(get_hitl_service_dependency),
    agent: AnalysisAgentLangGraph = Depends(get_agent),
):
    """
    Submit human response to an intervention request.

    After response is submitted, the workflow can be resumed.

    Args:
        request_id: Intervention request ID
        response: Human response
        hitl_service: HITL service instance
        agent: Analysis agent instance

    Returns:
        Success message
    """
    logger.info(f"Submitting HITL response for request: {request_id}")

    try:
        # Submit response
        success = await hitl_service.submit_response(
            request_id=response.request_id,
            action=response.action,
            data=response.data,
            feedback=response.feedback,
            modified_sql=response.modified_sql,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Intervention request {request_id} not found or expired",
            )

        return JSONResponse(
            content={
                "success": True,
                "message": f"Response submitted for request {request_id}",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit HITL response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit response: {str(e)}",
        )


# ============================================
# Endpoint: Cancel/Delete Session
# ============================================


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    hitl_service: HITLService = Depends(get_hitl_service_dependency),
):
    """
    Cancel and delete an analysis session.

    Args:
        session_id: Session identifier
        hitl_service: HITL service instance

    Returns:
        Success message
    """
    logger.info(f"Deleting session: {session_id}")

    try:
        # Cancel any pending interventions
        pending = hitl_service.get_pending_requests(session_id)
        for req in pending:
            await hitl_service.cancel_request(req.request_id)

        # In production, also delete from database
        # db.query(AnalysisSession).filter_by(id=session_id).delete()

        return JSONResponse(
            content={
                "success": True,
                "message": f"Session {session_id} deleted",
            }
        )

    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}",
        )
