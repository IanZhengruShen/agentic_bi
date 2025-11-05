"""
User Management API

Endpoints for user profile and role management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# Schemas
class UserProfile(BaseModel):
    """User profile response."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    department: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Request to update user profile (non-sensitive fields)."""
    full_name: Optional[str] = None
    department: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    """Request to update user role (admin only)."""
    new_role: str = Field(..., description="New role: admin, analyst, viewer, or user")


class RoleUpdateResponse(BaseModel):
    """Response after role update."""
    success: bool
    message: str
    user_id: str
    new_role: str


class PasswordChangeRequest(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# Endpoints

@router.get("/me", response_model=UserProfile)
async def get_current_user_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile.

    Returns full user profile including role, email, department, company, etc.
    """
    # Fetch company name if user has a company
    company_name = None
    if current_user.company_id:
        from app.models.company import Company
        company_result = await db.execute(
            select(Company).where(Company.id == current_user.company_id)
        )
        company = company_result.scalar_one_or_none()
        if company:
            company_name = company.name

    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        company_id=str(current_user.company_id) if current_user.company_id else None,
        company_name=company_name,
        department=current_user.department,
    )


@router.put("/me", response_model=UserProfile)
async def update_user_profile(
    profile: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile (non-sensitive fields).

    Users can update their own full_name and department.
    Role changes require admin privileges (use /users/role endpoint).
    """
    try:
        # Update user fields
        if profile.full_name is not None:
            current_user.full_name = profile.full_name
        if profile.department is not None:
            current_user.department = profile.department

        await db.commit()
        await db.refresh(current_user)

        logger.info(f"User profile updated: user_id={current_user.id}")

        # Fetch company name
        company_name = None
        if current_user.company_id:
            from app.models.company import Company
            company_result = await db.execute(
                select(Company).where(Company.id == current_user.company_id)
            )
            company = company_result.scalar_one_or_none()
            if company:
                company_name = company.name

        return UserProfile(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_active=current_user.is_active,
            company_id=str(current_user.company_id) if current_user.company_id else None,
            company_name=company_name,
            department=current_user.department,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update user profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get("/", response_model=list[UserProfile], summary="List company users (Admin only)")
async def list_company_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all users in the current user's company (admin only).

    Authorization: Only admins can list users.
    Returns: All active users in the same company.
    """
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list users",
        )

    # Check if user has a company
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with any company",
        )

    try:
        # Get company name
        from app.models.company import Company
        company_result = await db.execute(
            select(Company).where(Company.id == current_user.company_id)
        )
        company = company_result.scalar_one_or_none()
        company_name = company.name if company else None

        # Get all users in the same company
        stmt = select(User).where(
            User.company_id == current_user.company_id,
            User.is_active == True
        )
        result = await db.execute(stmt)
        users = result.scalars().all()

        logger.info(f"Listed {len(users)} users for company {current_user.company_id}")

        return [
            UserProfile(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                company_id=str(user.company_id) if user.company_id else None,
                company_name=company_name,
                department=user.department,
            )
            for user in users
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.put("/{user_id}/role", response_model=RoleUpdateResponse, summary="Update user role (Admin only)")
async def update_user_role(
    user_id: str,
    request: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user role (admin only).

    Authorization: Only admins can change roles.
    Protection: Prevents self-demotion from admin and cross-company role changes.
    Validation: Only allows valid roles (admin, analyst, viewer, user).
    """
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user roles",
        )

    # Validate role
    valid_roles = ["admin", "analyst", "viewer", "user"]
    if request.new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    try:
        # Get target user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Security: Prevent cross-company role changes
        if target_user.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot manage users from other companies",
            )

        # Handle orphan users (users without company)
        if target_user.company_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change role of user without company",
            )

        # Prevent self-demotion from admin
        if target_user.id == current_user.id and request.new_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from admin role",
            )

        # Update role
        old_role = target_user.role
        target_user.role = request.new_role
        await db.commit()

        logger.info(
            f"User role updated: user_id={target_user.id}, "
            f"old_role={old_role}, new_role={request.new_role}, "
            f"updated_by={current_user.id}"
        )

        return RoleUpdateResponse(
            success=True,
            message=f"Role updated successfully from {old_role} to {request.new_role}",
            user_id=str(target_user.id),
            new_role=request.new_role,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update user role: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )


@router.put("/me/password")
async def change_password(
    request: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change user password.

    Requires current password for verification.
    New password must be at least 8 characters.
    """
    from app.core.security import verify_password, get_password_hash

    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    try:
        # Update password
        current_user.password_hash = get_password_hash(request.new_password)
        await db.commit()

        logger.info(f"Password changed: user_id={current_user.id}")

        return {"message": "Password changed successfully"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to change password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )
