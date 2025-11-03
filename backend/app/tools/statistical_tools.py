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


# ============================================
# Result Models - Trend Analysis
# ============================================


class TrendResult(BaseModel):
    """Result from trend analysis."""

    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0.0-1.0 (how strong is the trend)
    confidence: float  # 0.0-1.0 (confidence in the trend)
    slope: Optional[float] = None  # Rate of change
    r_squared: Optional[float] = None  # Goodness of fit for linear regression
    time_column: Optional[str] = None  # Column used for time/sequence
    value_column: Optional[str] = None  # Column used for values
    sample_size: int
    insights: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================
# Tool: trend_analysis
# ============================================


async def trend_analysis(
    data: List[Dict[str, Any]],
    time_column: Optional[str] = None,
    value_column: Optional[str] = None,
    method: Literal["linear", "moving_average"] = "linear",
) -> TrendResult:
    """
    Detect trends in time series or sequential data.

    Useful for understanding patterns over time, growth/decline analysis.
    Example: "Is our revenue growing or declining over time?"

    Args:
        data: Query results as list of dictionaries
        time_column: Column to use for time/sequence (None = auto-detect)
        value_column: Column to use for values (None = auto-detect first numeric)
        method: Trend detection method ('linear' for regression, 'moving_average' for smoothing)

    Returns:
        TrendResult with trend direction, strength, and insights

    Raises:
        Exception: If trend analysis fails
    """
    logger.info(f"Computing trend analysis for {len(data)} rows using {method} method")

    try:
        if not data or len(data) < 3:
            return TrendResult(
                trend_direction="unknown",
                trend_strength=0.0,
                confidence=0.0,
                sample_size=len(data) if data else 0,
                warnings=["Need at least 3 data points for trend analysis"],
            )

        # Auto-detect time and value columns if not specified
        if time_column is None or value_column is None:
            detected_columns = _detect_time_value_columns(data)
            time_column = time_column or detected_columns["time_column"]
            value_column = value_column or detected_columns["value_column"]

        if not time_column or not value_column:
            return TrendResult(
                trend_direction="unknown",
                trend_strength=0.0,
                confidence=0.0,
                sample_size=len(data),
                warnings=["Could not detect appropriate time and value columns"],
            )

        # Extract and prepare data
        time_values = []
        numeric_values = []

        for i, row in enumerate(data):
            time_val = row.get(time_column)
            value_val = row.get(value_column)

            # Convert time to numeric (use index if datetime parsing fails)
            if time_val is not None:
                time_numeric = _to_numeric(time_val)
                if time_numeric is None:
                    time_numeric = float(i)  # Use row index as fallback
                time_values.append(time_numeric)
            else:
                time_values.append(float(i))

            # Convert value to numeric
            numeric_val = _to_numeric(value_val)
            if numeric_val is not None:
                numeric_values.append(numeric_val)

        if len(numeric_values) < 3:
            return TrendResult(
                trend_direction="unknown",
                trend_strength=0.0,
                confidence=0.0,
                time_column=time_column,
                value_column=value_column,
                sample_size=len(data),
                warnings=["Insufficient numeric data for trend analysis"],
            )

        # Align arrays (only use rows with valid numeric values)
        aligned_data = [(t, v) for t, v in zip(time_values, numeric_values)]
        time_values = [t for t, v in aligned_data]
        numeric_values = [v for t, v in aligned_data]

        # Perform trend analysis based on method
        if method == "linear":
            result = _linear_trend_analysis(time_values, numeric_values)
        else:  # moving_average
            result = _moving_average_trend_analysis(numeric_values)

        # Add metadata
        result["time_column"] = time_column
        result["value_column"] = value_column
        result["sample_size"] = len(numeric_values)

        # Generate insights
        insights = []
        direction = result["trend_direction"]
        strength = result["trend_strength"]

        if direction == "increasing":
            insights.append(
                f"{value_column} shows an {direction} trend "
                f"({'strong' if strength > 0.7 else 'moderate' if strength > 0.4 else 'weak'} pattern)"
            )
        elif direction == "decreasing":
            insights.append(
                f"{value_column} shows a {direction} trend "
                f"({'strong' if strength > 0.7 else 'moderate' if strength > 0.4 else 'weak'} pattern)"
            )
        else:
            insights.append(f"{value_column} remains relatively stable over time")

        if result.get("slope"):
            insights.append(f"Rate of change: {result['slope']:.4f} per time unit")

        result["insights"] = insights

        logger.info(
            f"Trend analysis completed: {direction} trend "
            f"(strength: {strength:.2f}, confidence: {result['confidence']:.2f})"
        )

        return TrendResult(**result)

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise


# ============================================
# Helper Functions - Trend Analysis
# ============================================


def _detect_time_value_columns(data: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Auto-detect time and value columns from data.

    Args:
        data: List of dictionaries

    Returns:
        Dict with 'time_column' and 'value_column'
    """
    if not data:
        return {"time_column": None, "value_column": None}

    columns = list(data[0].keys())

    # Look for time-related column names
    time_keywords = ["time", "date", "timestamp", "period", "year", "month", "day", "created", "updated"]
    time_column = None
    for col in columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in time_keywords):
            time_column = col
            break

    # If no time column found, use first column
    if not time_column and columns:
        time_column = columns[0]

    # Look for value column (first numeric column that's not the time column)
    value_column = None
    for col in columns:
        if col == time_column:
            continue
        # Check if column has numeric values
        values = [row.get(col) for row in data[:10]]  # Sample first 10 rows
        if values and _infer_data_type(values) == "numeric":
            value_column = col
            break

    return {"time_column": time_column, "value_column": value_column}


def _linear_trend_analysis(
    time_values: List[float],
    numeric_values: List[float]
) -> Dict[str, Any]:
    """
    Perform linear regression trend analysis.

    Args:
        time_values: Time/sequence values
        numeric_values: Numeric values to analyze

    Returns:
        Dict with trend_direction, trend_strength, confidence, slope, r_squared
    """
    n = len(time_values)

    # Calculate means
    mean_time = statistics.mean(time_values)
    mean_value = statistics.mean(numeric_values)

    # Calculate slope (β1)
    numerator = sum((t - mean_time) * (v - mean_value) for t, v in zip(time_values, numeric_values))
    denominator = sum((t - mean_time) ** 2 for t in time_values)

    slope = numerator / denominator if denominator != 0 else 0.0

    # Calculate R-squared
    predicted_values = [mean_value + slope * (t - mean_time) for t in time_values]
    ss_res = sum((v - p) ** 2 for v, p in zip(numeric_values, predicted_values))
    ss_tot = sum((v - mean_value) ** 2 for v in numeric_values)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    # Ensure R-squared is between 0 and 1
    r_squared = max(0.0, min(1.0, r_squared))

    # Determine trend direction
    if abs(slope) < 0.01:  # Very small slope
        trend_direction = "stable"
    elif slope > 0:
        trend_direction = "increasing"
    else:
        trend_direction = "decreasing"

    # Trend strength based on R-squared
    trend_strength = r_squared

    # Confidence based on sample size and R-squared
    confidence = r_squared * min(1.0, n / 30)  # Higher confidence with more data points

    return {
        "trend_direction": trend_direction,
        "trend_strength": float(trend_strength),
        "confidence": float(confidence),
        "slope": float(slope),
        "r_squared": float(r_squared),
        "warnings": [],
    }


def _moving_average_trend_analysis(
    numeric_values: List[float],
    window_size: int = 3
) -> Dict[str, Any]:
    """
    Perform moving average trend analysis.

    Args:
        numeric_values: Numeric values to analyze
        window_size: Window size for moving average

    Returns:
        Dict with trend_direction, trend_strength, confidence
    """
    if len(numeric_values) < window_size:
        return {
            "trend_direction": "unknown",
            "trend_strength": 0.0,
            "confidence": 0.0,
            "warnings": [f"Need at least {window_size} points for moving average"],
        }

    # Calculate moving averages
    moving_avgs = []
    for i in range(len(numeric_values) - window_size + 1):
        window = numeric_values[i:i + window_size]
        moving_avgs.append(statistics.mean(window))

    # Compare first and last moving average
    if len(moving_avgs) < 2:
        return {
            "trend_direction": "stable",
            "trend_strength": 0.0,
            "confidence": 0.5,
            "warnings": [],
        }

    first_avg = moving_avgs[0]
    last_avg = moving_avgs[-1]
    overall_mean = statistics.mean(numeric_values)

    # Calculate relative change
    relative_change = (last_avg - first_avg) / overall_mean if overall_mean != 0 else 0.0

    # Determine trend
    if abs(relative_change) < 0.05:  # Less than 5% change
        trend_direction = "stable"
        trend_strength = 0.0
    elif relative_change > 0:
        trend_direction = "increasing"
        trend_strength = min(1.0, abs(relative_change) * 5)  # Scale to 0-1
    else:
        trend_direction = "decreasing"
        trend_strength = min(1.0, abs(relative_change) * 5)

    # Confidence based on consistency of trend
    confidence = min(1.0, len(moving_avgs) / 10)  # Higher with more data points

    return {
        "trend_direction": trend_direction,
        "trend_strength": float(trend_strength),
        "confidence": float(confidence),
        "warnings": [],
    }
