"""
Tests for trend_analysis statistical tool.
"""

import pytest
from app.tools.statistical_tools import trend_analysis


@pytest.mark.asyncio
async def test_increasing_trend():
    """Test detection of increasing trend."""
    data = [
        {"date": "2024-01", "revenue": 100},
        {"date": "2024-02", "revenue": 150},
        {"date": "2024-03", "revenue": 200},
        {"date": "2024-04", "revenue": 250},
        {"date": "2024-05", "revenue": 300},
    ]

    result = await trend_analysis(data)

    assert result.trend_direction == "increasing"
    assert result.trend_strength > 0.9  # Strong linear relationship
    assert result.confidence > 0.7
    assert result.slope is not None
    assert result.slope > 0  # Positive slope
    assert result.r_squared is not None
    assert result.r_squared > 0.9  # Good fit
    assert result.time_column == "date"
    assert result.value_column == "revenue"
    assert len(result.insights) > 0
    assert "increasing" in result.insights[0]


@pytest.mark.asyncio
async def test_decreasing_trend():
    """Test detection of decreasing trend."""
    data = [
        {"month": 1, "churn_rate": 50},
        {"month": 2, "churn_rate": 45},
        {"month": 3, "churn_rate": 40},
        {"month": 4, "churn_rate": 35},
        {"month": 5, "churn_rate": 30},
    ]

    result = await trend_analysis(data)

    assert result.trend_direction == "decreasing"
    assert result.trend_strength > 0.9
    assert result.slope is not None
    assert result.slope < 0  # Negative slope
    assert result.time_column == "month"
    assert result.value_column == "churn_rate"
    assert len(result.insights) > 0
    assert "decreasing" in result.insights[0]


@pytest.mark.asyncio
async def test_stable_trend():
    """Test detection of stable/flat trend."""
    data = [
        {"period": i, "value": 100 + (i % 2)}  # Oscillates around 100
        for i in range(10)
    ]

    result = await trend_analysis(data)

    assert result.trend_direction == "stable"
    assert result.trend_strength < 0.3  # Low trend strength
    assert result.time_column == "period"
    assert result.value_column == "value"
    assert len(result.insights) > 0
    assert "stable" in result.insights[0]


@pytest.mark.asyncio
async def test_trend_with_explicit_columns():
    """Test trend analysis with explicitly specified columns."""
    data = [
        {"year": 2020, "sales": 1000, "costs": 800},
        {"year": 2021, "sales": 1200, "costs": 850},
        {"year": 2022, "sales": 1400, "costs": 900},
        {"year": 2023, "sales": 1600, "costs": 950},
    ]

    result = await trend_analysis(
        data,
        time_column="year",
        value_column="sales"
    )

    assert result.trend_direction == "increasing"
    assert result.time_column == "year"
    assert result.value_column == "sales"
    assert result.slope > 0


@pytest.mark.asyncio
async def test_trend_insufficient_data():
    """Test trend analysis with insufficient data points."""
    data = [
        {"date": "2024-01", "value": 100},
        {"date": "2024-02", "value": 110},
    ]

    result = await trend_analysis(data)

    assert result.trend_direction == "unknown"
    assert result.trend_strength == 0.0
    assert result.confidence == 0.0
    assert len(result.warnings) > 0
    assert "at least 3" in result.warnings[0]


@pytest.mark.asyncio
async def test_trend_empty_data():
    """Test trend analysis with empty data."""
    data = []

    result = await trend_analysis(data)

    assert result.trend_direction == "unknown"
    assert result.sample_size == 0
    assert len(result.warnings) > 0


@pytest.mark.asyncio
async def test_trend_moving_average_method():
    """Test trend analysis using moving average method."""
    data = [
        {"index": i, "value": 100 + i * 10}
        for i in range(10)
    ]

    result = await trend_analysis(data, method="moving_average")

    assert result.trend_direction == "increasing"
    assert result.trend_strength > 0.0


@pytest.mark.asyncio
async def test_trend_auto_detect_columns():
    """Test automatic detection of time and value columns."""
    data = [
        {"created_at": "2024-01-01", "metric_value": 100, "category": "A"},
        {"created_at": "2024-01-02", "metric_value": 120, "category": "B"},
        {"created_at": "2024-01-03", "metric_value": 140, "category": "A"},
        {"created_at": "2024-01-04", "metric_value": 160, "category": "B"},
    ]

    result = await trend_analysis(data)

    # Should detect 'created_at' as time column (has 'created' keyword)
    assert result.time_column == "created_at"
    # Should detect 'metric_value' as value column (first numeric)
    assert result.value_column == "metric_value"
    assert result.trend_direction == "increasing"


@pytest.mark.asyncio
async def test_trend_with_missing_values():
    """Test trend analysis with some missing values."""
    data = [
        {"time": 1, "value": 100},
        {"time": 2, "value": None},  # Missing value
        {"time": 3, "value": 120},
        {"time": 4, "value": 140},
        {"time": 5, "value": 160},
    ]

    result = await trend_analysis(data)

    # Should handle missing values gracefully
    assert result.trend_direction == "increasing"
    assert result.sample_size == 4  # Only 4 valid values


@pytest.mark.asyncio
async def test_trend_weak_relationship():
    """Test detection of weak/noisy trend."""
    data = [
        {"x": i, "y": 100 + i * 2 + (i % 3) * 20}  # Trend with noise
        for i in range(10)
    ]

    result = await trend_analysis(data)

    assert result.trend_direction in ["increasing", "stable"]  # Might be either due to noise
    assert 0.0 <= result.r_squared <= 1.0
    assert 0.0 <= result.confidence <= 1.0
