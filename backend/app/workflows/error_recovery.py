"""
Error Recovery Strategies for Multi-Agent Workflows.

This module provides error handling and recovery strategies for the
unified workflow orchestrator. The goal is to maximize partial success
and provide useful feedback even when parts of the workflow fail.

Key Strategies:
1. Partial Success: Return analysis results even if visualization fails
2. Graceful Degradation: Fall back to simpler operations when advanced ones fail
3. Informative Errors: Provide actionable error messages
4. Retry Logic: (Future) Implement retry with exponential backoff for transient errors

Design Philosophy:
- Analysis failure = workflow failure (cannot proceed without data)
- Visualization failure = partial success (analysis results still valuable)
- LLM failures = graceful degradation (use rule-based fallbacks)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """
    Error recovery strategies for unified workflows.

    This class implements various error handling patterns to ensure
    workflows provide maximum value even when components fail.
    """

    @staticmethod
    def handle_analysis_failure(
        workflow_id: str,
        error: Exception,
        state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle AnalysisAgent failure.

        Analysis failure is FATAL for the workflow - cannot proceed
        without data. Return error state immediately.

        Args:
            workflow_id: Workflow ID
            error: Exception that occurred
            state: Current workflow state (optional)

        Returns:
            Error state updates
        """
        logger.error(
            f"[ErrorRecovery] AnalysisAgent failed for workflow {workflow_id}: {error}"
        )

        error_message = str(error)

        # Provide specific guidance based on error type
        if "connection" in error_message.lower():
            guidance = "Database connection failed. Check database availability and credentials."
        elif "sql" in error_message.lower() or "syntax" in error_message.lower():
            guidance = "SQL generation or execution failed. Try rephrasing your query."
        elif "timeout" in error_message.lower():
            guidance = "Query timed out. Try querying less data or simplifying the request."
        else:
            guidance = "Analysis failed. Please check your query and try again."

        return {
            "workflow_status": "failed",
            "workflow_stage": "failed",
            "errors": [f"Analysis failed: {error_message}"],
            "recommendations": [guidance],
            "partial_success": False,
        }

    @staticmethod
    def handle_visualization_failure(
        workflow_id: str,
        error: Exception,
        state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle VisualizationAgent failure.

        Visualization failure is NON-FATAL - we can return analysis results
        without the chart. Mark as partial success.

        Args:
            workflow_id: Workflow ID
            error: Exception that occurred
            state: Current workflow state (optional)

        Returns:
            Partial success state updates
        """
        logger.warning(
            f"[ErrorRecovery] VisualizationAgent failed for workflow {workflow_id}: {error}. "
            f"Returning analysis results without visualization."
        )

        error_message = str(error)

        # Provide specific guidance
        if "data" in error_message.lower():
            guidance = "Data format incompatible with visualization. Analysis results available."
        elif "chart" in error_message.lower() or "plotly" in error_message.lower():
            guidance = "Chart generation failed. You can view the raw data results."
        else:
            guidance = "Visualization unavailable. Analysis results are still available."

        return {
            "workflow_status": "partial_success",
            "workflow_stage": "visualized",  # Reached viz stage, even if failed
            "warnings": [f"Visualization failed: {error_message}"],
            "recommendations": [guidance],
            "partial_success": True,
            # Don't set visualization_id to indicate it didn't complete
        }

    @staticmethod
    def handle_decision_failure(
        workflow_id: str,
        error: Exception,
        default_decision: bool = True,
    ) -> Dict[str, Any]:
        """
        Handle visualization decision failure.

        If the LLM-based decision fails, fall back to a default decision.
        Default is True (bias toward creating visualizations).

        Args:
            workflow_id: Workflow ID
            error: Exception that occurred
            default_decision: Default visualization decision (default True)

        Returns:
            State updates with default decision
        """
        logger.warning(
            f"[ErrorRecovery] Visualization decision failed for workflow {workflow_id}: {error}. "
            f"Using default decision: {default_decision}"
        )

        return {
            "should_visualize": default_decision,
            "visualization_reasoning": f"Decision engine unavailable, defaulting to visualize={default_decision}",
            "warnings": [f"Visualization decision LLM failed: {str(error)}"],
        }

    @staticmethod
    def create_error_response(
        workflow_id: str,
        error_message: str,
        created_at: Optional[str] = None,
        agents_executed: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            workflow_id: Workflow ID
            error_message: Error message
            created_at: When workflow started
            agents_executed: List of agents that executed before failure

        Returns:
            Complete error response
        """
        completed_at = datetime.utcnow().isoformat()
        execution_time_ms = 0

        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                completed = datetime.fromisoformat(completed_at)
                execution_time_ms = int((completed - created).total_seconds() * 1000)
            except Exception:
                pass

        return {
            "workflow_id": workflow_id,
            "workflow_status": "failed",
            "workflow_stage": "failed",
            "errors": [error_message],
            "created_at": created_at or datetime.utcnow().isoformat(),
            "completed_at": completed_at,
            "execution_time_ms": execution_time_ms,
            "agents_executed": agents_executed or [],
            "query_success": False,
            "partial_success": False,
        }


class RetryPolicy:
    """
    Retry policies for transient errors.

    Future enhancement: Implement exponential backoff retry logic
    for database connection errors, LLM timeouts, etc.

    For initial implementation, we'll handle retries within each agent.
    This class is a placeholder for future enhancements.
    """

    @staticmethod
    def should_retry(error: Exception, retry_count: int) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            error: Exception that occurred
            retry_count: Current retry attempt count

        Returns:
            True if should retry, False otherwise
        """
        # For now, no automatic retries at workflow level
        # Individual agents handle their own retries
        return False

    @staticmethod
    def get_retry_delay(retry_count: int) -> float:
        """
        Calculate retry delay with exponential backoff.

        Args:
            retry_count: Current retry attempt count

        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        return min(2 ** retry_count, 30)  # Cap at 30 seconds


# Singleton instances for easy access
error_recovery = ErrorRecoveryStrategy()
retry_policy = RetryPolicy()
