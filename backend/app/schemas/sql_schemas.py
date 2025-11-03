"""
Pydantic Schemas for SQL Validation

Models for SQL query validation results and error detection.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SQLValidationIssue(BaseModel):
    """A specific SQL validation issue."""

    severity: str = Field(..., description="Severity: error, warning, or info")
    category: str = Field(..., description="Issue category (e.g., 'null_handling', 'performance')")
    message: str = Field(..., description="Human-readable issue description")
    line: Optional[int] = Field(None, description="Line number in SQL (if applicable)")
    suggestion: Optional[str] = Field(None, description="Suggested fix")

    class Config:
        json_schema_extra = {
            "example": {
                "severity": "error",
                "category": "null_handling",
                "message": "NOT IN with potential NULL values will return unexpected results",
                "line": 5,
                "suggestion": "Use NOT EXISTS or filter out NULLs explicitly",
            }
        }


class SQLValidationResult(BaseModel):
    """Result of SQL query validation."""

    valid: bool = Field(..., description="Whether the SQL is valid and safe to execute")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in validation (0-1)",
    )

    # Issues found
    errors: List[SQLValidationIssue] = Field(
        default_factory=list,
        description="Critical errors that prevent execution",
    )
    warnings: List[SQLValidationIssue] = Field(
        default_factory=list,
        description="Potential issues that may cause problems",
    )
    info: List[SQLValidationIssue] = Field(
        default_factory=list,
        description="Informational suggestions for improvement",
    )

    # Auto-fix capability
    suggested_fix: Optional[str] = Field(
        None,
        description="Corrected SQL if auto-fix is possible",
    )
    fix_applied: bool = Field(
        default=False,
        description="Whether auto-fix was applied",
    )

    # Analysis details
    analysis: Optional[str] = Field(
        None,
        description="Detailed analysis explanation",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valid": False,
                "confidence": 0.95,
                "errors": [
                    {
                        "severity": "error",
                        "category": "null_handling",
                        "message": "NOT IN clause may produce unexpected results with NULL values",
                        "suggestion": "Use NOT EXISTS instead",
                    }
                ],
                "warnings": [
                    {
                        "severity": "warning",
                        "category": "performance",
                        "message": "Full table scan detected - consider adding index",
                        "suggestion": "Add index on customer_id column",
                    }
                ],
                "suggested_fix": "SELECT * FROM orders WHERE NOT EXISTS (SELECT 1 FROM excluded WHERE excluded.id = orders.id)",
            }
        }


class SQLErrorCategory:
    """Common SQL error categories for validation."""

    NULL_HANDLING = "null_handling"
    UNION_MISUSE = "union_misuse"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    INJECTION_RISK = "injection_risk"
    PERFORMANCE = "performance"
    SYNTAX = "syntax"
    JOIN_ISSUES = "join_issues"
    FUNCTION_USAGE = "function_usage"
    QUOTING = "quoting"
    RANGE_ISSUES = "range_issues"
