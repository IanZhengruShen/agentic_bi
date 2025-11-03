"""API routes for the Agentic BI platform."""

from app.api.agents import router as agents_router
from app.api.visualizations import router as visualizations_router
from app.api.style_profiles import router as style_profiles_router
from app.api.workflows import router as workflows_router

__all__ = [
    "agents_router",
    "visualizations_router",
    "style_profiles_router",
    "workflows_router",
]
