"""
Statistical Analysis Tools

This module provides statistical analysis tools:
1. correlation_analysis - Compute correlation matrix between columns
"""

import logging
from typing import Any, Dict, List, Optional, Literal
import statistics

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================
# Result Models
# ============================================


class CorrelationResult(BaseModel):
    """Result from correlation analysis."""

    correlation_matrix: Dict[str, Dict[str, float]]
    method: str
    columns_analyzed: List[str]
    sample_size: int
    significant_correlations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================
# Tool: correlation_analysis
# ============================================


async def correlation_analysis(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    method: Literal["pearson", "spearman"] = "pearson",
    significance_threshold: float = 0.5,
) -> CorrelationResult:
    """
    Compute correlation matrix between numeric columns.

    Useful for understanding relationships between variables.
    Example: "Is there a correlation between price and sales?"

    Args:
        data: Query results as list of dictionaries
        columns: Columns to analyze (None = all numeric columns)
        method: Correlation method ('pearson' for linear, 'spearman' for rank)
        significance_threshold: Threshold for highlighting significant correlations

    Returns:
        CorrelationResult with correlation matrix and significant relationships

    Raises:
        Exception: If correlation computation fails
    """
    logger.info(f"Computing {method} correlation for {len(data)} rows")

    try:
        if not data:
            return CorrelationResult(
                correlation_matrix={},
                method=method,
                columns_analyzed=[],
                sample_size=0,
                warnings=["No data provided"],
            )

        # Identify numeric columns
        if columns is None:
            # Auto-detect numeric columns
            all_columns = list(data[0].keys())
            columns = []
            for col in all_columns:
                values = [row.get(col) for row in data]
                non_null_values = [v for v in values if v is not None]
                if non_null_values and _infer_data_type(non_null_values) == "numeric":
                    columns.append(col)

        if len(columns) < 2:
            return CorrelationResult(
                correlation_matrix={},
                method=method,
                columns_analyzed=columns,
                sample_size=len(data),
                warnings=["Need at least 2 numeric columns for correlation analysis"],
            )

        # Extract numeric values for each column
        column_data = {}
        for col in columns:
            values = [_to_numeric(row.get(col)) for row in data]
            # Remove None values
            values = [v for v in values if v is not None]
            if len(values) < 3:
                logger.warning(f"Column {col} has too few numeric values, skipping")
                continue
            column_data[col] = values

        if len(column_data) < 2:
            return CorrelationResult(
                correlation_matrix={},
                method=method,
                columns_analyzed=list(column_data.keys()),
                sample_size=len(data),
                warnings=["Not enough columns with sufficient numeric data"],
            )

        # Compute correlation matrix
        correlation_matrix = {}
        warnings = []

        for col1 in column_data:
            correlation_matrix[col1] = {}
            for col2 in column_data:
                if col1 == col2:
                    correlation_matrix[col1][col2] = 1.0
                else:
                    # Compute correlation
                    corr = _compute_correlation(
                        column_data[col1],
                        column_data[col2],
                        method
                    )
                    correlation_matrix[col1][col2] = round(corr, 4)

        # Identify significant correlations (excluding self-correlation)
        significant_correlations = []
        for col1 in correlation_matrix:
            for col2 in correlation_matrix[col1]:
                if col1 < col2:  # Avoid duplicates (only upper triangle)
                    corr = correlation_matrix[col1][col2]
                    if abs(corr) >= significance_threshold:
                        significant_correlations.append({
                            "column1": col1,
                            "column2": col2,
                            "correlation": corr,
                            "strength": _interpret_correlation(abs(corr)),
                            "direction": "positive" if corr > 0 else "negative",
                        })

        # Sort by absolute correlation value
        significant_correlations.sort(
            key=lambda x: abs(x["correlation"]),
            reverse=True
        )

        result = CorrelationResult(
            correlation_matrix=correlation_matrix,
            method=method,
            columns_analyzed=list(column_data.keys()),
            sample_size=len(data),
            significant_correlations=significant_correlations,
            warnings=warnings,
        )

        logger.info(
            f"Correlation analysis completed: {len(column_data)} columns, "
            f"{len(significant_correlations)} significant correlations found"
        )

        return result

    except Exception as e:
        logger.error(f"Correlation analysis failed: {e}")
        raise


# ============================================
# Helper Functions
# ============================================


def _infer_data_type(values: List[Any]) -> str:
    """
    Infer data type from sample values.

    Args:
        values: List of non-null values

    Returns:
        Data type string: 'numeric', 'categorical', 'temporal', 'unknown'
    """
    if not values:
        return "unknown"

    # Sample first few values
    sample = values[:100]

    # Check numeric
    numeric_count = sum(1 for v in sample if _is_numeric(v))
    if numeric_count / len(sample) > 0.8:
        return "numeric"

    # Default to categorical
    return "categorical"


def _is_numeric(value: Any) -> bool:
    """Check if value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _to_numeric(value: Any) -> Optional[float]:
    """Convert value to numeric."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _compute_correlation(
    values1: List[float],
    values2: List[float],
    method: str
) -> float:
    """
    Compute correlation between two numeric arrays.

    Args:
        values1: First array of values
        values2: Second array of values
        method: Correlation method ('pearson' or 'spearman')

    Returns:
        Correlation coefficient (-1 to 1)
    """
    # Ensure equal length (pair-wise complete observations)
    min_len = min(len(values1), len(values2))
    values1 = values1[:min_len]
    values2 = values2[:min_len]

    if len(values1) < 3:
        return 0.0

    if method == "spearman":
        # Convert to ranks
        values1 = _rank_values(values1)
        values2 = _rank_values(values2)

    # Pearson correlation
    try:
        mean1 = statistics.mean(values1)
        mean2 = statistics.mean(values2)

        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))

        std1 = statistics.stdev(values1) if len(values1) > 1 else 0
        std2 = statistics.stdev(values2) if len(values2) > 1 else 0

        if std1 == 0 or std2 == 0:
            return 0.0

        denominator = len(values1) * std1 * std2

        return numerator / denominator if denominator != 0 else 0.0

    except Exception as e:
        logger.warning(f"Correlation computation error: {e}")
        return 0.0


def _rank_values(values: List[float]) -> List[float]:
    """
    Convert values to ranks (for Spearman correlation).

    Args:
        values: List of numeric values

    Returns:
        List of ranks (1-indexed)
    """
    # Sort values with original indices
    indexed_values = [(v, i) for i, v in enumerate(values)]
    indexed_values.sort(key=lambda x: x[0])

    # Assign ranks
    ranks = [0.0] * len(values)
    for rank, (value, original_index) in enumerate(indexed_values, start=1):
        ranks[original_index] = float(rank)

    return ranks


def _interpret_correlation(abs_corr: float) -> str:
    """
    Interpret correlation strength.

    Args:
        abs_corr: Absolute correlation value

    Returns:
        Interpretation string
    """
    if abs_corr >= 0.9:
        return "very strong"
    elif abs_corr >= 0.7:
        return "strong"
    elif abs_corr >= 0.5:
        return "moderate"
    elif abs_corr >= 0.3:
        return "weak"
    else:
        return "very weak"
