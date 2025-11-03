"""Pydantic schemas for API request/response validation."""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
)

from app.schemas.company import (
    CompanyBase,
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)

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

from app.schemas.visualization_schemas import (
    # Visualization schemas
    VisualizationRequest,
    VisualizationResponse,
    VisualizationListResponse,
    ChartRecommendation,
    PlotlyFigureResponse,
    # Custom style profile schemas
    CustomStyleProfileCreate,
    CustomStyleProfileUpdate,
    CustomStyleProfileResponse,
    CustomStyleProfileListResponse,
    LogoUploadResponse,
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "TokenResponse",
    "TokenRefreshRequest",
    "PasswordChangeRequest",
    # Company schemas
    "CompanyBase",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
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
    # Visualization schemas
    "VisualizationRequest",
    "VisualizationResponse",
    "VisualizationListResponse",
    "ChartRecommendation",
    "PlotlyFigureResponse",
    # Custom style profile schemas
    "CustomStyleProfileCreate",
    "CustomStyleProfileUpdate",
    "CustomStyleProfileResponse",
    "CustomStyleProfileListResponse",
    "LogoUploadResponse",
]
