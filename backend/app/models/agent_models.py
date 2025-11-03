"""
Database Models for Agent System

Models for:
- Analysis Sessions
- Human Interventions
- Query History
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    Float,
    BigInteger,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.models.base import Base


class AnalysisSession(Base):
    """
    Analysis session tracking.

    Tracks complete agent execution sessions including:
    - Query information
    - Execution details
    - Results and state
    - Status tracking
    """

    __tablename__ = "analysis_sessions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User relationships (FK will be added when user models exist)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # FK to users table
    company_id = Column(UUID(as_uuid=True), nullable=True)  # FK to companies table

    # Query information
    query = Column(Text, nullable=False, comment="Natural language query from user")
    query_type = Column(String(50), nullable=True, comment="Query intent type")
    generated_sql = Column(Text, nullable=True, comment="AI-generated SQL")
    final_sql = Column(Text, nullable=True, comment="Final SQL (after human modifications)")

    # Execution details
    database_connection_id = Column(UUID(as_uuid=True), nullable=True)
    execution_time_ms = Column(Integer, nullable=True, comment="Query execution time in milliseconds")
    rows_returned = Column(Integer, nullable=True, comment="Number of rows returned")
    data_size_bytes = Column(BigInteger, nullable=True, comment="Size of result data in bytes")

    # Results and state (JSONB for flexibility)
    results = Column(JSONB, nullable=True, comment="Query results")
    visualizations = Column(JSONB, nullable=True, comment="Generated visualizations")
    workflow_state = Column(JSONB, nullable=True, comment="Workflow execution state")
    agent_interactions = Column(JSONB, nullable=True, comment="Agent interaction history")

    # Status tracking
    status = Column(
        String(50),
        nullable=False,
        default="created",
        comment="Session status",
    )

    # Error information
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Confidence and quality metrics
    confidence_score = Column(Float, nullable=True, comment="SQL generation confidence (0-1)")
    human_intervention_count = Column(Integer, default=0, comment="Number of HITL interventions")
    total_tokens_used = Column(Integer, default=0, comment="Total LLM tokens consumed")

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'analyzing', 'awaiting_approval', 'executing', "
            "'visualizing', 'completed', 'failed', 'cancelled')",
            name="valid_status",
        ),
    )

    def __repr__(self):
        return (
            f"<AnalysisSession(id={self.id}, "
            f"status={self.status}, "
            f"query='{self.query[:50]}...')>"
        )


class HumanIntervention(Base):
    """
    Human-in-the-loop intervention tracking.

    Records all instances where human input was requested during
    agent execution, including the context, response, and timing.
    """

    __tablename__ = "human_interventions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    session_id = Column(
        UUID(as_uuid=True),
        # ForeignKey("analysis_sessions.id", ondelete="CASCADE"),  # Uncomment when analysis_sessions exists
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=True)  # User who responded

    # Intervention details
    intervention_type = Column(
        String(50),
        nullable=False,
        comment="Type of intervention requested",
    )
    intervention_reason = Column(String(255), nullable=True, comment="Why intervention was needed")

    # Request and response data
    request_data = Column(JSONB, nullable=False, comment="Context provided to human")
    response_data = Column(JSONB, nullable=True, comment="Human's response")

    # Timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    timeout_at = Column(DateTime(timezone=True), nullable=True)
    response_time_ms = Column(Integer, nullable=True, comment="Time to respond in milliseconds")

    # Outcome
    outcome = Column(
        String(50),
        nullable=True,
        comment="Outcome: approved, rejected, timeout, modified, etc.",
    )
    automated_fallback = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether fallback logic was used",
    )

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "intervention_type IN ('approve_query', 'modify_query', 'select_visualization', "
            "'modify_parameters', 'confirm_results', 'handle_validation_error')",
            name="valid_intervention_type",
        ),
    )

    def __repr__(self):
        return (
            f"<HumanIntervention(id={self.id}, "
            f"session_id={self.session_id}, "
            f"type={self.intervention_type}, "
            f"outcome={self.outcome})>"
        )


class QueryHistory(Base):
    """
    Query history for auditing and learning.

    Simplified model for tracking queries over time,
    useful for analytics and improving agent performance.
    """

    __tablename__ = "query_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    session_id = Column(
        UUID(as_uuid=True),
        # ForeignKey("analysis_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Query details
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    database_name = Column(String(255), nullable=True)

    # Results
    success = Column(Boolean, default=True, nullable=False)
    row_count = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # Metadata
    intent = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"<QueryHistory(id={self.id}, "
            f"success={self.success}, "
            f"query='{self.natural_language_query[:50]}...')>"
        )
