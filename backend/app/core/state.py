"""
Agent State Management

This module provides state management for agents with:
- State persistence and serialization
- Query history tracking
- Schema caching
- Human intervention tracking
- User preferences storage
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryRecord(BaseModel):
    """Record of a single query in the session."""

    query: str
    sql: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None


class InterventionRecord(BaseModel):
    """Record of a human intervention."""

    intervention_id: str = Field(default_factory=lambda: str(uuid4()))
    intervention_type: str
    request_context: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None
    outcome: Optional[str] = None  # approved, rejected, timeout, modified
    automated_fallback: bool = False

    @property
    def response_time_ms(self) -> Optional[int]:
        """Calculate response time in milliseconds."""
        if self.requested_at and self.responded_at:
            delta = self.responded_at - self.requested_at
            return int(delta.total_seconds() * 1000)
        return None


class SchemaCache(BaseModel):
    """Cached database schema information."""

    database: str
    tables: Dict[str, Any]  # table_name -> table_info
    cached_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 7200  # 2 hours default

    @property
    def is_expired(self) -> bool:
        """Check if cache has expired."""
        age = (datetime.utcnow() - self.cached_at).total_seconds()
        return age > self.ttl_seconds


class UserPreferences(BaseModel):
    """User preferences for agent behavior."""

    auto_approve_high_confidence: bool = True
    confidence_threshold: float = 0.8
    default_row_limit: int = 1000
    prefer_visualization: bool = True
    preferred_style_template: str = "default"
    enable_explanations: bool = True
    timeout_seconds: int = 300


class AgentState(BaseModel):
    """
    Comprehensive agent state.

    This tracks everything about an agent session including:
    - Session metadata
    - Query history
    - Schema cache
    - Human interventions
    - User preferences
    - Execution statistics
    """

    # Session identification
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    company_id: Optional[str] = None

    # Current context
    current_database: Optional[str] = None
    current_query: Optional[str] = None

    # History
    query_history: List[QueryRecord] = Field(default_factory=list)
    interventions: List[InterventionRecord] = Field(default_factory=list)

    # Caching
    schema_cache: Optional[SchemaCache] = None

    # Preferences
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)

    # Statistics
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_tokens_used: int = 0
    total_intervention_count: int = 0

    # Confidence tracking
    confidence_scores: List[float] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)

    def add_query_record(self, record: QueryRecord):
        """
        Add a query to history and update statistics.

        Args:
            record: QueryRecord to add
        """
        self.query_history.append(record)
        self.total_queries += 1

        if record.success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1

        if record.confidence is not None:
            self.confidence_scores.append(record.confidence)

        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        logger.debug(f"Added query record to session {self.session_id}")

    def add_intervention(self, intervention: InterventionRecord):
        """
        Add an intervention record.

        Args:
            intervention: InterventionRecord to add
        """
        self.interventions.append(intervention)
        self.total_intervention_count += 1
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        logger.debug(
            f"Added intervention record to session {self.session_id}: {intervention.intervention_type}"
        )

    def update_schema_cache(self, database: str, tables: Dict[str, Any], ttl_seconds: int = 7200):
        """
        Update cached schema information.

        Args:
            database: Database name
            tables: Schema information
            ttl_seconds: Cache TTL in seconds
        """
        self.schema_cache = SchemaCache(
            database=database,
            tables=tables,
            ttl_seconds=ttl_seconds,
        )
        self.updated_at = datetime.utcnow()

        logger.debug(f"Updated schema cache for database {database} in session {self.session_id}")

    def get_schema_cache(self, database: str) -> Optional[Dict[str, Any]]:
        """
        Get cached schema if available and not expired.

        Args:
            database: Database name

        Returns:
            Cached schema tables or None if not available/expired
        """
        if not self.schema_cache:
            return None

        if self.schema_cache.database != database:
            return None

        if self.schema_cache.is_expired:
            logger.debug(f"Schema cache expired for database {database}")
            return None

        logger.debug(f"Using cached schema for database {database}")
        return self.schema_cache.tables

    def add_tokens_used(self, tokens: int):
        """
        Track token usage.

        Args:
            tokens: Number of tokens used
        """
        self.total_tokens_used += tokens
        self.updated_at = datetime.utcnow()

    def get_recent_queries(self, limit: int = 5) -> List[QueryRecord]:
        """
        Get most recent queries.

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of recent QueryRecords
        """
        return self.query_history[-limit:]

    def get_average_confidence(self) -> Optional[float]:
        """
        Calculate average confidence score.

        Returns:
            Average confidence or None if no scores available
        """
        if not self.confidence_scores:
            return None
        return sum(self.confidence_scores) / len(self.confidence_scores)

    def get_success_rate(self) -> float:
        """
        Calculate query success rate.

        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of state
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """
        Create AgentState from dictionary.

        Args:
            data: Dictionary with state data

        Returns:
            AgentState instance
        """
        return cls(**data)

    def get_context_for_prompt(self) -> Dict[str, Any]:
        """
        Get relevant context for including in agent prompts.

        Returns:
            Dictionary with context information
        """
        recent_queries = self.get_recent_queries(3)

        return {
            "session_id": self.session_id,
            "current_database": self.current_database,
            "recent_queries": [
                {
                    "query": q.query,
                    "intent": q.intent,
                    "success": q.success,
                }
                for q in recent_queries
            ],
            "user_preferences": self.user_preferences.model_dump(),
            "average_confidence": self.get_average_confidence(),
            "total_queries": self.total_queries,
        }


class StateManager:
    """
    Manager for agent states.

    This provides an in-memory store for agent states during execution.
    For production, this should be backed by Redis or similar.
    """

    def __init__(self):
        """Initialize state manager."""
        self._states: Dict[str, AgentState] = {}
        logger.info("StateManager initialized")

    def create_state(
        self,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        database: Optional[str] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> AgentState:
        """
        Create a new agent state.

        Args:
            user_id: Optional user ID
            company_id: Optional company ID
            database: Optional default database
            preferences: Optional user preferences

        Returns:
            New AgentState instance
        """
        state = AgentState(
            user_id=user_id,
            company_id=company_id,
            current_database=database,
            user_preferences=preferences or UserPreferences(),
        )

        self._states[state.session_id] = state
        logger.info(f"Created new agent state: {state.session_id}")

        return state

    def get_state(self, session_id: str) -> Optional[AgentState]:
        """
        Get agent state by session ID.

        Args:
            session_id: Session identifier

        Returns:
            AgentState or None if not found
        """
        return self._states.get(session_id)

    def update_state(self, state: AgentState):
        """
        Update stored agent state.

        Args:
            state: AgentState to update
        """
        self._states[state.session_id] = state
        state.updated_at = datetime.utcnow()

    def delete_state(self, session_id: str):
        """
        Delete agent state.

        Args:
            session_id: Session identifier
        """
        if session_id in self._states:
            del self._states[session_id]
            logger.info(f"Deleted agent state: {session_id}")

    def list_active_sessions(self) -> List[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        return list(self._states.keys())

    def cleanup_expired_states(self, max_age_hours: int = 24):
        """
        Remove states that haven't been active recently.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        now = datetime.utcnow()
        expired = []

        for session_id, state in self._states.items():
            age_hours = (now - state.last_activity_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired.append(session_id)

        for session_id in expired:
            self.delete_state(session_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired states")


# Global state manager instance
state_manager = StateManager()


def get_state_manager() -> StateManager:
    """
    Get global state manager instance.

    Returns:
        StateManager instance
    """
    return state_manager
