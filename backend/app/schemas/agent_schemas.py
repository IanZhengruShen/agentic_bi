"""
Pydantic Schemas for Agent API

Request and response models for agent-related API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================
# Request Schemas
# ============================================


class QueryExecutionRequest(BaseModel):
    """Request to execute a natural language query."""

    query: str = Field(..., min_length=3, max_length=1000, description="Natural language query")
    database: str = Field(..., min_length=1, max_length=255, description="Target database name")

    # Optional parameters
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_id: Optional[str] = Field(None, description="User ID for tracking")
    company_id: Optional[str] = Field(None, description="Company ID for multi-tenancy")
    options: Dict[str, Any] = Field(
        default_factory=lambda: {
            "limit_rows": 1000,
            "include_analysis": True,
            "explain_query": True,
        },
        description="Execution options",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me total sales by region for Q4 2024",
                "database": "sales_db",
                "options": {
                    "limit_rows": 1000,
                    "include_analysis": True,
                },
            }
        }


class HITLResponseSubmission(BaseModel):
    """Human response to an intervention request."""

    request_id: str = Field(..., description="Intervention request ID")
    action: str = Field(..., description="Action taken (approve, reject, modify, etc.)")
    modified_sql: Optional[str] = Field(None, description="Modified SQL (if action=modify)")
    feedback: Optional[str] = Field(None, description="Optional feedback text")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_123456",
                "action": "approve",
            }
        }


# ============================================
# Response Schemas
# ============================================


class QueryExecutionResponse(BaseModel):
    """Response after initiating query execution."""

    session_id: str = Field(..., description="Session ID for tracking")
    status: str = Field(..., description="Current workflow status")
    message: str = Field(..., description="Human-readable message")
    websocket_url: Optional[str] = Field(None, description="WebSocket URL for real-time updates")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "status": "analyzing",
                "message": "Query execution started",
                "websocket_url": "ws://localhost:8000/ws/session_abc123",
            }
        }


class WorkflowStatusResponse(BaseModel):
    """Current status of a workflow execution."""

    session_id: str
    workflow_status: str = Field(..., description="Overall workflow status")

    # Query details
    query: Optional[str] = None
    database: Optional[str] = None

    # SQL generation
    generated_sql: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None

    # Execution results
    query_success: bool = False
    row_count: int = 0
    execution_time_ms: int = 0
    query_error: Optional[str] = None

    # Analysis
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    human_interventions_count: int = 0
    total_tokens_used: int = 0
    errors: List[str] = Field(default_factory=list)

    # Timestamps
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "workflow_status": "completed",
                "query": "Show me total sales by region",
                "generated_sql": "SELECT region, SUM(sales) FROM sales_table GROUP BY region",
                "confidence": 0.95,
                "query_success": True,
                "row_count": 5,
                "insights": ["Top performing region is West with $2.5M in sales"],
            }
        }


class QueryResultsResponse(BaseModel):
    """Detailed query results with data."""

    session_id: str
    success: bool

    # SQL and metadata
    sql: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None

    # Results
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time_ms: int = 0

    # Analysis
    analysis: Optional[Dict[str, Any]] = None
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Error info
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "success": True,
                "sql": "SELECT * FROM users LIMIT 10",
                "data": [
                    {"id": 1, "name": "John Doe", "email": "john@example.com"},
                    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
                ],
                "row_count": 2,
                "insights": ["Dataset contains 2 users"],
            }
        }


class SessionListResponse(BaseModel):
    """List of analysis sessions."""

    total: int = Field(..., description="Total number of sessions")
    sessions: List[Dict[str, Any]] = Field(..., description="Session summaries")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "sessions": [
                    {
                        "session_id": "session_abc123",
                        "query": "Show me sales",
                        "status": "completed",
                        "created_at": "2024-11-03T10:00:00Z",
                    },
                    {
                        "session_id": "session_def456",
                        "query": "Get user count",
                        "status": "analyzing",
                        "created_at": "2024-11-03T11:00:00Z",
                    },
                ],
            }
        }


class PendingInterventionsResponse(BaseModel):
    """List of pending human interventions."""

    session_id: str
    pending_count: int
    interventions: List[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "pending_count": 1,
                "interventions": [
                    {
                        "request_id": "req_123",
                        "intervention_type": "approve_query",
                        "context": {
                            "generated_sql": "SELECT * FROM users",
                            "confidence": 0.75,
                        },
                        "requested_at": "2024-11-03T10:00:00Z",
                        "timeout_at": "2024-11-03T10:05:00Z",
                    }
                ],
            }
        }


# ============================================
# Error Response Schema
# ============================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Query execution failed",
                "details": {"reason": "Invalid SQL syntax"},
                "timestamp": "2024-11-03T10:00:00Z",
            }
        }


# ============================================
# Health Check Schema
# ============================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    services: Dict[str, bool] = Field(..., description="Service availability")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "database": True,
                    "mindsdb": True,
                    "langfuse": True,
                },
            }
        }
