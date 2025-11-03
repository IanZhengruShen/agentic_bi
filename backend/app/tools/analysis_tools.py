"""
Analysis Tools for Data Processing

This module provides data analysis and preprocessing tools:
1. analyze_data - Descriptive statistics and data quality analysis
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import Counter

from pydantic import BaseModel, Field
import statistics

logger = logging.getLogger(__name__)


# ============================================
# Result Models
# ============================================


class ColumnStats(BaseModel):
    """Statistics for a single column."""

    column_name: str
    data_type: str

    # For numeric columns
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None

    # For all columns
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: int = 0

    # For categorical columns
    top_values: Optional[List[Dict[str, Any]]] = None


class DataQuality(BaseModel):
    """Data quality assessment."""

    total_rows: int
    total_columns: int
    complete_rows: int
    completeness_percentage: float

    columns_with_nulls: List[str] = Field(default_factory=list)
    columns_with_high_nulls: List[str] = Field(default_factory=list)  # >50% nulls
    duplicate_row_count: int = 0

    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class DataAnalysisResult(BaseModel):
    """Comprehensive data analysis result."""

    # Summary statistics
    summary_stats: Dict[str, ColumnStats]

    # Data quality
    data_quality: DataQuality

    # Insights
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Processed data (optional)
    processed_data: Optional[List[Dict[str, Any]]] = None

    # Metadata
    analysis_type: str
    row_count: int
    column_count: int
    analysis_time_ms: int


# ============================================
# Tool: analyze_data
# ============================================


async def analyze_data(
    data: List[Dict[str, Any]],
    analysis_type: str = "descriptive",
    include_processed_data: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> DataAnalysisResult:
    """
    Perform descriptive analysis and preprocessing on query results.

    This tool provides:
    - Descriptive statistics for numeric columns
    - Frequency distributions for categorical columns
    - Data quality assessment
    - Auto-generated insights
    - Recommendations for visualization

    Args:
        data: Query results as list of dictionaries
        analysis_type: Type of analysis ('descriptive', 'quality', 'full')
        include_processed_data: Whether to include cleaned data
        options: Additional analysis options

    Returns:
        DataAnalysisResult with comprehensive analysis

    Raises:
        Exception: If analysis fails
    """
    logger.info(f"Analyzing data: {len(data)} rows, type={analysis_type}")

    import time
    start_time = time.time()

    try:
        if not data:
            return DataAnalysisResult(
                summary_stats={},
                data_quality=DataQuality(
                    total_rows=0,
                    total_columns=0,
                    complete_rows=0,
                    completeness_percentage=0.0,
                ),
                analysis_type=analysis_type,
                row_count=0,
                column_count=0,
                analysis_time_ms=0,
                insights=["No data to analyze"],
            )

        row_count = len(data)
        columns = list(data[0].keys())
        column_count = len(columns)

        # Perform analyses based on type
        summary_stats = {}
        if analysis_type in ["descriptive", "full"]:
            summary_stats = await _compute_descriptive_stats(data, columns)

        data_quality = await _assess_data_quality(data, columns)

        insights = _generate_insights(summary_stats, data_quality, data)
        recommendations = _generate_recommendations(summary_stats, data_quality, data)

        # Optionally include processed data
        processed_data = None
        if include_processed_data:
            processed_data = await _preprocess_data(data, data_quality)

        execution_time_ms = int((time.time() - start_time) * 1000)

        result = DataAnalysisResult(
            summary_stats=summary_stats,
            data_quality=data_quality,
            insights=insights,
            recommendations=recommendations,
            processed_data=processed_data,
            analysis_type=analysis_type,
            row_count=row_count,
            column_count=column_count,
            analysis_time_ms=execution_time_ms,
        )

        logger.info(f"Analysis completed in {execution_time_ms}ms")

        return result

    except Exception as e:
        logger.error(f"Data analysis failed: {e}")
        raise


# ============================================
# Helper Functions
# ============================================


async def _compute_descriptive_stats(
    data: List[Dict[str, Any]],
    columns: List[str],
) -> Dict[str, ColumnStats]:
    """
    Compute descriptive statistics for each column.

    Args:
        data: Data rows
        columns: Column names

    Returns:
        Dictionary mapping column names to ColumnStats
    """
    stats = {}

    for col in columns:
        values = [row.get(col) for row in data]
        non_null_values = [v for v in values if v is not None]

        # Determine data type
        data_type = _infer_data_type(non_null_values)

        # Calculate basic stats
        null_count = len(values) - len(non_null_values)
        null_percentage = (null_count / len(values) * 100) if len(values) > 0 else 0.0
        unique_count = len(set(str(v) for v in non_null_values))

        col_stats = ColumnStats(
            column_name=col,
            data_type=data_type,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
        )

        # Type-specific analysis
        if data_type == "numeric" and non_null_values:
            numeric_values = [_to_numeric(v) for v in non_null_values]
            numeric_values = [v for v in numeric_values if v is not None]

            if numeric_values:
                try:
                    col_stats.mean = statistics.mean(numeric_values)
                    col_stats.median = statistics.median(numeric_values)
                    col_stats.min_value = min(numeric_values)
                    col_stats.max_value = max(numeric_values)

                    if len(numeric_values) > 1:
                        col_stats.std_dev = statistics.stdev(numeric_values)
                        col_stats.q25 = statistics.quantiles(numeric_values, n=4)[0]
                        col_stats.q75 = statistics.quantiles(numeric_values, n=4)[2]
                except Exception as e:
                    logger.warning(f"Error computing numeric stats for {col}: {e}")

        elif data_type == "categorical" and non_null_values:
            # Frequency distribution
            freq = Counter(non_null_values)
            top_10 = freq.most_common(10)

            col_stats.top_values = [
                {"value": str(value), "count": count, "percentage": count / len(non_null_values) * 100}
                for value, count in top_10
            ]

        stats[col] = col_stats

    return stats


async def _assess_data_quality(
    data: List[Dict[str, Any]],
    columns: List[str],
) -> DataQuality:
    """
    Assess data quality issues.

    Args:
        data: Data rows
        columns: Column names

    Returns:
        DataQuality assessment
    """
    total_rows = len(data)
    total_columns = len(columns)

    # Count complete rows (no nulls)
    complete_rows = sum(
        1 for row in data
        if all(row.get(col) is not None for col in columns)
    )

    completeness_percentage = (complete_rows / total_rows * 100) if total_rows > 0 else 0.0

    # Identify columns with nulls
    columns_with_nulls = []
    columns_with_high_nulls = []

    for col in columns:
        null_count = sum(1 for row in data if row.get(col) is None)
        null_percentage = (null_count / total_rows * 100) if total_rows > 0 else 0.0

        if null_count > 0:
            columns_with_nulls.append(col)

        if null_percentage > 50:
            columns_with_high_nulls.append(col)

    # Detect duplicate rows
    unique_rows = set(
        tuple(sorted(row.items())) for row in data
    )
    duplicate_row_count = total_rows - len(unique_rows)

    # Generate issues and warnings
    issues = []
    warnings = []

    if completeness_percentage < 50:
        issues.append(f"Low data completeness: {completeness_percentage:.1f}%")

    if columns_with_high_nulls:
        warnings.append(f"Columns with >50% nulls: {', '.join(columns_with_high_nulls)}")

    if duplicate_row_count > 0:
        warnings.append(f"Found {duplicate_row_count} duplicate rows")

    if total_rows < 10:
        warnings.append("Very small dataset - statistics may not be meaningful")

    return DataQuality(
        total_rows=total_rows,
        total_columns=total_columns,
        complete_rows=complete_rows,
        completeness_percentage=completeness_percentage,
        columns_with_nulls=columns_with_nulls,
        columns_with_high_nulls=columns_with_high_nulls,
        duplicate_row_count=duplicate_row_count,
        issues=issues,
        warnings=warnings,
    )


def _generate_insights(
    stats: Dict[str, ColumnStats],
    quality: DataQuality,
    data: List[Dict[str, Any]],
) -> List[str]:
    """
    Generate automatic insights from data analysis.

    Args:
        stats: Column statistics
        quality: Data quality assessment
        data: Raw data

    Returns:
        List of insight strings
    """
    insights = []

    # Data size insight
    if quality.total_rows > 1000:
        insights.append(f"Large dataset with {quality.total_rows:,} rows")
    elif quality.total_rows < 100:
        insights.append(f"Small dataset with only {quality.total_rows} rows")

    # Completeness insight
    if quality.completeness_percentage > 90:
        insights.append(f"High data quality: {quality.completeness_percentage:.1f}% complete rows")
    elif quality.completeness_percentage < 50:
        insights.append(f"Data quality concern: only {quality.completeness_percentage:.1f}% complete rows")

    # Column-specific insights
    for col_name, col_stats in stats.items():
        if col_stats.data_type == "numeric":
            if col_stats.mean is not None and col_stats.std_dev is not None:
                cv = (col_stats.std_dev / col_stats.mean * 100) if col_stats.mean != 0 else 0
                if cv > 100:
                    insights.append(f"High variability in '{col_name}' (CV: {cv:.1f}%)")

        elif col_stats.data_type == "categorical":
            if col_stats.top_values and len(col_stats.top_values) > 0:
                top_value = col_stats.top_values[0]
                if top_value["percentage"] > 80:
                    insights.append(
                        f"'{col_name}' is dominated by '{top_value['value']}' "
                        f"({top_value['percentage']:.1f}%)"
                    )

    # Duplicate insight
    if quality.duplicate_row_count > 0:
        dup_pct = (quality.duplicate_row_count / quality.total_rows * 100)
        insights.append(f"Dataset contains {dup_pct:.1f}% duplicate rows")

    return insights


def _generate_recommendations(
    stats: Dict[str, ColumnStats],
    quality: DataQuality,
    data: List[Dict[str, Any]],
) -> List[str]:
    """
    Generate recommendations based on analysis.

    Args:
        stats: Column statistics
        quality: Data quality assessment
        data: Raw data

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Data quality recommendations
    if quality.columns_with_high_nulls:
        recommendations.append(
            f"Consider removing or imputing columns with high null rates: "
            f"{', '.join(quality.columns_with_high_nulls)}"
        )

    if quality.duplicate_row_count > 0:
        recommendations.append("Remove duplicate rows before visualization")

    # Visualization recommendations
    numeric_cols = [col for col, s in stats.items() if s.data_type == "numeric"]
    categorical_cols = [col for col, s in stats.items() if s.data_type == "categorical"]

    if len(numeric_cols) >= 2:
        recommendations.append(
            f"Consider scatter plot for relationship between {numeric_cols[0]} and {numeric_cols[1]}"
        )

    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        recommendations.append(
            f"Consider bar chart showing {numeric_cols[0]} by {categorical_cols[0]}"
        )

    if any(s.data_type == "temporal" for s in stats.values()):
        recommendations.append("Time-series data detected - consider line chart for trends")

    return recommendations


async def _preprocess_data(
    data: List[Dict[str, Any]],
    quality: DataQuality,
) -> List[Dict[str, Any]]:
    """
    Preprocess data based on quality assessment.

    Args:
        data: Raw data
        quality: Data quality assessment

    Returns:
        Processed data
    """
    # For now, just remove duplicates
    # More sophisticated preprocessing can be added later
    processed = []
    seen = set()

    for row in data:
        row_tuple = tuple(sorted(row.items()))
        if row_tuple not in seen:
            seen.add(row_tuple)
            processed.append(row)

    return processed


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

    # Check temporal
    temporal_count = sum(1 for v in sample if _is_temporal(v))
    if temporal_count / len(sample) > 0.8:
        return "temporal"

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


def _is_temporal(value: Any) -> bool:
    """Check if value is temporal (date/datetime)."""
    if isinstance(value, (datetime,)):
        return True

    if isinstance(value, str):
        # Try parsing common date formats
        import dateutil.parser
        try:
            dateutil.parser.parse(value)
            return True
        except:
            return False

    return False
