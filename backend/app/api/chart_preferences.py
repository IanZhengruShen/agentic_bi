"""
Chart preferences API endpoints.

This module provides endpoints for managing user chart styling preferences
using Plotly's native template system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
import uuid

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chart_template import (
    UserChartPreferences,
    ChartPreferencesResponse,
    UpdateChartPreferencesRequest,
    SaveTemplateRequest,
    ChartTemplateConfig,
    SavedTemplate,
    BUILTIN_PLOTLY_TEMPLATES
)

router = APIRouter(prefix="/api/user/chart", tags=["chart-preferences"])


@router.get("/preferences", response_model=ChartPreferencesResponse)
async def get_chart_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's chart preferences.

    Returns:
    - Current template (builtin or custom)
    - Saved custom templates
    - Available builtin templates
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[chart_preferences] GET preferences for user_id={current_user.id}")

    user_prefs = current_user.preferences or {}
    logger.info(f"[chart_preferences] user.preferences from DB: {user_prefs}")

    chart_prefs = user_prefs.get("chart_preferences", {})
    logger.info(f"[chart_preferences] chart_preferences: {chart_prefs}")

    # Default to plotly_white if not set
    chart_template = chart_prefs.get("chart_template", {
        "type": "builtin",
        "name": "plotly_white",
        "custom_definition": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    })

    logger.info(f"[chart_preferences] Returning chart_template: {chart_template}")

    saved_templates = chart_prefs.get("saved_templates", [])

    return {
        "chart_template": chart_template,
        "saved_templates": saved_templates,
        "available_builtin_templates": BUILTIN_PLOTLY_TEMPLATES
    }


@router.put("/preferences", response_model=ChartPreferencesResponse)
async def update_chart_preferences(
    request: UpdateChartPreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's chart template preference.
    """
    import logging
    from sqlalchemy import update
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[chart_preferences] Updating preferences for user_id={current_user.id}")
        logger.info(f"[chart_preferences] Request: type={request.chart_template.type}, name={request.chart_template.name}")

        # Get current preferences
        user_prefs = current_user.preferences or {}
        logger.info(f"[chart_preferences] Current preferences: {user_prefs}")

        chart_prefs = user_prefs.get("chart_preferences", {})

        # Update chart template (use mode='json' to serialize datetime objects)
        chart_template_dict = request.chart_template.model_dump(mode='json')
        chart_template_dict["updated_at"] = datetime.utcnow().isoformat()
        chart_prefs["chart_template"] = chart_template_dict

        logger.info(f"[chart_preferences] Updated chart_template: {chart_template_dict}")

        # Save using UPDATE statement (more reliable with async)
        user_prefs["chart_preferences"] = chart_prefs

        stmt = update(User).where(User.id == current_user.id).values(preferences=user_prefs)
        await db.execute(stmt)
        await db.commit()

        logger.info(f"[chart_preferences] Committed successfully")

        # Return updated preferences
        return {
            "chart_template": chart_prefs["chart_template"],
            "saved_templates": chart_prefs.get("saved_templates", []),
            "available_builtin_templates": BUILTIN_PLOTLY_TEMPLATES
        }

    except Exception as e:
        logger.error(f"[chart_preferences] ERROR updating preferences: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.post("/templates", response_model=SavedTemplate)
async def save_custom_template(
    request: SaveTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a custom template for reuse.
    """
    from sqlalchemy import update

    try:
        # Get current preferences
        user_prefs = current_user.preferences or {}
        chart_prefs = user_prefs.get("chart_preferences", {})
        saved_templates = chart_prefs.get("saved_templates", [])

        # Create new template
        now = datetime.utcnow()
        new_template = {
            "id": f"template_{uuid.uuid4().hex[:8]}",
            "name": request.name,
            "description": request.description,
            "template_definition": request.template_definition.model_dump(mode='json'),
            "thumbnail": request.thumbnail,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        # Add to saved templates
        saved_templates.append(new_template)
        chart_prefs["saved_templates"] = saved_templates
        user_prefs["chart_preferences"] = chart_prefs

        # Save using UPDATE statement
        stmt = update(User).where(User.id == current_user.id).values(preferences=user_prefs)
        await db.execute(stmt)
        await db.commit()

        return new_template

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")


@router.put("/templates/{template_id}", response_model=SavedTemplate)
async def update_custom_template(
    template_id: str,
    request: SaveTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a saved custom template.
    """
    from sqlalchemy import update

    try:
        # Get current preferences
        user_prefs = current_user.preferences or {}
        chart_prefs = user_prefs.get("chart_preferences", {})
        saved_templates = chart_prefs.get("saved_templates", [])

        # Find and update the template
        template_found = False
        for template in saved_templates:
            if template["id"] == template_id:
                template_found = True
                template["name"] = request.name
                template["description"] = request.description
                template["template_definition"] = request.template_definition.model_dump(mode='json')
                template["thumbnail"] = request.thumbnail
                template["updated_at"] = datetime.utcnow().isoformat()
                updated_template = template
                break

        if not template_found:
            raise HTTPException(status_code=404, detail="Template not found")

        chart_prefs["saved_templates"] = saved_templates
        user_prefs["chart_preferences"] = chart_prefs

        # Save using UPDATE statement
        stmt = update(User).where(User.id == current_user.id).values(preferences=user_prefs)
        await db.execute(stmt)
        await db.commit()

        return updated_template

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_custom_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a saved custom template.
    """
    from sqlalchemy import update

    try:
        # Get current preferences
        user_prefs = current_user.preferences or {}
        chart_prefs = user_prefs.get("chart_preferences", {})
        saved_templates = chart_prefs.get("saved_templates", [])

        # Filter out the template
        saved_templates = [t for t in saved_templates if t["id"] != template_id]
        chart_prefs["saved_templates"] = saved_templates
        user_prefs["chart_preferences"] = chart_prefs

        # Save using UPDATE statement
        stmt = update(User).where(User.id == current_user.id).values(preferences=user_prefs)
        await db.execute(stmt)
        await db.commit()

        return {"message": "Template deleted successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")
