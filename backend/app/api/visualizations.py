"""
Visualization API Endpoints

REST API for creating and managing visualizations.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.models.user import User
from app.models.visualization_models import Visualization, CustomStyleProfile
from app.models.agent_models import AnalysisSession
from app.schemas.visualization_schemas import (
    VisualizationRequest,
    VisualizationResponse,
    VisualizationListResponse,
)
from app.api.deps import get_current_user
from app.agents.visualization_agent import create_visualization_agent
from langfuse.langchain import CallbackHandler
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualizations", tags=["visualizations"])


@router.post("/", response_model=VisualizationResponse, status_code=status.HTTP_201_CREATED)
async def create_visualization(
    request: VisualizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create visualization from analysis session data.

    Workflow:
    1. Fetch AnalysisSession and verify ownership
    2. Load custom style profile if specified
    3. Initialize VisualizationAgent
    4. Run workflow to generate Plotly figure
    5. Save visualization to database
    6. Return complete visualization response

    Args:
        request: Visualization creation request
        current_user: Authenticated user
        db: Database session

    Returns:
        VisualizationResponse with complete Plotly figure
    """
    logger.info(f"Creating visualization for session {request.session_id}")

    try:
        # 1. Fetch and verify AnalysisSession
        session = db.query(AnalysisSession).filter(
            AnalysisSession.id == UUID(request.session_id),
            AnalysisSession.company_id == current_user.company_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session {request.session_id} not found"
            )

        if not session.query_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analysis session has no data to visualize"
            )

        # 2. Load custom style profile if specified
        custom_profile = None
        if request.custom_style_profile_id:
            profile = db.query(CustomStyleProfile).filter(
                CustomStyleProfile.id == UUID(request.custom_style_profile_id),
                CustomStyleProfile.company_id == current_user.company_id
            ).first()

            if profile:
                custom_profile = profile.to_dict()
                logger.info(f"Using custom style profile: {profile.name}")
            else:
                logger.warning(f"Custom profile {request.custom_style_profile_id} not found, using default")

        # 3. Initialize Langfuse callback
        langfuse_handler = None
        if settings.langfuse.langfuse_public_key and settings.langfuse.langfuse_secret_key:
            langfuse_handler = CallbackHandler(
                public_key=settings.langfuse.langfuse_public_key,
                secret_key=settings.langfuse.langfuse_secret_key,
                host=settings.langfuse.langfuse_host,
            )

        # 4. Create VisualizationAgent and run workflow
        agent = create_visualization_agent(langfuse_handler=langfuse_handler)

        result = await agent.create_visualization(
            session_id=request.session_id,
            data=session.query_data,
            user_query=session.query,
            analysis_results=session.analysis_results,
            chart_type=request.chart_type,
            plotly_theme=request.plotly_theme,
            custom_style_profile_id=request.custom_style_profile_id,
            custom_style_profile=custom_profile,
            style_overrides=request.style_overrides,
            include_insights=request.options.get("include_insights", True),
        )

        # Check if workflow succeeded
        if result.get("workflow_status") == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Visualization creation failed: {result.get('errors', ['Unknown error'])}"
            )

        # 5. Save to database
        visualization = Visualization(
            id=UUID(result["visualization_id"]),
            session_id=UUID(request.session_id),
            user_id=current_user.id,
            company_id=current_user.company_id,
            chart_type=result["chart_type"],
            plotly_figure_json=result["plotly_figure"],
            plotly_theme=request.plotly_theme,
            custom_style_profile_id=UUID(request.custom_style_profile_id) if request.custom_style_profile_id else None,
            theme_customizations=request.style_overrides,
            insights=result.get("chart_insights", []),
            recommendation_confidence=int(result.get("recommendation_confidence", 0.8) * 100) if result.get("recommendation_confidence") else None,
            alternative_chart_types=result.get("alternative_chart_types"),
            status="completed",
        )

        db.add(visualization)
        db.commit()
        db.refresh(visualization)

        logger.info(f"Visualization {visualization.id} created successfully")

        # 6. Return response
        return VisualizationResponse(
            visualization_id=str(visualization.id),
            session_id=str(visualization.session_id),
            chart_type=visualization.chart_type,
            plotly_figure=visualization.plotly_figure_json,
            plotly_theme=visualization.plotly_theme,
            custom_style_profile_id=str(visualization.custom_style_profile_id) if visualization.custom_style_profile_id else None,
            insights=visualization.insights or [],
            status=visualization.status,
            created_at=visualization.created_at,
            updated_at=visualization.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create visualization: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create visualization: {str(e)}"
        )


@router.get("/{viz_id}", response_model=VisualizationResponse)
async def get_visualization(
    viz_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get visualization by ID.

    Args:
        viz_id: Visualization ID
        current_user: Authenticated user
        db: Database session

    Returns:
        VisualizationResponse
    """
    logger.info(f"Fetching visualization {viz_id}")

    try:
        visualization = db.query(Visualization).filter(
            Visualization.id == UUID(viz_id),
            Visualization.company_id == current_user.company_id
        ).first()

        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        return VisualizationResponse(
            visualization_id=str(visualization.id),
            session_id=str(visualization.session_id),
            chart_type=visualization.chart_type,
            plotly_figure=visualization.plotly_figure_json,
            plotly_theme=visualization.plotly_theme,
            custom_style_profile_id=str(visualization.custom_style_profile_id) if visualization.custom_style_profile_id else None,
            insights=visualization.insights or [],
            status=visualization.status,
            created_at=visualization.created_at,
            updated_at=visualization.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch visualization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch visualization: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=VisualizationListResponse)
async def list_session_visualizations(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all visualizations for an analysis session.

    Args:
        session_id: Analysis session ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of visualizations for the session
    """
    logger.info(f"Listing visualizations for session {session_id}")

    try:
        # Verify session exists and user has access
        session = db.query(AnalysisSession).filter(
            AnalysisSession.id == UUID(session_id),
            AnalysisSession.company_id == current_user.company_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session {session_id} not found"
            )

        # Fetch visualizations
        visualizations = db.query(Visualization).filter(
            Visualization.session_id == UUID(session_id),
            Visualization.company_id == current_user.company_id
        ).order_by(Visualization.created_at.desc()).all()

        viz_responses = [
            VisualizationResponse(
                visualization_id=str(viz.id),
                session_id=str(viz.session_id),
                chart_type=viz.chart_type,
                plotly_figure=viz.plotly_figure_json,
                plotly_theme=viz.plotly_theme,
                custom_style_profile_id=str(viz.custom_style_profile_id) if viz.custom_style_profile_id else None,
                insights=viz.insights or [],
                status=viz.status,
                created_at=viz.created_at,
                updated_at=viz.updated_at,
            )
            for viz in visualizations
        ]

        return VisualizationListResponse(
            visualizations=viz_responses,
            total=len(viz_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list visualizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list visualizations: {str(e)}"
        )


@router.delete("/{viz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visualization(
    viz_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete visualization.

    Args:
        viz_id: Visualization ID
        current_user: Authenticated user
        db: Database session

    Returns:
        204 No Content on success
    """
    logger.info(f"Deleting visualization {viz_id}")

    try:
        visualization = db.query(Visualization).filter(
            Visualization.id == UUID(viz_id),
            Visualization.company_id == current_user.company_id
        ).first()

        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        db.delete(visualization)
        db.commit()

        logger.info(f"Visualization {viz_id} deleted successfully")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete visualization: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete visualization: {str(e)}"
        )
