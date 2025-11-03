"""
Visualization Database Models

Models for storing visualizations and custom style profiles.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.models.base import Base


class Visualization(Base):
    """
    Stores visualization configurations and results.

    Links to AnalysisSession and contains complete Plotly figure JSON.
    """
    __tablename__ = "visualizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Link to AnalysisSession
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Plotly figure
    chart_type = Column(String(50), nullable=False)  # bar, line, pie, scatter, heatmap, table, etc.
    plotly_figure_json = Column(JSON, nullable=False)  # Complete Plotly figure as JSON

    # Styling
    plotly_theme = Column(String(50), default="plotly")  # plotly, plotly_white, plotly_dark, custom
    custom_style_profile_id = Column(UUID(as_uuid=True), ForeignKey("custom_style_profiles.id"), nullable=True)
    theme_customizations = Column(JSON, nullable=True)  # Ad-hoc overrides

    # Metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    insights = Column(JSON, nullable=True)  # List of generated insights

    # Recommendation metadata
    recommendation_confidence = Column(Integer, nullable=True)  # 0-100 (stored as int for simplicity)
    alternative_chart_types = Column(JSON, nullable=True)  # List of alternative types considered

    # Status
    status = Column(String(50), default="pending")  # pending, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    custom_style_profile = relationship("CustomStyleProfile", backref="visualizations")

    def __repr__(self):
        return f"<Visualization(id={self.id}, chart_type={self.chart_type}, status={self.status})>"


class CustomStyleProfile(Base):
    """
    Custom style profiles for company branding.

    Allows companies to define custom color schemes, logos, fonts,
    and other styling options for consistent visualization appearance.
    """
    __tablename__ = "custom_style_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Creator

    # Profile metadata
    name = Column(String(100), nullable=False)  # e.g., "Corporate Brand", "Presentation Style"
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)  # Default style for company
    is_public = Column(Boolean, default=False, nullable=False)  # Shared across company

    # Style configuration
    base_theme = Column(String(50), default="plotly", nullable=False)  # Base Plotly theme

    # Color scheme
    color_palette = Column(JSON, nullable=True)  # ["#hex1", "#hex2", ...]
    background_color = Column(String(20), nullable=True)  # Hex color
    text_color = Column(String(20), nullable=True)  # Hex color
    grid_color = Column(String(20), nullable=True)  # Hex color

    # Typography
    font_family = Column(String(100), nullable=True)  # e.g., "Arial, sans-serif"
    font_size = Column(Integer, nullable=True)  # Base font size in px
    title_font_size = Column(Integer, nullable=True)  # Title font size in px

    # Layout
    margin_config = Column(JSON, nullable=True)  # {"l": 60, "r": 60, "t": 80, "b": 60}

    # Branding
    logo_url = Column(String(500), nullable=True)  # S3/cloud URL for logo image
    logo_position = Column(String(20), nullable=True)  # "top-left", "top-right", "bottom-left", "bottom-right"
    logo_size = Column(JSON, nullable=True)  # {"width": 100, "height": 50}
    watermark_text = Column(String(100), nullable=True)  # Optional watermark text

    # Advanced styling (full Plotly layout customization)
    advanced_config = Column(JSON, nullable=True)  # Additional Plotly layout options

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CustomStyleProfile(id={self.id}, name={self.name}, is_default={self.is_default})>"

    def to_dict(self):
        """Convert to dictionary for use in styling tools."""
        return {
            "id": str(self.id),
            "name": self.name,
            "base_theme": self.base_theme,
            "color_palette": self.color_palette,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "grid_color": self.grid_color,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "title_font_size": self.title_font_size,
            "margin_config": self.margin_config,
            "logo_url": self.logo_url,
            "logo_position": self.logo_position,
            "logo_size": self.logo_size,
            "watermark_text": self.watermark_text,
            "advanced_config": self.advanced_config,
        }
