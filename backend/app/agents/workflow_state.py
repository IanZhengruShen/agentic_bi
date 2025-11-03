"""
LangGraph Workflow State Definition

This module defines the state schema for the LangGraph-based
agent workflow, following the TypedDict pattern required by LangGraph.
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime
import operator


class WorkflowState(TypedDict):
    """
    State for LangGraph workflow execution.

    This follows LangGraph's state management pattern where:
    - Fields are strongly typed
    - State is passed between nodes
    - Reducers can be defined for list/dict accumulation
    """

    # Session identification
    session_id: str
    user_id: Optional[str]
    company_id: Optional[str]

    # Input
    query: str  # Natural language query
    database: str  # Target database
    options: Dict[str, Any]  # User options

    # Schema information
    schema: Optional[Dict[str, Any]]

    # SQL generation
    generated_sql: Optional[str]
    intent: Optional[str]
    confidence: Optional[float]
    explanation: Optional[str]
    tables_used: Annotated[List[str], operator.add]  # Accumulate across retries
    warnings: Annotated[List[str], operator.add]  # Accumulate warnings
    needs_human_review: bool

    # Validation
    sql_valid: bool
    validation_errors: Annotated[List[str], operator.add]
    validation_warnings: Annotated[List[str], operator.add]

    # Human interventions
    human_interventions: Annotated[List[Dict[str, Any]], operator.add]
    intervention_outcomes: Annotated[List[str], operator.add]

    # Execution
    query_success: bool
    query_data: Optional[List[Dict[str, Any]]]
    row_count: int
    execution_time_ms: int
    query_error: Optional[str]

    # Analysis
    analysis_results: Optional[Dict[str, Any]]
    insights: Annotated[List[str], operator.add]
    recommendations: Annotated[List[str], operator.add]

    # Enhanced analysis (PR#5 - additional tools like correlation, filtering, aggregation)
    enhanced_analysis: Optional[Dict[str, Any]]

    # Visualization (for future PRs)
    visualizations: Annotated[List[Dict[str, Any]], operator.add]

    # Error tracking
    errors: Annotated[List[str], operator.add]

    # Workflow control
    workflow_status: str  # created, analyzing, reviewing, executing, completed, failed
    retry_count: int

    # Metadata
    total_tokens_used: int
    started_at: str  # ISO format datetime
    completed_at: Optional[str]


def create_initial_state(
    session_id: str,
    query: str,
    database: str,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    """
    Create initial workflow state.

    Args:
        session_id: Session identifier
        query: Natural language query
        database: Target database
        user_id: Optional user ID
        company_id: Optional company ID
        options: Optional configuration options

    Returns:
        Initial WorkflowState
    """
    return WorkflowState(
        # Session
        session_id=session_id,
        user_id=user_id,
        company_id=company_id,

        # Input
        query=query,
        database=database,
        options=options or {},

        # Schema
        schema=None,

        # SQL generation
        generated_sql=None,
        intent=None,
        confidence=None,
        explanation=None,
        tables_used=[],
        warnings=[],
        needs_human_review=False,

        # Validation
        sql_valid=False,
        validation_errors=[],
        validation_warnings=[],

        # Human interventions
        human_interventions=[],
        intervention_outcomes=[],

        # Execution
        query_success=False,
        query_data=None,
        row_count=0,
        execution_time_ms=0,
        query_error=None,

        # Analysis
        analysis_results=None,
        insights=[],
        recommendations=[],

        # Enhanced analysis
        enhanced_analysis=None,

        # Visualization
        visualizations=[],

        # Errors
        errors=[],

        # Workflow control
        workflow_status="created",
        retry_count=0,

        # Metadata
        total_tokens_used=0,
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )
