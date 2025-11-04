"""
User API Endpoints.

Provides REST API for user management and preferences.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.deps import get_current_active_user
from app.models import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/users", tags=["users"])


class NotificationPreferences(BaseModel):
    """User notification preferences for HITL."""

    websocket_enabled: bool = True
    email_enabled: bool = False
    slack_enabled: bool = False
    slack_channel: Optional[str] = None
    intervention_types: list[str] = [
        "sql_review",
        "data_modification",
        "high_cost_query",
    ]


class UserProfile(BaseModel):
    """User profile data."""

    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    company_id: Optional[str]
    department: Optional[str]


class UserProfileUpdate(BaseModel):
    """User profile update payload."""

    full_name: Optional[str] = None
    department: Optional[str] = None


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user",
    description="Get details of the currently authenticated user",
)
async def get_current_user_details(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user details.

    **Returns:**
    User object with all fields.
    """
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        company_id=str(current_user.company_id) if current_user.company_id else None,
        department=current_user.department,
    )


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Update user profile",
    description="Update current user's profile information",
)
async def update_user_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user profile information.

    **Note:** Role changes require admin privileges and should use the separate role endpoint.
    """
    logger.info(f"[API:users] User {current_user.id} updating profile")

    try:
        # Update allowed fields
        if profile.full_name is not None:
            current_user.full_name = profile.full_name
        if profile.department is not None:
            current_user.department = profile.department

        await db.commit()
        await db.refresh(current_user)

        logger.info(f"[API:users] Profile updated successfully for user {current_user.id}")

        return UserProfile(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_active=current_user.is_active,
            company_id=str(current_user.company_id) if current_user.company_id else None,
            department=current_user.department,
        )

    except Exception as e:
        logger.error(f"[API:users] Failed to update profile: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}",
        )


@router.get(
    "/me/notification-preferences",
    response_model=NotificationPreferences,
    summary="Get notification preferences",
    description="Get user's notification preferences for HITL",
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get user's notification preferences.

    **Returns:**
    NotificationPreferences object with all settings.
    """
    logger.info(f"[API:users] User {current_user.id} getting notification preferences")

    # Return user's preferences from database
    # For now, return default preferences (can be enhanced to store in DB)
    prefs = current_user.notification_preferences or {}

    return NotificationPreferences(
        websocket_enabled=prefs.get("websocket_enabled", True),
        email_enabled=prefs.get("email_enabled", False),
        slack_enabled=prefs.get("slack_enabled", False),
        slack_channel=prefs.get("slack_channel"),
        intervention_types=prefs.get(
            "intervention_types",
            ["sql_review", "data_modification", "high_cost_query"],
        ),
    )


@router.put(
    "/me/notification-preferences",
    response_model=NotificationPreferences,
    summary="Update notification preferences",
    description="Update user's notification preferences for HITL",
)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user's notification preferences.

    **Request Body:**
    NotificationPreferences object with all settings.

    **Returns:**
    Updated NotificationPreferences.
    """
    logger.info(
        f"[API:users] User {current_user.id} updating notification preferences"
    )

    try:
        # Update user's preferences in database
        current_user.notification_preferences = preferences.model_dump()
        await db.commit()
        await db.refresh(current_user)

        logger.info(f"[API:users] Preferences updated successfully for user {current_user.id}")

        return preferences

    except Exception as e:
        logger.error(f"[API:users] Failed to update preferences: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}",
        )


class RoleUpdateRequest(BaseModel):
    """Request to update user role."""

    user_id: str
    new_role: str  # admin, analyst, viewer, user


@router.put(
    "/role",
    summary="Update user role (Admin only)",
    description="Update a user's role. Requires admin privileges.",
)
async def update_user_role(
    request: RoleUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user's role.

    **Authorization:** Only admins can change user roles.

    **Valid Roles:**
    - admin: Full system access
    - analyst: Can create and analyze queries
    - viewer: Read-only access
    - user: Standard user access
    """
    # Check if current user is admin
    if current_user.role != "admin":
        logger.warning(
            f"[API:users] Non-admin user {current_user.id} attempted to change role"
        )
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user roles",
        )

    # Validate role
    valid_roles = ["admin", "analyst", "viewer", "user"]
    if request.new_role not in valid_roles:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    logger.info(
        f"[API:users] Admin {current_user.id} updating role for user {request.user_id} to {request.new_role}"
    )

    try:
        from sqlalchemy import select

        # Fetch target user
        stmt = select(User).where(User.id == uuid.UUID(request.user_id))
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found",
            )

        # Prevent self-demotion from admin (safety measure)
        if target_user.id == current_user.id and request.new_role != "admin":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from admin role",
            )

        # Update role
        old_role = target_user.role
        target_user.role = request.new_role

        await db.commit()
        await db.refresh(target_user)

        logger.info(
            f"[API:users] Role updated successfully: user={request.user_id}, "
            f"old_role={old_role}, new_role={request.new_role}"
        )

        return {
            "success": True,
            "message": f"User role updated from {old_role} to {request.new_role}",
            "user_id": str(target_user.id),
            "new_role": target_user.role,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:users] Failed to update role: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}",
        )
