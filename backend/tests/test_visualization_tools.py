"""
Tests for visualization tools.
"""

import pytest
import plotly.graph_objects as go
from unittest.mock import AsyncMock, MagicMock

from app.tools.visualization_tools import (
    recommend_chart_type,
    create_plotly_figure,
    apply_plotly_theme,
    generate_chart_insights,
)
from app.schemas.visualization_schemas import ChartRecommendation


# ============================================
# Chart Recommendation Tests
# ============================================

@pytest.mark.asyncio
async def test_recommend_bar_chart_for_categorical_data():
    """Test bar chart recommendation for categorical comparisons."""
    data = [
        {"region": "North", "sales": 1000},
        {"region": "South", "sales": 1500},
        {"region": "East", "sales": 1200},
        {"region": "West", "sales": 1800},
    ]

    # Mock LLM client
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"recommended_type": "bar", "reasoning": "Categorical comparison", "confidence": 0.9, "alternatives": ["pie", "table"]}'
    mock_llm.chat_completion.return_value = mock_response

    result = await recommend_chart_type(
        data=data,
        user_query="Show sales by region",
        analysis_results=None,
        llm_client=mock_llm,
    )

    assert result.recommended_type == "bar"
    assert result.confidence >= 0.8
    assert isinstance(result.alternatives, list)


@pytest.mark.asyncio
async def test_recommend_line_chart_for_time_series():
    """Test line chart recommendation for time series data."""
    data = [
        {"date": "2024-01", "revenue": 1000},
        {"date": "2024-02", "revenue": 1200},
        {"date": "2024-03", "revenue": 1400},
    ]

    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"recommended_type": "line", "reasoning": "Time series trend", "confidence": 0.95, "alternatives": ["area", "bar"]}'
    mock_llm.chat_completion.return_value = mock_response

    result = await recommend_chart_type(
        data=data,
        user_query="Show revenue trend over time",
        analysis_results=None,
        llm_client=mock_llm,
    )

    assert result.recommended_type == "line"


@pytest.mark.asyncio
async def test_recommend_chart_empty_data():
    """Test recommendation with empty data defaults to table."""
    data = []

    mock_llm = AsyncMock()

    result = await recommend_chart_type(
        data=data,
        user_query="Show data",
        analysis_results=None,
        llm_client=mock_llm,
    )

    assert result.recommended_type == "table"
    assert result.confidence == 1.0


# ============================================
# Chart Creation Tests
# ============================================

@pytest.mark.asyncio
async def test_create_bar_chart():
    """Test bar chart creation with Plotly."""
    data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
        {"category": "C", "value": 15},
    ]

    fig = await create_plotly_figure(
        data=data,
        chart_type="bar",
        user_query="Show values by category",
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.data[0].type == "bar"


@pytest.mark.asyncio
async def test_create_line_chart():
    """Test line chart creation."""
    data = [
        {"month": "Jan", "revenue": 1000},
        {"month": "Feb", "revenue": 1200},
        {"month": "Mar", "revenue": 1400},
    ]

    fig = await create_plotly_figure(
        data=data,
        chart_type="line",
        user_query="Revenue trend",
    )

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "scatter"  # Plotly line charts use scatter with mode='lines'


@pytest.mark.asyncio
async def test_create_pie_chart():
    """Test pie chart creation."""
    data = [
        {"category": "A", "percentage": 30},
        {"category": "B", "percentage": 45},
        {"category": "C", "percentage": 25},
    ]

    fig = await create_plotly_figure(
        data=data,
        chart_type="pie",
        user_query="Show distribution",
    )

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "pie"


@pytest.mark.asyncio
async def test_create_scatter_plot():
    """Test scatter plot creation."""
    data = [
        {"price": 10, "sales": 100},
        {"price": 15, "sales": 80},
        {"price": 20, "sales": 60},
        {"price": 25, "sales": 40},
    ]

    fig = await create_plotly_figure(
        data=data,
        chart_type="scatter",
        user_query="Price vs sales correlation",
    )

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "scatter"


@pytest.mark.asyncio
async def test_create_table():
    """Test table creation."""
    data = [
        {"name": "John", "age": 30, "city": "NYC"},
        {"name": "Jane", "age": 25, "city": "LA"},
    ]

    fig = await create_plotly_figure(
        data=data,
        chart_type="table",
        user_query="Show user data",
    )

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "table"


@pytest.mark.asyncio
async def test_create_chart_empty_data_raises_error():
    """Test that empty data raises ValueError."""
    data = []

    with pytest.raises(ValueError, match="No data provided"):
        await create_plotly_figure(
            data=data,
            chart_type="bar",
            user_query="Test",
        )


@pytest.mark.asyncio
async def test_create_chart_invalid_type_raises_error():
    """Test that invalid chart type raises ValueError."""
    data = [{"x": 1, "y": 2}]

    with pytest.raises(ValueError, match="Unsupported chart type"):
        await create_plotly_figure(
            data=data,
            chart_type="invalid_chart_type",
            user_query="Test",
        )


# ============================================
# Theme Application Tests
# ============================================

@pytest.mark.asyncio
async def test_apply_default_theme():
    """Test applying default Plotly theme."""
    data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
    fig = await create_plotly_figure(data, "bar", "Test")

    styled_fig = await apply_plotly_theme(fig, theme="plotly")

    assert isinstance(styled_fig, go.Figure)
    assert styled_fig.layout.template.layout.colorway is not None


@pytest.mark.asyncio
async def test_apply_custom_profile():
    """Test applying custom style profile with branding."""
    data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
    fig = await create_plotly_figure(data, "bar", "Test")

    custom_profile = {
        "base_theme": "plotly_white",
        "color_palette": ["#FF6B35", "#004E89", "#1A936F"],
        "font_family": "Arial, sans-serif",
        "font_size": 14,
        "background_color": "#FFFFFF",
        "watermark_text": "Confidential",
    }

    styled_fig = await apply_plotly_theme(
        fig,
        theme="plotly",
        custom_profile=custom_profile,
    )

    assert isinstance(styled_fig, go.Figure)
    # Verify custom colors applied
    assert styled_fig.layout.colorway == tuple(custom_profile["color_palette"])
    # Verify watermark added
    assert len(styled_fig.layout.annotations) > 0


@pytest.mark.asyncio
async def test_apply_theme_with_logo():
    """Test applying theme with logo."""
    data = [{"x": 1, "y": 10}]
    fig = await create_plotly_figure(data, "bar", "Test")

    custom_profile = {
        "base_theme": "plotly",
        "logo_url": "https://example.com/logo.png",
        "logo_position": "top-right",
        "logo_size": {"width": 100, "height": 50},
    }

    styled_fig = await apply_plotly_theme(
        fig,
        theme="plotly",
        custom_profile=custom_profile,
    )

    assert isinstance(styled_fig, go.Figure)
    # Verify logo image added
    assert len(styled_fig.layout.images) > 0
    assert styled_fig.layout.images[0].source == custom_profile["logo_url"]


# ============================================
# Insights Generation Tests
# ============================================

@pytest.mark.asyncio
async def test_generate_insights():
    """Test insights generation for chart."""
    data = [
        {"region": "North", "sales": 1000},
        {"region": "South", "sales": 2000},  # Highest
        {"region": "East", "sales": 1200},
    ]

    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"insights": ["South has highest sales at 2000", "North has lowest sales at 1000"]}'
    mock_llm.chat_completion.return_value = mock_response

    insights = await generate_chart_insights(
        data=data,
        chart_type="bar",
        chart_config={},
        analysis_results=None,
        llm_client=mock_llm,
    )

    assert isinstance(insights, list)
    assert len(insights) > 0


@pytest.mark.asyncio
async def test_generate_insights_empty_data():
    """Test insights with empty data."""
    data = []

    mock_llm = AsyncMock()

    insights = await generate_chart_insights(
        data=data,
        chart_type="bar",
        chart_config={},
        analysis_results=None,
        llm_client=mock_llm,
    )

    assert insights == ["No data available for analysis"]


@pytest.mark.asyncio
async def test_generate_insights_fallback_on_llm_error():
    """Test fallback to basic insights when LLM fails."""
    data = [
        {"x": 1, "value": 100},
        {"x": 2, "value": 200},
    ]

    mock_llm = AsyncMock()
    mock_llm.chat_completion.side_effect = Exception("LLM error")

    insights = await generate_chart_insights(
        data=data,
        chart_type="bar",
        chart_config={},
        analysis_results=None,
        llm_client=mock_llm,
    )

    # Should fallback to basic insights
    assert isinstance(insights, list)
    assert len(insights) > 0
