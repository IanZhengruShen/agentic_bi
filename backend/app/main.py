"""
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.api import (
    agents_router,
    visualizations_router,
    style_profiles_router,
    workflows_router,
    websocket_router,
    hitl_router,
    databases_router,
    chart_preferences_router,
    users_router,
)

# Create FastAPI app
app = FastAPI(
    title="Agentic BI Platform API",
    description="AI-powered data analysis and visualization platform with LangGraph agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router (authentication)
app.include_router(api_router, prefix="/api/v1")

# Include agent routers
app.include_router(agents_router)
app.include_router(visualizations_router)
app.include_router(style_profiles_router)
app.include_router(workflows_router)
app.include_router(databases_router)

# Include chart preferences router
app.include_router(chart_preferences_router)

# Include users router
app.include_router(users_router)

# Include WebSocket router
app.include_router(websocket_router)

# Include HITL router
app.include_router(hitl_router)

# Log registered routes on startup
@app.on_event("startup")
async def startup_event():
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Agentic BI Platform API - Registered Routes:")
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            logger.info(f"  {route.methods} {route.path}")
        elif hasattr(route, "path"):
            logger.info(f"  WebSocket {route.path}")
    logger.info("=" * 50)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Agentic BI Platform API",
        "version": "0.1.0",
        "status": "running",
        "features": [
            "LangGraph-based agent workflows",
            "Unified multi-agent orchestration (Analysis + Visualization)",
            "Human-in-the-loop interventions",
            "Natural language to SQL",
            "Automated data analysis",
            "AI-powered visualizations with Plotly",
            "Custom style profiles and branding",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "backend-api",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
