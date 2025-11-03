"""
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

from app.api import agents_router

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
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Agentic BI Platform API",
        "version": "0.1.0",
        "status": "running",
        "features": [
            "LangGraph-based agent workflows",
            "Human-in-the-loop interventions",
            "Natural language to SQL",
            "Automated data analysis",
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
