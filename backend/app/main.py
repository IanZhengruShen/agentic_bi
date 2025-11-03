"""
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

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
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents_router)


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
