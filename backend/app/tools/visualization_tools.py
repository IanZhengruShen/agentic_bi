"""
Visualization Tools

Plotly-based tools for chart generation and styling.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.core.llm import LLMClient
from app.schemas.visualization_schemas import ChartRecommendation

logger = logging.getLogger(__name__)


# ============================================
# Tool 1: Recommend Chart Type
# ============================================

async def recommend_chart_type(
    data: List[Dict[str, Any]],
    user_query: str,
    analysis_results: Optional[Dict[str, Any]],
    llm_client: LLMClient,
) -> ChartRecommendation:
    """
    Recommend best chart type based on data characteristics and user intent.

    Uses combination of:
    1. Data analysis (column types, cardinality, etc.)
    2. User query intent parsing
    3. LLM intelligence

    Args:
        data: Query results as list of dicts
        user_query: Original user query for context
        analysis_results: Optional analysis results from AnalysisAgent
        llm_client: LLM client for intelligent recommendation

    Returns:
        ChartRecommendation with type, reasoning, confidence, alternatives
    """
    logger.info(f"Recommending chart type for {len(data)} rows")

    try:
        if not data:
            return ChartRecommendation(
                recommended_type="table",
                reasoning="No data available, defaulting to table view",
                confidence=1.0,
                alternatives=[],
                data_characteristics={"row_count": 0}
            )

        # Analyze data characteristics
        df = pd.DataFrame(data)
        characteristics = _analyze_data_characteristics(df)

        # Build prompt for LLM
        prompt = f"""You are a data visualization expert. Recommend the best chart type for this data.

User's question: "{user_query}"

Data characteristics:
- Rows: {len(df)}
- Columns: {len(df.columns)}
- Column details: {characteristics['columns_summary']}
- Numeric columns: {characteristics['numeric_columns']}
- Categorical columns: {characteristics['categorical_columns']}
- Temporal columns: {characteristics['temporal_columns']}

Available chart types:
- bar: Categorical comparisons (vertical/horizontal bars)
- line: Trends over time or continuous data
- pie: Part-to-whole relationships (best for <7 categories)
- scatter: Correlation between two numeric variables
- heatmap: Matrix data with intensity values
- histogram: Distribution of a single numeric variable
- box: Statistical distribution with quartiles
- area: Cumulative trends over time
- table: Detailed data display

Respond with JSON only:
{{
    "recommended_type": "chart_type",
    "reasoning": "Brief explanation why this chart is best",
    "confidence": 0.9,
    "alternatives": ["alternative1", "alternative2"]
}}

Consider:
1. What is the user asking? (comparison, trend, distribution, correlation, etc.)
2. What types of data do we have?
3. How many data points and categories?
4. Will this chart answer the user's question clearly?
"""

        # Get LLM recommendation
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for consistent recommendations
        )

        # Parse LLM response
        import json
        import re
        response_text = response.content if hasattr(response, 'content') else str(response)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            recommendation_data = json.loads(json_match.group(0))

            return ChartRecommendation(
                recommended_type=recommendation_data.get("recommended_type", "bar"),
                reasoning=recommendation_data.get("reasoning", "LLM recommendation"),
                confidence=float(recommendation_data.get("confidence", 0.8)),
                alternatives=recommendation_data.get("alternatives", []),
                data_characteristics=characteristics
            )
        else:
            # Fallback to rule-based recommendation
            return _rule_based_recommendation(df, user_query, characteristics)

    except Exception as e:
        logger.error(f"Chart recommendation failed: {e}")
        # Fallback to safe default
        return ChartRecommendation(
            recommended_type="bar",
            reasoning=f"Error in recommendation: {str(e)}, defaulting to bar chart",
            confidence=0.5,
            alternatives=["line", "table"],
            data_characteristics={}
        )


def _analyze_data_characteristics(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze DataFrame to extract characteristics for recommendation."""
    characteristics = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_columns": [],
        "categorical_columns": [],
        "temporal_columns": [],
        "columns_summary": {}
    }

    for col in df.columns:
        col_data = df[col].dropna()
        if len(col_data) == 0:
            continue

        # Determine column type
        if pd.api.types.is_numeric_dtype(col_data):
            characteristics["numeric_columns"].append(col)
            characteristics["columns_summary"][col] = {
                "type": "numeric",
                "unique_count": col_data.nunique(),
                "min": float(col_data.min()) if len(col_data) > 0 else None,
                "max": float(col_data.max()) if len(col_data) > 0 else None,
            }
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            characteristics["temporal_columns"].append(col)
            characteristics["columns_summary"][col] = {
                "type": "temporal",
                "unique_count": col_data.nunique(),
            }
        else:
            # Categorical
            characteristics["categorical_columns"].append(col)
            unique_count = col_data.nunique()
            characteristics["columns_summary"][col] = {
                "type": "categorical",
                "unique_count": unique_count,
                "cardinality": "low" if unique_count < 10 else "medium" if unique_count < 50 else "high",
            }

    return characteristics


def _rule_based_recommendation(
    df: pd.DataFrame,
    user_query: str,
    characteristics: Dict[str, Any]
) -> ChartRecommendation:
    """Fallback rule-based chart recommendation."""
    num_numeric = len(characteristics["numeric_columns"])
    num_categorical = len(characteristics["categorical_columns"])
    num_temporal = len(characteristics["temporal_columns"])

    # Rule 1: Time series data -> line chart
    if num_temporal >= 1 and num_numeric >= 1:
        return ChartRecommendation(
            recommended_type="line",
            reasoning="Temporal data detected, line chart shows trends well",
            confidence=0.85,
            alternatives=["area", "bar"],
            data_characteristics=characteristics
        )

    # Rule 2: Two numeric columns -> scatter plot
    if num_numeric >= 2 and "correlation" in user_query.lower():
        return ChartRecommendation(
            recommended_type="scatter",
            reasoning="Two numeric columns with correlation query, scatter plot shows relationships",
            confidence=0.9,
            alternatives=["line", "bar"],
            data_characteristics=characteristics
        )

    # Rule 3: One categorical, one numeric -> bar chart
    if num_categorical >= 1 and num_numeric >= 1:
        return ChartRecommendation(
            recommended_type="bar",
            reasoning="Categorical and numeric data, bar chart for comparisons",
            confidence=0.8,
            alternatives=["pie", "table"],
            data_characteristics=characteristics
        )

    # Rule 4: Distribution query -> histogram
    if "distribution" in user_query.lower() and num_numeric >= 1:
        return ChartRecommendation(
            recommended_type="histogram",
            reasoning="Distribution analysis requested, histogram shows frequency distribution",
            confidence=0.85,
            alternatives=["box", "bar"],
            data_characteristics=characteristics
        )

    # Default: bar chart
    return ChartRecommendation(
        recommended_type="bar",
        reasoning="General purpose bar chart for comparisons",
        confidence=0.6,
        alternatives=["line", "table"],
        data_characteristics=characteristics
    )


# ============================================
# Tool 2: Create Plotly Figure
# ============================================

async def create_plotly_figure(
    data: List[Dict[str, Any]],
    chart_type: str,
    user_query: str,
    analysis_results: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None,
) -> go.Figure:
    """
    Generate Plotly figure from data.

    Supports multiple chart types with intelligent column mapping.

    Args:
        data: Query results as list of dicts
        chart_type: Chart type to create
        user_query: Original user query for context
        analysis_results: Optional analysis results
        llm_client: Optional LLM for intelligent column selection

    Returns:
        Plotly figure object

    Raises:
        ValueError: If chart type is unsupported or data is invalid
    """
    logger.info(f"Creating {chart_type} chart for {len(data)} rows")

    try:
        if not data:
            raise ValueError("No data provided for visualization")

        # Convert to pandas DataFrame
        df = pd.DataFrame(data)

        # Generate chart title from user query
        title = _generate_chart_title(user_query)

        # Determine column mappings (x, y, color, etc.)
        mappings = _determine_column_mappings(df, chart_type, user_query)

        # Create appropriate Plotly figure
        if chart_type == "bar":
            fig = px.bar(
                df,
                x=mappings["x"],
                y=mappings["y"],
                color=mappings.get("color"),
                title=title,
                barmode=mappings.get("barmode", "group")
            )

        elif chart_type == "line":
            fig = px.line(
                df,
                x=mappings["x"],
                y=mappings["y"],
                color=mappings.get("color"),
                title=title,
            )

        elif chart_type == "pie":
            fig = px.pie(
                df,
                names=mappings["x"],
                values=mappings["y"],
                title=title,
            )

        elif chart_type == "scatter":
            fig = px.scatter(
                df,
                x=mappings["x"],
                y=mappings["y"],
                color=mappings.get("color"),
                size=mappings.get("size"),
                title=title,
            )

        elif chart_type == "heatmap":
            # Heatmap requires pivot or matrix data
            if mappings.get("pivot_index") and mappings.get("pivot_columns"):
                pivot_df = df.pivot_table(
                    values=mappings["y"],
                    index=mappings["pivot_index"],
                    columns=mappings["pivot_columns"],
                    fill_value=0
                )
                fig = px.imshow(
                    pivot_df,
                    title=title,
                    labels=dict(x=mappings["pivot_columns"], y=mappings["pivot_index"], color=mappings["y"])
                )
            else:
                # Correlation heatmap
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) >= 2:
                    corr_matrix = df[numeric_cols].corr()
                    fig = px.imshow(
                        corr_matrix,
                        title=title + " - Correlation Matrix",
                        labels=dict(color="Correlation")
                    )
                else:
                    raise ValueError("Heatmap requires at least 2 numeric columns or pivot configuration")

        elif chart_type == "histogram":
            fig = px.histogram(
                df,
                x=mappings["x"],
                color=mappings.get("color"),
                title=title,
            )

        elif chart_type == "box":
            fig = px.box(
                df,
                x=mappings.get("x"),
                y=mappings["y"],
                color=mappings.get("color"),
                title=title,
            )

        elif chart_type == "area":
            fig = px.area(
                df,
                x=mappings["x"],
                y=mappings["y"],
                color=mappings.get("color"),
                title=title,
            )

        elif chart_type == "table":
            # Create table visualization
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color='paleturquoise',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color='lavender',
                    align='left',
                    font=dict(size=11)
                )
            )])
            fig.update_layout(title=title)

        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        # Configure default interactivity
        fig.update_layout(
            hovermode='closest',
            dragmode='zoom',
        )

        logger.info(f"Successfully created {chart_type} chart")
        return fig

    except Exception as e:
        logger.error(f"Failed to create Plotly figure: {e}")
        raise


def _determine_column_mappings(
    df: pd.DataFrame,
    chart_type: str,
    user_query: str
) -> Dict[str, Any]:
    """
    Determine best column mappings for chart axes.

    Uses heuristics to select appropriate columns for x, y, color, etc.

    Args:
        df: DataFrame with data
        chart_type: Type of chart being created
        user_query: User's question for hints

    Returns:
        Dictionary with column mappings
    """
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

    mappings = {}

    if chart_type in ["bar", "line", "area"]:
        # X-axis: prefer datetime > categorical > first column
        if datetime_cols:
            mappings["x"] = datetime_cols[0]
        elif categorical_cols:
            mappings["x"] = categorical_cols[0]
        else:
            mappings["x"] = df.columns[0]

        # Y-axis: prefer numeric columns
        if numeric_cols:
            mappings["y"] = numeric_cols[0]
        else:
            mappings["y"] = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        # Color: use second categorical if available
        if len(categorical_cols) > 1:
            mappings["color"] = categorical_cols[1]

    elif chart_type == "pie":
        # Names: categorical or first column
        if categorical_cols:
            mappings["x"] = categorical_cols[0]
        else:
            mappings["x"] = df.columns[0]

        # Values: numeric or second column
        if numeric_cols:
            mappings["y"] = numeric_cols[0]
        else:
            mappings["y"] = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    elif chart_type == "scatter":
        # X and Y: first two numeric columns
        if len(numeric_cols) >= 2:
            mappings["x"] = numeric_cols[0]
            mappings["y"] = numeric_cols[1]
            if len(numeric_cols) >= 3:
                mappings["size"] = numeric_cols[2]
        else:
            mappings["x"] = df.columns[0]
            mappings["y"] = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        # Color: categorical if available
        if categorical_cols:
            mappings["color"] = categorical_cols[0]

    elif chart_type == "heatmap":
        # Try to find pivot columns
        if len(categorical_cols) >= 2 and numeric_cols:
            mappings["pivot_index"] = categorical_cols[0]
            mappings["pivot_columns"] = categorical_cols[1]
            mappings["y"] = numeric_cols[0]

    elif chart_type in ["histogram", "box"]:
        # Use first numeric column
        if numeric_cols:
            mappings["x"] = numeric_cols[0]
            mappings["y"] = numeric_cols[0]
        else:
            mappings["x"] = df.columns[0]
            mappings["y"] = df.columns[0]

        # Color by categorical
        if categorical_cols:
            mappings["color"] = categorical_cols[0]

    return mappings


def _generate_chart_title(user_query: str) -> str:
    """Generate appropriate chart title from user query."""
    # Simple heuristic: capitalize first letter and ensure it's a reasonable length
    title = user_query.strip()
    if len(title) > 100:
        title = title[:97] + "..."
    return title[0].upper() + title[1:] if title else "Data Visualization"


# ============================================
# Tool 3: Apply Plotly Theme
# ============================================

async def apply_plotly_theme(
    fig: go.Figure,
    theme: str = "plotly",
    custom_profile: Optional[Dict[str, Any]] = None,
    customizations: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """
    Apply Plotly theme and custom styling to figure.

    Supports:
    - Built-in Plotly themes
    - Custom style profiles (enterprise branding)
    - Logo placement
    - Watermarks
    - Ad-hoc customizations

    Args:
        fig: Plotly figure to style
        theme: Base Plotly theme
        custom_profile: Optional CustomStyleProfile dict
        customizations: Optional ad-hoc style overrides

    Returns:
        Styled Plotly figure
    """
    logger.info(f"Applying theme: {theme}, custom_profile: {custom_profile is not None}")

    try:
        # Step 1: Apply base Plotly theme
        base_theme = theme
        if custom_profile:
            base_theme = custom_profile.get("base_theme", theme)
        fig.update_layout(template=base_theme)

        # Step 2: Apply custom profile styling (if provided)
        if custom_profile:
            # Color palette
            if custom_profile.get("color_palette"):
                fig.update_layout(colorway=custom_profile["color_palette"])

            # Background colors
            if custom_profile.get("background_color"):
                fig.update_layout(
                    plot_bgcolor=custom_profile["background_color"],
                    paper_bgcolor=custom_profile["background_color"]
                )

            # Text color
            if custom_profile.get("text_color"):
                fig.update_layout(font_color=custom_profile["text_color"])

            # Grid color
            if custom_profile.get("grid_color"):
                fig.update_xaxes(gridcolor=custom_profile["grid_color"])
                fig.update_yaxes(gridcolor=custom_profile["grid_color"])

            # Typography
            font_config = {}
            if custom_profile.get("font_family"):
                font_config["family"] = custom_profile["font_family"]
            if custom_profile.get("font_size"):
                font_config["size"] = custom_profile["font_size"]
            if font_config:
                fig.update_layout(font=font_config)

            # Title font size
            if custom_profile.get("title_font_size"):
                fig.update_layout(title_font_size=custom_profile["title_font_size"])

            # Margins
            if custom_profile.get("margin_config"):
                fig.update_layout(margin=custom_profile["margin_config"])

            # Logo
            if custom_profile.get("logo_url"):
                _add_logo_to_figure(
                    fig,
                    logo_url=custom_profile["logo_url"],
                    position=custom_profile.get("logo_position", "top-right"),
                    size=custom_profile.get("logo_size", {"width": 100, "height": 50})
                )

            # Watermark
            if custom_profile.get("watermark_text"):
                _add_watermark_to_figure(
                    fig,
                    text=custom_profile["watermark_text"]
                )

            # Advanced config
            if custom_profile.get("advanced_config"):
                fig.update_layout(**custom_profile["advanced_config"])

        # Step 3: Apply ad-hoc customizations (override everything)
        if customizations:
            if "colors" in customizations:
                fig.update_layout(colorway=customizations["colors"])
            if "font_family" in customizations or "font_size" in customizations:
                fig.update_layout(
                    font=dict(
                        family=customizations.get("font_family"),
                        size=customizations.get("font_size", 12),
                    )
                )
            if "margin" in customizations:
                fig.update_layout(margin=customizations["margin"])
            # Apply any other layout customizations
            for key, value in customizations.items():
                if key not in ["colors", "font_family", "font_size", "margin"]:
                    fig.update_layout(**{key: value})

        logger.info("Theme applied successfully")
        return fig

    except Exception as e:
        logger.error(f"Failed to apply theme: {e}")
        # Return figure as-is on error
        return fig


def _add_logo_to_figure(
    fig: go.Figure,
    logo_url: str,
    position: str = "top-right",
    size: Dict[str, int] = None
) -> None:
    """Add company logo to figure as image annotation."""
    if size is None:
        size = {"width": 100, "height": 50}

    # Position coordinates (normalized 0-1)
    position_map = {
        "top-left": {"x": 0.02, "y": 0.98, "xanchor": "left", "yanchor": "top"},
        "top-right": {"x": 0.98, "y": 0.98, "xanchor": "right", "yanchor": "top"},
        "bottom-left": {"x": 0.02, "y": 0.02, "xanchor": "left", "yanchor": "bottom"},
        "bottom-right": {"x": 0.98, "y": 0.02, "xanchor": "right", "yanchor": "bottom"},
    }

    pos_config = position_map.get(position, position_map["top-right"])

    # Add logo as layout image
    fig.add_layout_image(
        dict(
            source=logo_url,
            xref="paper", yref="paper",
            x=pos_config["x"], y=pos_config["y"],
            sizex=size["width"]/1000,  # Relative size
            sizey=size["height"]/1000,
            xanchor=pos_config["xanchor"],
            yanchor=pos_config["yanchor"],
            layer="above"
        )
    )


def _add_watermark_to_figure(
    fig: go.Figure,
    text: str,
) -> None:
    """Add watermark text to figure."""
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=50, color="rgba(150, 150, 150, 0.15)"),
        textangle=-30,
    )


# ============================================
# Tool 4: Generate Chart Insights
# ============================================

async def generate_chart_insights(
    data: List[Dict[str, Any]],
    chart_type: str,
    chart_config: Dict[str, Any],
    analysis_results: Optional[Dict[str, Any]],
    llm_client: LLMClient,
) -> List[str]:
    """
    Generate natural language insights about the visualization.

    Uses LLM to analyze the data and chart configuration to produce
    meaningful insights that help users understand what the chart shows.

    Args:
        data: Query results
        chart_type: Type of chart created
        chart_config: Chart configuration details
        analysis_results: Optional analysis results
        llm_client: LLM client

    Returns:
        List of insight strings
    """
    logger.info(f"Generating insights for {chart_type} chart")

    try:
        if not data:
            return ["No data available for analysis"]

        df = pd.DataFrame(data)

        # Build prompt for LLM
        prompt = f"""Generate 2-4 concise insights about this visualization.

Chart type: {chart_type}
Data summary:
- Rows: {len(df)}
- Columns: {list(df.columns)}
- Sample data: {df.head(3).to_dict('records')}

Focus on:
1. Key patterns or trends visible in the chart
2. Notable highest/lowest values
3. Comparisons between categories or time periods
4. Any anomalies or interesting observations

Format: Return a JSON array of insight strings.
{{"insights": ["insight 1", "insight 2", ...]}}

Keep insights concise (1-2 sentences each) and actionable.
"""

        # Get LLM insights
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        # Parse response
        import json
        import re
        response_text = response.content if hasattr(response, 'content') else str(response)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            insights_data = json.loads(json_match.group(0))
            insights = insights_data.get("insights", [])
            if insights:
                logger.info(f"Generated {len(insights)} insights")
                return insights

        # Fallback to basic statistical insights
        return _generate_basic_insights(df, chart_type)

    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        return [f"Visualization shows {len(data)} data points"]


def _generate_basic_insights(df: pd.DataFrame, chart_type: str) -> List[str]:
    """Generate basic statistical insights without LLM."""
    insights = []

    numeric_cols = df.select_dtypes(include=['number']).columns

    if len(numeric_cols) > 0:
        # Find column with highest value
        for col in numeric_cols[:2]:  # Limit to first 2 numeric columns
            max_val = df[col].max()
            min_val = df[col].min()
            insights.append(f"{col} ranges from {min_val:.2f} to {max_val:.2f}")

    insights.append(f"Chart displays {len(df)} data points")

    return insights[:3]  # Limit to 3 insights
