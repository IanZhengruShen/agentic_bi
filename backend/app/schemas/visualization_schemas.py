"""
Visualization Pydantic Schemas

Schemas for visualization API requests and responses.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================
# Visualization Request/Response Schemas
# ============================================

class VisualizationRequest(BaseModel):
    """Request to create visualization from analysis session data."""

    session_id: str = Field(..., description="Analysis session ID containing the data")
    chart_type: Optional[str] = Field(None, description="Specific chart type (skip recommendation if provided)")
    plotly_theme: str = Field("plotly", description="Base Plotly theme")
    custom_style_profile_id: Optional[str] = Field(None, description="Custom style profile ID to use")
    style_overrides: Optional[Dict[str, Any]] = Field(None, description="Ad-hoc style customizations")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "chart_type": "bar",
                "plotly_theme": "plotly_white",
                "custom_style_profile_id": "987fcdeb-51a2-43d1-b543-123456789abc",
                "options": {
                    "include_insights": True
                }
            }
        }


class ChartRecommendation(BaseModel):
    """Chart type recommendation from LLM."""

    recommended_type: str = Field(..., description="Recommended chart type")
    reasoning: str = Field(..., description="Why this chart type was recommended")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    alternatives: List[str] = Field(default_factory=list, description="Alternative chart types")
    data_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Data analysis that led to recommendation")


class PlotlyFigureResponse(BaseModel):
    """Plotly figure with metadata."""

    chart_type: str = Field(..., description="Chart type")
    plotly_json: Dict[str, Any] = Field(..., description="Complete Plotly figure as JSON")
    plotly_theme: str = Field(..., description="Applied theme")
    insights: List[str] = Field(default_factory=list, description="Generated insights")


class VisualizationResponse(BaseModel):
    """Complete visualization response."""

    visualization_id: str
    session_id: str
    chart_type: str
    plotly_figure: Dict[str, Any] = Field(..., description="Complete Plotly figure JSON")
    plotly_theme: str
    custom_style_profile_id: Optional[str] = None
    recommendation: Optional[ChartRecommendation] = None
    insights: List[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VisualizationListResponse(BaseModel):
    """List of visualizations for a session."""

    visualizations: List[VisualizationResponse]
    total: int


# ============================================
# Custom Style Profile Schemas
# ============================================

class CustomStyleProfileCreate(BaseModel):
    """Create custom style profile."""

    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    description: Optional[str] = Field(None, description="Profile description")
    is_default: bool = Field(False, description="Set as company default")
    is_public: bool = Field(False, description="Share with entire company")

    # Style configuration
    base_theme: str = Field("plotly", description="Base Plotly theme")
    color_palette: Optional[List[str]] = Field(None, description="Custom color palette (hex colors)")
    background_color: Optional[str] = Field(None, description="Background color (hex)")
    text_color: Optional[str] = Field(None, description="Text color (hex)")
    grid_color: Optional[str] = Field(None, description="Grid color (hex)")

    # Typography
    font_family: Optional[str] = Field(None, description="Font family")
    font_size: Optional[int] = Field(None, ge=8, le=72, description="Base font size in pixels")
    title_font_size: Optional[int] = Field(None, ge=10, le=96, description="Title font size in pixels")

    # Layout
    margin_config: Optional[Dict[str, int]] = Field(None, description="Margin configuration (l, r, t, b)")

    # Branding
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo URL (S3 or external)")
    logo_position: Optional[str] = Field("top-right", description="Logo position")
    logo_size: Optional[Dict[str, int]] = Field(None, description="Logo size (width, height)")
    watermark_text: Optional[str] = Field(None, max_length=100, description="Watermark text")

    # Advanced
    advanced_config: Optional[Dict[str, Any]] = Field(None, description="Advanced Plotly layout options")

    @field_validator('logo_position')
    @classmethod
    def validate_logo_position(cls, v):
        if v and v not in ["top-left", "top-right", "bottom-left", "bottom-right"]:
            raise ValueError("logo_position must be one of: top-left, top-right, bottom-left, bottom-right")
        return v

    @field_validator('color_palette')
    @classmethod
    def validate_color_palette(cls, v):
        if v:
            for color in v:
                if not color.startswith('#') or len(color) not in [4, 7]:
                    raise ValueError(f"Invalid hex color: {color}. Must be #RGB or #RRGGBB")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corp Brand",
                "description": "Corporate branding for all visualizations",
                "is_default": True,
                "is_public": True,
                "base_theme": "plotly_white",
                "color_palette": ["#FF6B35", "#004E89", "#1A936F", "#F77F00", "#06BEE1"],
                "background_color": "#FFFFFF",
                "font_family": "Arial, sans-serif",
                "font_size": 12,
                "logo_url": "https://s3.amazonaws.com/acme/logo.png",
                "logo_position": "top-right",
                "watermark_text": "Confidential"
            }
        }


class CustomStyleProfileUpdate(BaseModel):
    """Update custom style profile (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_public: Optional[bool] = None
    base_theme: Optional[str] = None
    color_palette: Optional[List[str]] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    grid_color: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = Field(None, ge=8, le=72)
    title_font_size: Optional[int] = Field(None, ge=10, le=96)
    margin_config: Optional[Dict[str, int]] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    logo_position: Optional[str] = None
    logo_size: Optional[Dict[str, int]] = None
    watermark_text: Optional[str] = Field(None, max_length=100)
    advanced_config: Optional[Dict[str, Any]] = None

    @field_validator('logo_position')
    @classmethod
    def validate_logo_position(cls, v):
        if v and v not in ["top-left", "top-right", "bottom-left", "bottom-right"]:
            raise ValueError("logo_position must be one of: top-left, top-right, bottom-left, bottom-right")
        return v


class CustomStyleProfileResponse(BaseModel):
    """Custom style profile response."""

    id: str
    company_id: str
    user_id: str
    name: str
    description: Optional[str]
    is_default: bool
    is_public: bool
    base_theme: str
    color_palette: Optional[List[str]]
    background_color: Optional[str]
    text_color: Optional[str]
    grid_color: Optional[str]
    font_family: Optional[str]
    font_size: Optional[int]
    title_font_size: Optional[int]
    margin_config: Optional[Dict[str, int]]
    logo_url: Optional[str]
    logo_position: Optional[str]
    logo_size: Optional[Dict[str, int]]
    watermark_text: Optional[str]
    advanced_config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomStyleProfileListResponse(BaseModel):
    """List of custom style profiles."""

    profiles: List[CustomStyleProfileResponse]
    total: int
    company_default: Optional[CustomStyleProfileResponse] = Field(None, description="Company's default profile if set")


# ============================================
# Logo Upload Schema
# ============================================

class LogoUploadResponse(BaseModel):
    """Response after logo upload."""

    logo_url: str = Field(..., description="URL of uploaded logo")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="MIME type")
    uploaded_at: datetime
