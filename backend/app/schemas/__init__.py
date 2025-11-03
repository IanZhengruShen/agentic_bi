"""Pydantic schemas for API request/response validation."""

from app.schemas.agent_schemas import (
    # Request schemas
    QueryExecutionRequest,
    HITLResponseSubmission,
    # Response schemas
    QueryExecutionResponse,
    WorkflowStatusResponse,
    QueryResultsResponse,
    SessionListResponse,
    PendingInterventionsResponse,
    ErrorResponse,
    HealthCheckResponse,
)

from app.schemas.sql_schemas import (
    SQLValidationIssue,
    SQLValidationResult,
    SQLErrorCategory,
)

__all__ = [
    # Requests
    "QueryExecutionRequest",
    "HITLResponseSubmission",
    # Responses
    "QueryExecutionResponse",
    "WorkflowStatusResponse",
    "QueryResultsResponse",
    "SessionListResponse",
    "PendingInterventionsResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    # SQL Validation
    "SQLValidationIssue",
    "SQLValidationResult",
    "SQLErrorCategory",
]
