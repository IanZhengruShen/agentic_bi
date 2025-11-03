"""
Tests for correlation_analysis tool.
"""

import pytest
from app.tools.statistical_tools import correlation_analysis


@pytest.mark.asyncio
async def test_correlation_analysis_basic():
    """Test basic correlation analysis."""
    # Test data with clear correlation
    data = [
        {"x": 1, "y": 2, "z": 10},
        {"x": 2, "y": 4, "z": 20},
        {"x": 3, "y": 6, "z": 30},
        {"x": 4, "y": 8, "z": 40},
        {"x": 5, "y": 10, "z": 50},
    ]

    result = await correlation_analysis(data)

    assert result.method == "pearson"
    assert result.sample_size == 5
    assert len(result.columns_analyzed) == 3
    assert "x" in result.columns_analyzed
    assert "y" in result.columns_analyzed
    assert "z" in result.columns_analyzed

    # x and y should have perfect correlation
    assert result.correlation_matrix["x"]["y"] == pytest.approx(1.0, abs=0.01)
    # x and z should have perfect correlation
    assert result.correlation_matrix["x"]["z"] == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_correlation_analysis_no_correlation():
    """Test correlation with uncorrelated data."""
    data = [
        {"a": 1, "b": 5},
        {"a": 2, "b": 3},
        {"a": 3, "b": 8},
        {"a": 4, "b": 2},
        {"a": 5, "b": 9},
    ]

    result = await correlation_analysis(data)

    assert result.sample_size == 5
    # Should have weak or no correlation
    assert abs(result.correlation_matrix["a"]["b"]) < 0.9


@pytest.mark.asyncio
async def test_correlation_analysis_empty_data():
    """Test correlation with empty data."""
    data = []

    result = await correlation_analysis(data)

    assert result.sample_size == 0
    assert len(result.correlation_matrix) == 0
    assert len(result.warnings) > 0


@pytest.mark.asyncio
async def test_correlation_analysis_insufficient_columns():
    """Test correlation with only one numeric column."""
    data = [
        {"a": 1, "b": "text"},
        {"a": 2, "b": "text"},
        {"a": 3, "b": "text"},
    ]

    result = await correlation_analysis(data)

    assert len(result.warnings) > 0
    assert "at least 2 numeric columns" in result.warnings[0].lower()


@pytest.mark.asyncio
async def test_correlation_analysis_spearman():
    """Test Spearman correlation method."""
    data = [
        {"x": 1, "y": 1},
        {"x": 2, "y": 4},
        {"x": 3, "y": 9},
        {"x": 4, "y": 16},
        {"x": 5, "y": 25},
    ]

    result = await correlation_analysis(data, method="spearman")

    assert result.method == "spearman"
    assert result.sample_size == 5
    # Should detect monotonic relationship
    assert result.correlation_matrix["x"]["y"] > 0.9


@pytest.mark.asyncio
async def test_correlation_analysis_significant_correlations():
    """Test identification of significant correlations."""
    data = [
        {"a": 1, "b": 2, "c": 100},  # a and b correlated, c independent
        {"a": 2, "b": 4, "c": 50},
        {"a": 3, "b": 6, "c": 75},
        {"a": 4, "b": 8, "c": 25},
        {"a": 5, "b": 10, "c": 90},
    ]

    result = await correlation_analysis(data, significance_threshold=0.9)

    # Should find a-b correlation
    significant = result.significant_correlations
    assert len(significant) > 0

    # Check first significant correlation
    top_corr = significant[0]
    assert "column1" in top_corr
    assert "column2" in top_corr
    assert "correlation" in top_corr
    assert "strength" in top_corr
    assert "direction" in top_corr
