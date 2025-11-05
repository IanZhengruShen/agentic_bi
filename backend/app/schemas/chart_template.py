"""
Chart template schemas for Plotly styling.

This module defines schemas for managing user chart preferences using Plotly's
native template system.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class PlotlyLayoutTemplate(BaseModel):
    """Plotly layout template structure."""
    font: Optional[Dict[str, Any]] = None
    title: Optional[Dict[str, Any]] = None
    colorway: Optional[List[str]] = None
    plot_bgcolor: Optional[str] = None
    paper_bgcolor: Optional[str] = None
    hovermode: Optional[str] = None
    logo_url: Optional[str] = None  # URL or base64 data URI for logo
    logo_position: Optional[Dict[str, Any]] = None  # x, y, sizex, sizey, xanchor, yanchor
    # Add more as needed


class PlotlyDataTemplate(BaseModel):
    """Plotly data template structure (chart-specific styling)."""
    bar: Optional[List[Dict[str, Any]]] = None
    scatter: Optional[List[Dict[str, Any]]] = None
    line: Optional[List[Dict[str, Any]]] = None
    # Add more chart types as needed


class CustomTemplateDefinition(BaseModel):
    """Full custom Plotly template."""
    layout: Optional[PlotlyLayoutTemplate] = None
    data: Optional[PlotlyDataTemplate] = None


class ChartTemplateConfig(BaseModel):
    """User's chart template configuration."""
    type: Literal["builtin", "custom"] = "builtin"
    name: Optional[str] = None  # If builtin: "plotly_white", "ggplot2", etc.
    custom_definition: Optional[CustomTemplateDefinition] = None  # If custom
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SavedTemplate(BaseModel):
    """User-saved custom template."""
    id: str
    name: str
    description: Optional[str] = None
    template_definition: CustomTemplateDefinition
    thumbnail: Optional[str] = None  # Base64 or URL
    created_at: datetime
    updated_at: datetime


class UserChartPreferences(BaseModel):
    """Complete user chart preferences."""
    chart_template: Optional[ChartTemplateConfig] = None
    saved_templates: List[SavedTemplate] = []


class UpdateChartPreferencesRequest(BaseModel):
    """Request to update chart preferences."""
    chart_template: ChartTemplateConfig


class SaveTemplateRequest(BaseModel):
    """Request to save a custom template."""
    name: str
    description: Optional[str] = None
    template_definition: CustomTemplateDefinition
    thumbnail: Optional[str] = None


class ChartPreferencesResponse(BaseModel):
    """Response with user preferences."""
    chart_template: ChartTemplateConfig
    saved_templates: List[SavedTemplate]
    available_builtin_templates: List[str]  # List of Plotly template names


# Built-in Plotly templates
BUILTIN_PLOTLY_TEMPLATES = [
    "plotly",
    "plotly_white",
    "plotly_dark",
    "ggplot2",
    "seaborn",
    "simple_white",
    "presentation",
    "xgridoff",
    "ygridoff",
    "gridon",
    "none"
]
