"""
LangGraph Workflow Nodes

Each node is a function that:
1. Receives the current state
2. Performs an action (call tool, LLM, etc.)
3. Returns updated state

Nodes are composable and can be chained together by LangGraph.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from app.agents.workflow_state import WorkflowState
from app.core.llm import LLMClient
from app.core.config import settings
from app.core.prompts import PromptType, get_prompt
from app.services.mindsdb_service import MindsDBService
from app.services.hitl_service import HITLService
from app.tools.sql_tools import (
    explore_schema,
    generate_sql,
    validate_query,
    execute_sql_query,
)
from app.tools.analysis_tools import analyze_data
import json

logger = logging.getLogger(__name__)


# ============================================
# Node: Identify Query Intent
# ============================================


async def identify_intent_node(
    state: WorkflowState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Node: Identify if query is data analysis related or not.

    This is the first node in the workflow. It classifies whether
    the user query requires data analysis (SQL generation, querying)
    or is something else (greeting, general question, etc.).

    Args:
        state: Current workflow state
        llm_client: LLM client instance

    Returns:
        State updates with intent classification
    """
    logger.info(f"[Node: identify_intent] Query: {state['query'][:100]}...")

    try:
        # Get intent classification prompt
        intent_prompt = get_prompt(PromptType.QUERY_INTENT)
        prompt = intent_prompt.render(query=state["query"])

        # Call LLM to classify intent
        llm_response = await llm_client.chat_completion_with_system(
            system_message="You are an intent classifier for a business intelligence system.",
            user_message=prompt,
            temperature=0.1,  # Low temperature for classification
            max_tokens=200,
        )

        response = llm_response.content

        # Parse JSON response
        try:
            intent_result = json.loads(response)
            intent = intent_result.get("intent", "OTHER")
            confidence = intent_result.get("confidence", 0.0)
            reasoning = intent_result.get("reasoning", "")

            logger.info(
                f"Intent classified as: {intent} "
                f"(confidence: {confidence:.2f}, reasoning: {reasoning})"
            )

            return {
                "query_intent": intent,
                "intent_confidence": confidence,
                "intent_reasoning": reasoning,
                "workflow_status": "intent_identified",
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse intent response as JSON: {e}")
            # Fallback: check if response contains "DATA_ANALYSIS"
            if "DATA_ANALYSIS" in response.upper():
                return {
                    "query_intent": "DATA_ANALYSIS",
                    "intent_confidence": 0.5,
                    "intent_reasoning": "Fallback classification from text response",
                    "workflow_status": "intent_identified",
                }
            else:
                return {
                    "query_intent": "OTHER",
                    "intent_confidence": 0.5,
                    "intent_reasoning": "Fallback classification from text response",
                    "workflow_status": "intent_identified",
                }

    except Exception as e:
        logger.error(f"Intent identification failed: {e}")
        # Default to data analysis on error to not break workflow
        return {
            "query_intent": "DATA_ANALYSIS",
            "intent_confidence": 0.3,
            "intent_reasoning": f"Error during classification: {str(e)}",
            "workflow_status": "intent_identified",
        }


# ============================================
# Node: Handle Non-Analysis Query
# ============================================


async def handle_non_analysis_node(
    state: WorkflowState,
) -> Dict[str, Any]:
    """
    Node: Handle non-data-analysis queries with a polite response.

    This node is called when the query intent is classified as "OTHER"
    (not data analysis related). It returns a simple response explaining
    the AI's purpose.

    Args:
        state: Current workflow state

    Returns:
        State updates with polite rejection message
    """
    logger.info(f"[Node: handle_non_analysis] Query: {state['query'][:100]}...")

    # Check if it's a greeting
    query_lower = state["query"].lower().strip()
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    is_greeting = any(greeting in query_lower for greeting in greetings)

    if is_greeting:
        message = (
            "Hello! I'm an AI data analyst assistant. I can help you analyze data, "
            "generate SQL queries, create visualizations, and provide insights from your databases. "
            "\n\nHow can I help you with your data today?"
        )
    else:
        # Extract the topic they're asking about (simple heuristic)
        message = (
            f"I'm an AI data analyst specialized in business intelligence and data analysis. "
            f"I cannot help you with '{state['query']}' as it's outside my area of expertise. "
            "\n\nI can help you with:\n"
            "• Querying databases with natural language\n"
            "• Analyzing data and generating insights\n"
            "• Creating visualizations and reports\n"
            "• Identifying trends and patterns in your data\n"
            "\nPlease ask me a data-related question!"
        )

    # Calculate execution time
    from datetime import datetime as dt
    started_at = dt.fromisoformat(state["started_at"])
    completed_at = datetime.utcnow()
    execution_time_ms = int((completed_at - started_at).total_seconds() * 1000)

    return {
        "workflow_status": "completed",
        "query_success": False,
        "final_message": message,
        "intent_rejection": True,
        "completed_at": completed_at.isoformat(),
        "execution_time_ms": execution_time_ms,
    }


# ============================================
# Node: Explore Schema
# ============================================


async def explore_schema_node(
    state: WorkflowState,
    mindsdb_service: MindsDBService,
) -> Dict[str, Any]:
    """
    Node: Explore database schema.

    Args:
        state: Current workflow state
        mindsdb_service: MindsDB service instance

    Returns:
        State updates
    """
    logger.info(f"[Node: explore_schema] Database: {state['database']}")

    try:
        schema_info = await explore_schema(
            database=state["database"],
            mindsdb_service=mindsdb_service,
        )

        return {
            "schema": {
                "database": schema_info.database,
                "tables": schema_info.tables,
            },
            "workflow_status": "analyzing",
        }

    except Exception as e:
        logger.error(f"Schema exploration failed: {e}")
        return {
            "errors": [f"Schema exploration failed: {str(e)}"],
            "workflow_status": "failed",
        }


# ============================================
# Node: Generate SQL
# ============================================


async def generate_sql_node(
    state: WorkflowState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Node: Generate SQL from natural language.

    Args:
        state: Current workflow state
        llm_client: LLM client instance

    Returns:
        State updates
    """
    logger.info(f"[Node: generate_sql] Query: {state['query'][:100]}...")

    try:
        # Prepare context from state
        context = {
            "session_id": state["session_id"],
            "retry_count": state["retry_count"],
        }

        sql_result = await generate_sql(
            query=state["query"],
            schema=state["schema"] or {},
            llm_client=llm_client,
            context=context,
            confidence_threshold=settings.agent.sql_confidence_threshold,
        )

        return {
            "generated_sql": sql_result.sql,
            "intent": sql_result.intent,
            "confidence": sql_result.confidence,
            "explanation": sql_result.explanation,
            "tables_used": sql_result.tables_used,
            "warnings": sql_result.warnings,
            "needs_human_review": sql_result.needs_human_review,
            "total_tokens_used": state["total_tokens_used"] + 500,  # Approximate
        }

    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        return {
            "errors": [f"SQL generation failed: {str(e)}"],
            "workflow_status": "failed",
        }


# ============================================
# Node: Human Review (HITL)
# ============================================


async def human_review_node(
    state: WorkflowState,
    hitl_service: HITLService,
) -> Dict[str, Any]:
    """
    Node: Request human review for generated SQL using interrupt().

    This implementation uses LangGraph's interrupt() pattern for true
    pause/resume functionality, allowing thousands of concurrent workflows.

    Args:
        state: Current workflow state
        hitl_service: HITL service instance (for optional WebSocket notifications)

    Returns:
        State updates
    """
    from langgraph.types import interrupt

    logger.info("[Node: human_review] Requesting approval...")

    try:
        # Optional: Send WebSocket notification that workflow is paused
        if hitl_service:
            await hitl_service.notify_intervention_requested(
                session_id=state["session_id"],
                context={
                    "generated_sql": state["generated_sql"],
                    "confidence": state["confidence"],
                    "explanation": state["explanation"],
                    "warnings": state["warnings"],
                    "intent": state["intent"],
                }
            )

        # Pause workflow and wait for human input
        # This doesn't block - the workflow state is persisted and can resume later
        human_response = interrupt({
            "type": "human_review",
            "session_id": state["session_id"],
            "intervention_type": "approve_query",
            "context": {
                "generated_sql": state["generated_sql"],
                "confidence": state["confidence"],
                "explanation": state["explanation"],
                "warnings": state["warnings"],
                "intent": state["intent"],
            },
            "options": [
                {
                    "action": "approve",
                    "label": "Execute as-is",
                    "description": "Execute the generated SQL",
                },
                {
                    "action": "modify",
                    "label": "Modify SQL",
                    "description": "Provide modified SQL",
                },
                {
                    "action": "reject",
                    "label": "Reject",
                    "description": "Reject and stop",
                },
            ],
        })

        # When execution resumes, human_response contains the user's decision
        logger.info(f"[Node: human_review] Received response: {human_response.get('action')}")

        # Record intervention
        intervention_record = {
            "type": "approve_query",
            "outcome": human_response.get("action"),
            "timestamp": datetime.utcnow().isoformat(),
            "response": human_response,
        }

        updates = {
            "human_interventions": [intervention_record],
            "intervention_outcomes": [human_response.get("action")],
            "workflow_status": "reviewing",
        }

        # Handle outcome
        if human_response.get("action") == "modify" and human_response.get("modified_sql"):
            updates["generated_sql"] = human_response["modified_sql"]
            updates["needs_human_review"] = False

        elif human_response.get("action") == "reject":
            updates["workflow_status"] = "failed"
            updates["errors"] = ["Query rejected by user"]

        elif human_response.get("action") == "approve":
            updates["needs_human_review"] = False

        return updates

    except Exception as e:
        logger.error(f"Human review failed: {e}")
        return {
            "errors": [f"Human review failed: {str(e)}"],
            "workflow_status": "failed",
        }


# ============================================
# Node: Validate SQL
# ============================================


async def validate_sql_node(
    state: WorkflowState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Node: Validate SQL query for safety (basic + advanced).

    This node performs two-stage validation:
    1. Basic validation (syntax, safety checks)
    2. Advanced LLM-based validation (subtle errors, best practices)

    Args:
        state: Current workflow state
        llm_client: LLM client for advanced validation

    Returns:
        State updates
    """
    logger.info("[Node: validate_sql] Validating query...")

    try:
        # Stage 1: Basic validation
        basic_validation = await validate_query(
            query=state["generated_sql"] or "",
            llm_client=llm_client,
            schema=state["schema"],
        )

        # Stage 2: Advanced LLM-based validation
        advanced_validation = await advanced_validate_sql(
            query=state["generated_sql"] or "",
            schema=state["schema"],
            database=state["database"],
            llm_client=llm_client,
        )

        # Combine results
        all_errors = basic_validation.errors + [
            issue.message for issue in advanced_validation.errors
        ]
        all_warnings = basic_validation.warnings + [
            issue.message for issue in advanced_validation.warnings
        ]

        # If advanced validation suggests a fix and it's high confidence, apply it
        if (
            advanced_validation.suggested_fix
            and advanced_validation.confidence > 0.9
            and not basic_validation.valid
        ):
            logger.info(
                f"[Node: validate_sql] Applying auto-fix (confidence: {advanced_validation.confidence})"
            )
            return {
                "generated_sql": advanced_validation.suggested_fix,
                "sql_valid": True,
                "validation_errors": [],
                "validation_warnings": [
                    f"Auto-fixed: {err}" for err in all_errors
                ] + all_warnings,
            }

        # Otherwise return validation status
        return {
            "sql_valid": basic_validation.valid and advanced_validation.valid,
            "validation_errors": all_errors,
            "validation_warnings": all_warnings,
        }

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "sql_valid": False,
            "validation_errors": [f"Validation error: {str(e)}"],
        }


async def advanced_validate_sql(
    query: str,
    schema: Dict[str, Any],
    database: str,
    llm_client: LLMClient,
) -> "SQLValidationResult":
    """
    Advanced SQL validation using LLM to detect subtle errors.

    Checks for:
    - NOT IN with NULL values
    - UNION vs UNION ALL misuse
    - BETWEEN for exclusive ranges
    - Data type mismatches in predicates
    - Improper identifier quoting
    - Incorrect function argument counts
    - Type casting errors
    - JOIN column mismatches
    - SQL injection patterns
    - Performance issues

    Args:
        query: SQL query to validate
        schema: Database schema information
        database: Database name/dialect
        llm_client: LLM client for validation

    Returns:
        SQLValidationResult with issues and suggested fixes
    """
    from app.schemas.sql_schemas import SQLValidationResult, SQLValidationIssue, SQLErrorCategory

    logger.info("[Advanced Validation] Analyzing query for subtle errors...")

    # Build comprehensive validation prompt
    validation_prompt = f"""You are an expert SQL validator. Analyze this query for common mistakes and best practices.

DATABASE: {database}
SCHEMA:
{schema}

QUERY TO VALIDATE:
```sql
{query}
```

Check for these common issues:

1. NULL HANDLING:
   - NOT IN with columns that may contain NULL (returns unexpected results)
   - Comparisons with NULL using = instead of IS NULL
   - OUTER JOIN with conditions that filter NULLs

2. UNION MISUSE:
   - Using UNION when UNION ALL is appropriate (performance)
   - UNION ALL when duplicates should be removed

3. RANGE ISSUES:
   - BETWEEN for exclusive ranges (BETWEEN is inclusive)
   - Date range issues with time components

4. DATA TYPES:
   - Comparing incompatible types
   - Implicit type conversions that may fail
   - String/number comparison issues

5. IDENTIFIER QUOTING:
   - Reserved keywords used without quotes
   - Special characters in identifiers
   - Case sensitivity issues

6. FUNCTION USAGE:
   - Wrong number of arguments
   - Incorrect function for database dialect
   - Aggregate function misuse in WHERE

7. JOIN ISSUES:
   - Cartesian products (missing JOIN conditions)
   - Wrong columns in JOIN conditions
   - JOIN type misuse (INNER vs OUTER)

8. INJECTION RISKS:
   - String concatenation vulnerabilities
   - Unparameterized inputs
   - Dynamic SQL construction issues

9. PERFORMANCE:
   - SELECT * in production code
   - Missing index opportunities
   - Full table scans that could be avoided
   - Function calls on indexed columns (breaks index)

10. BEST PRACTICES:
    - Missing LIMIT on potentially large results
    - ORDER BY without proper index
    - Subqueries that could be JOINs

Return your analysis as a JSON object with this structure:
{{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "errors": [
        {{
            "severity": "error",
            "category": "null_handling" | "union_misuse" | "data_type_mismatch" | "injection_risk" | "performance" | "syntax" | "join_issues" | "function_usage" | "quoting" | "range_issues",
            "message": "Description of the issue",
            "suggestion": "How to fix it"
        }}
    ],
    "warnings": [
        {{
            "severity": "warning",
            "category": "performance",
            "message": "Description",
            "suggestion": "Improvement suggestion"
        }}
    ],
    "info": [],
    "suggested_fix": "Corrected SQL query (only if errors found)",
    "analysis": "Brief explanation of key findings"
}}

If the query is perfect, return valid=true with confidence=1.0 and empty error arrays.
If you find issues, provide specific, actionable suggestions.
"""

    try:
        # Use LLM to validate
        response = await llm_client.generate_with_schema(
            prompt=validation_prompt,
            schema=SQLValidationResult,
            temperature=0.1,  # Low temperature for consistent validation
        )

        logger.info(
            f"[Advanced Validation] Valid: {response.valid}, "
            f"Errors: {len(response.errors)}, "
            f"Warnings: {len(response.warnings)}"
        )

        return response

    except Exception as e:
        logger.error(f"Advanced validation failed: {e}")
        # Return a safe default
        return SQLValidationResult(
            valid=True,  # Don't block execution on validation failure
            confidence=0.5,
            errors=[],
            warnings=[
                SQLValidationIssue(
                    severity="warning",
                    category="validation",
                    message=f"Advanced validation unavailable: {str(e)}",
                    suggestion="Proceeding with basic validation only",
                )
            ],
            analysis="Advanced validation failed, using basic validation only",
        )


# ============================================
# Node: Execute Query
# ============================================


async def execute_query_node(
    state: WorkflowState,
    mindsdb_service: MindsDBService,
) -> Dict[str, Any]:
    """
    Node: Execute SQL query via MindsDB.

    Args:
        state: Current workflow state
        mindsdb_service: MindsDB service instance

    Returns:
        State updates
    """
    logger.info("[Node: execute_query] Executing SQL...")

    try:
        result = await execute_sql_query(
            database=state["database"],
            query=state["generated_sql"] or "",
            mindsdb_service=mindsdb_service,
            limit=state["options"].get("limit_rows", 1000),
        )

        return {
            "query_success": result.success,
            "query_data": result.data,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
            "query_error": result.error,
            "workflow_status": "executing" if result.success else "failed",
        }

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {
            "query_success": False,
            "query_error": str(e),
            "workflow_status": "failed",
        }


# ============================================
# Node: Analyze Results
# ============================================


async def analyze_results_node(
    state: WorkflowState,
) -> Dict[str, Any]:
    """
    Node: Analyze query results.

    Args:
        state: Current workflow state

    Returns:
        State updates
    """
    logger.info("[Node: analyze_results] Analyzing data...")

    try:
        if not state["query_data"]:
            return {
                "workflow_status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
            }

        analysis = await analyze_data(
            data=state["query_data"],
            analysis_type="descriptive",
            include_processed_data=False,
        )

        return {
            "analysis_results": analysis.model_dump(),
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "workflow_status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {
            "errors": [f"Analysis failed: {str(e)}"],
            "workflow_status": "completed",  # Still complete, just without analysis
            "completed_at": datetime.utcnow().isoformat(),
        }


# ============================================
# Conditional Edge Functions
# ============================================


def route_by_intent(state: WorkflowState) -> str:
    """
    Route workflow based on query intent.

    This is called after identify_intent_node to decide whether
    to proceed with data analysis or handle as non-analysis query.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "explore_schema" or "handle_non_analysis"
    """
    intent = state.get("query_intent", "DATA_ANALYSIS")

    if intent == "DATA_ANALYSIS":
        logger.info("Routing to data analysis workflow")
        return "explore_schema"
    else:
        logger.info(f"Routing to non-analysis handler (intent: {intent})")
        return "handle_non_analysis"


def should_request_human_review(state: WorkflowState) -> str:
    """
    Determine if human review is needed.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "human_review" or "validate_sql"
    """
    if state.get("needs_human_review", False):
        return "human_review"
    return "validate_sql"


def should_proceed_after_validation(state: WorkflowState) -> str:
    """
    Determine if we should proceed after validation.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "execute_query" or "end"
    """
    if not state.get("sql_valid", False):
        # Could add HITL checkpoint here for validation errors
        logger.warning("SQL validation failed, but proceeding to execution")

    return "execute_query"


def should_analyze_results(state: WorkflowState) -> str:
    """
    Determine if we should analyze results.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "analyze_results" or "end"
    """
    if state.get("query_success", False) and state.get("query_data"):
        return "analyze_results"
    return "end"


def should_do_enhanced_analysis(state: WorkflowState) -> str:
    """
    Determine whether to run enhanced analysis.

    Enhanced analysis runs if:
    - Query succeeded
    - We have data
    - Basic analysis completed

    Args:
        state: Current workflow state

    Returns:
        Next node name: "enhanced_analysis" or "end"
    """
    if not state.get("query_success", False):
        return "end"

    if not state.get("query_data") or len(state["query_data"]) == 0:
        return "end"

    if not state.get("analysis_results"):
        return "end"

    # Run enhanced analysis
    return "enhanced_analysis"


# ============================================
# Node: Enhanced Analysis (PR#5)
# ============================================


async def enhanced_analysis_node(
    state: WorkflowState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Node: Perform enhanced analysis based on user query.

    Uses LLM to decide which additional tools to run
    (correlation, filtering, aggregation, etc.)

    Args:
        state: Current workflow state
        llm_client: LLM client for decision making

    Returns:
        State updates with enhanced_analysis results
    """
    from app.tools.statistical_tools import correlation_analysis, trend_analysis

    logger.info("Enhanced analysis node: Determining additional analysis needed")

    try:
        data = state.get("query_data")
        user_query = state.get("query")

        if not data or len(data) == 0:
            logger.info("No data available for enhanced analysis")
            return {"enhanced_analysis": None}

        # Ask LLM which additional analysis would be helpful
        decision_prompt = f"""You are analyzing the results of a SQL query.

User's original question: "{user_query}"

We have {len(data)} rows of data with these columns: {list(data[0].keys())}

The basic descriptive statistics have already been computed.

What ADDITIONAL analysis would help answer the user's question better?

Available tools:
- correlation_analysis: Find relationships between numeric columns (use when user asks about correlation, relationships, or dependencies)
- trend_analysis: Detect trends in time series data (use when user asks about growth, decline, trends, changes over time)

Think about:
1. Did the user ask about relationships or correlations?
2. Did the user ask about trends, growth, or changes over time?
3. Are there numeric columns that might be related?
4. Is there temporal or sequential data?
5. Would understanding trends or correlations provide valuable insights?

Respond with JSON only:
{{
    "tools_to_run": ["correlation_analysis"],  // List of tools, or empty array if none needed
    "reasoning": "Brief explanation of why these tools are useful"
}}

Examples:
- User asks "Is there correlation between X and Y?" -> {{"tools_to_run": ["correlation_analysis"], "reasoning": "User explicitly asked about correlation"}}
- User asks "Are sales growing over time?" -> {{"tools_to_run": ["trend_analysis"], "reasoning": "User asked about growth trend"}}
- User asks "Show revenue trends and how they relate to marketing spend" -> {{"tools_to_run": ["trend_analysis", "correlation_analysis"], "reasoning": "User wants both trend and correlation analysis"}}
- User asks "Show me all users" -> {{"tools_to_run": [], "reasoning": "Simple data retrieval, no additional analysis needed"}}
"""

        # Get LLM decision
        llm_response = await llm_client.chat_completion_with_system(
            system_message="You are a data analysis assistant helping decide which analysis tools to use.",
            user_message=decision_prompt,
            trace_name="enhanced_analysis_decision",
            metadata={
                "user_query": user_query,
                "row_count": len(data),
            },
        )

        # Parse LLM response
        import json
        import re

        # Extract JSON from response
        response_text = llm_response.content
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if not json_match:
            logger.warning("Could not parse LLM decision for enhanced analysis")
            return {"enhanced_analysis": None}

        decision = json.loads(json_match.group(0))
        tools_to_run = decision.get("tools_to_run", [])
        reasoning = decision.get("reasoning", "")

        logger.info(f"LLM decided to run tools: {tools_to_run}. Reasoning: {reasoning}")

        # If no tools to run, return early
        if not tools_to_run:
            logger.info("No enhanced analysis tools needed")
            return {"enhanced_analysis": None}

        # Run selected tools
        enhanced_results = {
            "tools_used": tools_to_run,
            "reasoning": reasoning,
            "results": {},
        }

        insights = []

        for tool_name in tools_to_run:
            if tool_name == "correlation_analysis":
                try:
                    logger.info("Running correlation_analysis")
                    corr_result = await correlation_analysis(data)

                    enhanced_results["results"]["correlation_analysis"] = {
                        "correlation_matrix": corr_result.correlation_matrix,
                        "significant_correlations": corr_result.significant_correlations,
                        "method": corr_result.method,
                        "columns_analyzed": corr_result.columns_analyzed,
                        "sample_size": corr_result.sample_size,
                    }

                    # Add insights about significant correlations
                    for sig_corr in corr_result.significant_correlations:
                        col1 = sig_corr["column1"]
                        col2 = sig_corr["column2"]
                        corr_val = sig_corr["correlation"]
                        strength = sig_corr["strength"]
                        direction = sig_corr["direction"]

                        insights.append(
                            f"Found {strength} {direction} correlation ({corr_val:.2f}) "
                            f"between {col1} and {col2}"
                        )

                    logger.info(
                        f"Correlation analysis completed: "
                        f"{len(corr_result.significant_correlations)} significant correlations found"
                    )

                except Exception as e:
                    logger.error(f"Correlation analysis failed: {e}")
                    enhanced_results["results"]["correlation_analysis"] = {
                        "error": str(e)
                    }

            elif tool_name == "trend_analysis":
                try:
                    logger.info("Running trend_analysis")
                    trend_result = await trend_analysis(data)

                    enhanced_results["results"]["trend_analysis"] = {
                        "trend_direction": trend_result.trend_direction,
                        "trend_strength": trend_result.trend_strength,
                        "confidence": trend_result.confidence,
                        "slope": trend_result.slope,
                        "r_squared": trend_result.r_squared,
                        "time_column": trend_result.time_column,
                        "value_column": trend_result.value_column,
                        "sample_size": trend_result.sample_size,
                    }

                    # Add insights from trend analysis
                    insights.extend(trend_result.insights)

                    logger.info(
                        f"Trend analysis completed: {trend_result.trend_direction} trend "
                        f"(strength: {trend_result.trend_strength:.2f})"
                    )

                except Exception as e:
                    logger.error(f"Trend analysis failed: {e}")
                    enhanced_results["results"]["trend_analysis"] = {
                        "error": str(e)
                    }

            # Add more tools here as we implement them
            # elif tool_name == "outlier_detection":
            #     ...
            # elif tool_name == "filter_data":
            #     ...
            # elif tool_name == "aggregate_data":
            #     ...

        return {
            "enhanced_analysis": enhanced_results,
            "insights": insights,
        }

    except Exception as e:
        logger.error(f"Enhanced analysis node failed: {e}")
        return {
            "enhanced_analysis": None,
            "errors": [f"Enhanced analysis failed: {str(e)}"],
        }
