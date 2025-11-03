"""
SQL Tools for Analysis Agent

This module provides SQL-related tools:
1. explore_schema - Discover database schema
2. generate_sql - Generate SQL from natural language
3. execute_sql_query - Execute SQL via MindsDB
4. validate_query - Validate SQL safety and correctness
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
import time

from pydantic import BaseModel, Field

from app.core.llm import LLMClient
from app.core.prompts import PromptType, get_prompt
from app.services.mindsdb_service import MindsDBService, QueryResult

logger = logging.getLogger(__name__)


# ============================================
# Tool Result Models
# ============================================


class SchemaInfo(BaseModel):
    """Schema information result."""

    database: str
    tables: Dict[str, Any]
    table_count: int
    retrieved_at: float


class SQLGenerationResult(BaseModel):
    """Result from SQL generation."""

    sql: str
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    tables_used: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    needs_human_review: bool = False


class QueryExecutionResult(BaseModel):
    """Result from query execution."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time_ms: int = 0
    error: Optional[str] = None


class ValidationResult(BaseModel):
    """Result from query validation."""

    valid: bool
    safety_level: str  # safe, warning, dangerous
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    dangerous_operations: List[str] = Field(default_factory=list)


# ============================================
# Tool 1: explore_schema
# ============================================


async def explore_schema(
    database: str,
    mindsdb_service: MindsDBService,
    table: Optional[str] = None,
    use_cache: bool = True,
) -> SchemaInfo:
    """
    Explore database schema to discover available tables and columns.

    This tool provides the agent with information about what data is available.

    Args:
        database: Database name to explore
        mindsdb_service: MindsDB service instance
        table: Optional specific table to explore
        use_cache: Whether to use cached schema (default: True)

    Returns:
        SchemaInfo with database structure

    Raises:
        Exception: If schema retrieval fails
    """
    logger.info(f"Exploring schema for database '{database}'" + (f", table '{table}'" if table else ""))

    try:
        start_time = time.time()

        # Get schema from MindsDB
        schema = await mindsdb_service.get_schema(database, table)

        retrieval_time = time.time() - start_time
        table_count = len(schema.get("tables", {}))

        result = SchemaInfo(
            database=database,
            tables=schema.get("tables", {}),
            table_count=table_count,
            retrieved_at=retrieval_time,
        )

        logger.info(
            f"Schema exploration completed: {table_count} tables in {retrieval_time:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(f"Schema exploration failed: {e}")
        raise


# ============================================
# Tool 2: generate_sql
# ============================================


async def generate_sql(
    query: str,
    schema: Dict[str, Any],
    llm_client: LLMClient,
    context: Optional[Dict[str, Any]] = None,
    confidence_threshold: float = 0.8,
) -> SQLGenerationResult:
    """
    Generate SQL query from natural language using LLM.

    This is the core tool for translating user intent into executable SQL.

    Args:
        query: Natural language query
        schema: Database schema from explore_schema
        llm_client: LLM client instance
        context: Optional context (previous queries, preferences)
        confidence_threshold: Threshold for auto-approval (default: 0.8)

    Returns:
        SQLGenerationResult with generated SQL and metadata

    Raises:
        Exception: If SQL generation fails
    """
    logger.info(f"Generating SQL for query: '{query[:100]}...'")

    try:
        # Get prompt template
        prompt_template = get_prompt(PromptType.SQL_GENERATION)

        # Format schema for prompt
        schema_str = _format_schema_for_prompt(schema)

        # Format context if provided
        context_str = ""
        if context:
            context_str = json.dumps(context, indent=2)

        # Render prompt
        rendered_prompt = prompt_template.render(
            schema=schema_str,
            query=query,
            context=context_str,
        )

        # Call LLM
        llm_response = await llm_client.chat_completion_with_system(
            system_message="You are an expert SQL query generator.",
            user_message=rendered_prompt,
            trace_name="sql_generation",
            metadata={"query": query, "database": schema.get("database")},
        )

        # Parse response (expect JSON)
        try:
            response_json = _extract_json_from_response(llm_response.content)

            result = SQLGenerationResult(
                sql=response_json.get("sql", ""),
                intent=response_json.get("intent", "unknown"),
                confidence=float(response_json.get("confidence", 0.5)),
                explanation=response_json.get("explanation", ""),
                tables_used=response_json.get("tables_used", []),
                warnings=response_json.get("warnings", []),
                needs_human_review=response_json.get("needs_review", False),
            )

            # Auto-set needs_review based on confidence
            if result.confidence < confidence_threshold:
                result.needs_human_review = True

            # Check for dangerous operations
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "TRUNCATE", "ALTER"]
            sql_upper = result.sql.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    result.needs_human_review = True
                    result.warnings.append(f"Contains {keyword} operation - requires review")

            logger.info(
                f"SQL generated successfully: confidence={result.confidence:.2f}, "
                f"needs_review={result.needs_human_review}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return fallback result
            return SQLGenerationResult(
                sql="",
                intent="unknown",
                confidence=0.0,
                explanation=f"Failed to parse LLM response: {e}",
                needs_human_review=True,
                warnings=["LLM response parsing failed"],
            )

    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        raise


# ============================================
# Tool 3: execute_sql_query
# ============================================


async def execute_sql_query(
    database: str,
    query: str,
    mindsdb_service: MindsDBService,
    limit: Optional[int] = None,
) -> QueryExecutionResult:
    """
    Execute SQL query via MindsDB.

    Args:
        database: Database name
        query: SQL query to execute
        mindsdb_service: MindsDB service instance
        limit: Optional row limit

    Returns:
        QueryExecutionResult with data and metadata

    Raises:
        Exception: If execution fails critically
    """
    logger.info(f"Executing SQL query on database '{database}'")

    try:
        # Execute via MindsDB
        result = await mindsdb_service.execute_query(
            query=query,
            database=database,
            limit=limit,
        )

        # Convert to our result format
        execution_result = QueryExecutionResult(
            success=result.success,
            data=result.data,
            row_count=result.row_count,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
        )

        if execution_result.success:
            logger.info(
                f"Query executed successfully: {execution_result.row_count} rows in "
                f"{execution_result.execution_time_ms}ms"
            )
        else:
            logger.error(f"Query execution failed: {execution_result.error}")

        return execution_result

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return QueryExecutionResult(
            success=False,
            error=f"Execution error: {str(e)}",
        )


# ============================================
# Tool 4: validate_query
# ============================================


async def validate_query(
    query: str,
    llm_client: Optional[LLMClient] = None,
    schema: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """
    Validate SQL query for safety and correctness.

    Performs both rule-based and LLM-based validation.

    Args:
        query: SQL query to validate
        llm_client: Optional LLM client for advanced validation
        schema: Optional schema for reference validation

    Returns:
        ValidationResult with validation details
    """
    logger.info("Validating SQL query")

    result = ValidationResult(
        valid=True,
        safety_level="safe",
    )

    try:
        # Rule-based validation
        query_upper = query.upper().strip()

        # Check for dangerous operations
        dangerous_ops = {
            "DROP": "DROP operation detected - destructive",
            "TRUNCATE": "TRUNCATE operation detected - destructive",
            "DELETE": "DELETE operation detected",
            "UPDATE": "UPDATE operation detected",
            "ALTER": "ALTER operation detected - schema change",
        }

        for op, message in dangerous_ops.items():
            if op in query_upper:
                result.dangerous_operations.append(message)
                result.safety_level = "dangerous"
                result.warnings.append(message)

        # Check for DELETE/UPDATE without WHERE
        if "DELETE" in query_upper and "WHERE" not in query_upper:
            result.errors.append("DELETE without WHERE clause - would delete all rows")
            result.valid = False
            result.safety_level = "dangerous"

        if "UPDATE" in query_upper and "WHERE" not in query_upper:
            result.warnings.append("UPDATE without WHERE clause - would update all rows")
            result.safety_level = "warning"

        # Check for SELECT *
        if re.search(r"SELECT\s+\*", query_upper):
            result.warnings.append("SELECT * detected - consider specifying columns")

        # Check for LIMIT clause on SELECT
        if "SELECT" in query_upper and "LIMIT" not in query_upper:
            result.warnings.append("No LIMIT clause - query may return large dataset")
            result.suggestions.append("Consider adding LIMIT clause for performance")

        # Check for SQL injection patterns
        injection_patterns = [
            r";\s*(DROP|DELETE|UPDATE|INSERT)",
            r"--",
            r"/\*.*\*/",
            r"UNION\s+SELECT",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, query_upper):
                result.errors.append(f"Potential SQL injection pattern detected: {pattern}")
                result.valid = False
                result.safety_level = "dangerous"

        # Basic syntax checks
        if not query.strip():
            result.errors.append("Empty query")
            result.valid = False

        # Check balanced parentheses
        if query.count("(") != query.count(")"):
            result.errors.append("Unbalanced parentheses")
            result.valid = False

        # LLM-based validation (if available)
        if llm_client and result.valid:
            try:
                llm_validation = await _llm_validate_query(query, llm_client, schema)
                # Merge LLM validation results
                result.warnings.extend(llm_validation.get("warnings", []))
                result.suggestions.extend(llm_validation.get("suggestions", []))
            except Exception as e:
                logger.warning(f"LLM validation failed: {e}")

        # Final safety level determination
        if result.errors:
            result.valid = False
            result.safety_level = "dangerous"
        elif len(result.dangerous_operations) > 0:
            result.safety_level = "dangerous"
        elif len(result.warnings) > 0:
            result.safety_level = "warning"

        logger.info(
            f"Validation completed: valid={result.valid}, safety={result.safety_level}"
        )

        return result

    except Exception as e:
        logger.error(f"Query validation error: {e}")
        return ValidationResult(
            valid=False,
            safety_level="dangerous",
            errors=[f"Validation error: {str(e)}"],
        )


# ============================================
# Helper Functions
# ============================================


def _format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Format schema information for LLM prompt.

    Args:
        schema: Schema dictionary

    Returns:
        Formatted schema string
    """
    lines = []
    tables = schema.get("tables", {})

    lines.append(f"Database: {schema.get('database', 'unknown')}")
    lines.append(f"\nAvailable Tables ({len(tables)}):")

    for table_name, table_info in tables.items():
        lines.append(f"\n  Table: {table_name}")

        if "columns" in table_info and table_info["columns"]:
            lines.append("  Columns:")
            for col in table_info["columns"]:
                if isinstance(col, dict):
                    col_name = col.get("Field", col.get("name", "unknown"))
                    col_type = col.get("Type", col.get("type", "unknown"))
                    lines.append(f"    - {col_name} ({col_type})")
                else:
                    lines.append(f"    - {col}")

    return "\n".join(lines)


def _extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response.

    Handles cases where LLM wraps JSON in markdown code blocks.

    Args:
        response: LLM response text

    Returns:
        Parsed JSON dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object in response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response

    return json.loads(json_str)


async def _llm_validate_query(
    query: str,
    llm_client: LLMClient,
    schema: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Use LLM to validate query for additional insights.

    Args:
        query: SQL query
        llm_client: LLM client
        schema: Optional schema

    Returns:
        Validation insights dictionary
    """
    try:
        prompt_template = get_prompt(PromptType.QUERY_VALIDATION)

        schema_str = ""
        if schema:
            schema_str = _format_schema_for_prompt(schema)

        rendered_prompt = prompt_template.render(
            query=query,
            schema=schema_str,
        )

        llm_response = await llm_client.chat_completion_with_system(
            system_message="You are a SQL query validator.",
            user_message=rendered_prompt,
            trace_name="query_validation",
        )

        # Parse response
        response_json = _extract_json_from_response(llm_response.content)
        return response_json

    except Exception as e:
        logger.warning(f"LLM validation failed: {e}")
        return {}
