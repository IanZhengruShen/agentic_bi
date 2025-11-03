"""
Custom Style Profiles API Endpoints

REST API for managing custom style profiles and company branding.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.base import get_db
from app.models.user import User
from app.models.visualization_models import CustomStyleProfile
from app.schemas.visualization_schemas import (
    CustomStyleProfileCreate,
    CustomStyleProfileUpdate,
    CustomStyleProfileResponse,
    CustomStyleProfileListResponse,
    LogoUploadResponse,
)
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/style-profiles", tags=["style-profiles"])


@router.post("/", response_model=CustomStyleProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_style_profile(
    request: CustomStyleProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create custom style profile for company branding.

    Features:
    - Custom color palettes
    - Company logos
    - Typography settings
    - Layout configuration
    - Watermarks
    - Advanced Plotly customizations

    Args:
        request: Style profile creation request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created CustomStyleProfileResponse
    """
    logger.info(f"Creating style profile: {request.name}")

    try:
        # If setting as default, unset other defaults first
        if request.is_default:
            db.query(CustomStyleProfile).filter(
                CustomStyleProfile.company_id == current_user.company_id,
                CustomStyleProfile.is_default == True
            ).update({"is_default": False})

        # Create profile
        profile = CustomStyleProfile(
            company_id=current_user.company_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            is_default=request.is_default,
            is_public=request.is_public,
            base_theme=request.base_theme,
            color_palette=request.color_palette,
            background_color=request.background_color,
            text_color=request.text_color,
            grid_color=request.grid_color,
            font_family=request.font_family,
            font_size=request.font_size,
            title_font_size=request.title_font_size,
            margin_config=request.margin_config,
            logo_url=request.logo_url,
            logo_position=request.logo_position,
            logo_size=request.logo_size,
            watermark_text=request.watermark_text,
            advanced_config=request.advanced_config,
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        logger.info(f"Style profile {profile.id} created successfully")

        return CustomStyleProfileResponse(
            id=str(profile.id),
            company_id=str(profile.company_id),
            user_id=str(profile.user_id),
            name=profile.name,
            description=profile.description,
            is_default=profile.is_default,
            is_public=profile.is_public,
            base_theme=profile.base_theme,
            color_palette=profile.color_palette,
            background_color=profile.background_color,
            text_color=profile.text_color,
            grid_color=profile.grid_color,
            font_family=profile.font_family,
            font_size=profile.font_size,
            title_font_size=profile.title_font_size,
            margin_config=profile.margin_config,
            logo_url=profile.logo_url,
            logo_position=profile.logo_position,
            logo_size=profile.logo_size,
            watermark_text=profile.watermark_text,
            advanced_config=profile.advanced_config,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    except Exception as e:
        logger.error(f"Failed to create style profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create style profile: {str(e)}"
        )


@router.get("/", response_model=CustomStyleProfileListResponse)
async def list_style_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all accessible style profiles.

    Returns both:
    - Public profiles (shared across company)
    - User's private profiles

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of accessible style profiles
    """
    logger.info(f"Listing style profiles for company {current_user.company_id}")

    try:
        # Fetch public profiles + user's private profiles
        profiles = db.query(CustomStyleProfile).filter(
            and_(
                CustomStyleProfile.company_id == current_user.company_id,
                (CustomStyleProfile.is_public == True) | (CustomStyleProfile.user_id == current_user.id)
            )
        ).order_by(
            CustomStyleProfile.is_default.desc(),
            CustomStyleProfile.created_at.desc()
        ).all()

        # Find company default
        company_default = next((p for p in profiles if p.is_default), None)

        profile_responses = [
            CustomStyleProfileResponse(
                id=str(p.id),
                company_id=str(p.company_id),
                user_id=str(p.user_id),
                name=p.name,
                description=p.description,
                is_default=p.is_default,
                is_public=p.is_public,
                base_theme=p.base_theme,
                color_palette=p.color_palette,
                background_color=p.background_color,
                text_color=p.text_color,
                grid_color=p.grid_color,
                font_family=p.font_family,
                font_size=p.font_size,
                title_font_size=p.title_font_size,
                margin_config=p.margin_config,
                logo_url=p.logo_url,
                logo_position=p.logo_position,
                logo_size=p.logo_size,
                watermark_text=p.watermark_text,
                advanced_config=p.advanced_config,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in profiles
        ]

        default_response = None
        if company_default:
            default_response = next((r for r in profile_responses if r.id == str(company_default.id)), None)

        return CustomStyleProfileListResponse(
            profiles=profile_responses,
            total=len(profile_responses),
            company_default=default_response
        )

    except Exception as e:
        logger.error(f"Failed to list style profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list style profiles: {str(e)}"
        )


@router.get("/{profile_id}", response_model=CustomStyleProfileResponse)
async def get_style_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get style profile by ID.

    Args:
        profile_id: Profile ID
        current_user: Authenticated user
        db: Database session

    Returns:
        CustomStyleProfileResponse
    """
    logger.info(f"Fetching style profile {profile_id}")

    try:
        profile = db.query(CustomStyleProfile).filter(
            CustomStyleProfile.id == UUID(profile_id),
            CustomStyleProfile.company_id == current_user.company_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Style profile {profile_id} not found"
            )

        # Check access: must be public or owned by user
        if not profile.is_public and profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private style profile"
            )

        return CustomStyleProfileResponse(
            id=str(profile.id),
            company_id=str(profile.company_id),
            user_id=str(profile.user_id),
            name=profile.name,
            description=profile.description,
            is_default=profile.is_default,
            is_public=profile.is_public,
            base_theme=profile.base_theme,
            color_palette=profile.color_palette,
            background_color=profile.background_color,
            text_color=profile.text_color,
            grid_color=profile.grid_color,
            font_family=profile.font_family,
            font_size=profile.font_size,
            title_font_size=profile.title_font_size,
            margin_config=profile.margin_config,
            logo_url=profile.logo_url,
            logo_position=profile.logo_position,
            logo_size=profile.logo_size,
            watermark_text=profile.watermark_text,
            advanced_config=profile.advanced_config,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch style profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch style profile: {str(e)}"
        )


@router.put("/{profile_id}", response_model=CustomStyleProfileResponse)
async def update_style_profile(
    profile_id: str,
    request: CustomStyleProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update style profile (owner only).

    Args:
        profile_id: Profile ID
        request: Update request
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated CustomStyleProfileResponse
    """
    logger.info(f"Updating style profile {profile_id}")

    try:
        profile = db.query(CustomStyleProfile).filter(
            CustomStyleProfile.id == UUID(profile_id),
            CustomStyleProfile.company_id == current_user.company_id,
            CustomStyleProfile.user_id == current_user.id  # Owner only
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Style profile {profile_id} not found or access denied"
            )

        # If setting as default, unset other defaults
        if request.is_default and not profile.is_default:
            db.query(CustomStyleProfile).filter(
                CustomStyleProfile.company_id == current_user.company_id,
                CustomStyleProfile.is_default == True
            ).update({"is_default": False})

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)

        logger.info(f"Style profile {profile_id} updated successfully")

        return CustomStyleProfileResponse(
            id=str(profile.id),
            company_id=str(profile.company_id),
            user_id=str(profile.user_id),
            name=profile.name,
            description=profile.description,
            is_default=profile.is_default,
            is_public=profile.is_public,
            base_theme=profile.base_theme,
            color_palette=profile.color_palette,
            background_color=profile.background_color,
            text_color=profile.text_color,
            grid_color=profile.grid_color,
            font_family=profile.font_family,
            font_size=profile.font_size,
            title_font_size=profile.title_font_size,
            margin_config=profile.margin_config,
            logo_url=profile.logo_url,
            logo_position=profile.logo_position,
            logo_size=profile.logo_size,
            watermark_text=profile.watermark_text,
            advanced_config=profile.advanced_config,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update style profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update style profile: {str(e)}"
        )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete style profile (owner only).

    Args:
        profile_id: Profile ID
        current_user: Authenticated user
        db: Database session

    Returns:
        204 No Content on success
    """
    logger.info(f"Deleting style profile {profile_id}")

    try:
        profile = db.query(CustomStyleProfile).filter(
            CustomStyleProfile.id == UUID(profile_id),
            CustomStyleProfile.company_id == current_user.company_id,
            CustomStyleProfile.user_id == current_user.id  # Owner only
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Style profile {profile_id} not found or access denied"
            )

        # Don't allow deletion of default profile
        if profile.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default style profile. Set another profile as default first."
            )

        db.delete(profile)
        db.commit()

        logger.info(f"Style profile {profile_id} deleted successfully")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete style profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete style profile: {str(e)}"
        )


@router.post("/{profile_id}/set-default", response_model=CustomStyleProfileResponse)
async def set_default_style_profile(
    profile_id: str,
    current_user: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db),
):
    """
    Set profile as company default (admin only).

    When set as default, all visualizations will use this profile
    unless explicitly overridden.

    Args:
        profile_id: Profile ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated profile as default
    """
    logger.info(f"Setting style profile {profile_id} as company default")

    try:
        profile = db.query(CustomStyleProfile).filter(
            CustomStyleProfile.id == UUID(profile_id),
            CustomStyleProfile.company_id == current_user.company_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Style profile {profile_id} not found"
            )

        # Unset current default
        db.query(CustomStyleProfile).filter(
            CustomStyleProfile.company_id == current_user.company_id,
            CustomStyleProfile.is_default == True
        ).update({"is_default": False})

        # Set new default
        profile.is_default = True
        db.commit()
        db.refresh(profile)

        logger.info(f"Style profile {profile_id} set as company default")

        return CustomStyleProfileResponse(
            id=str(profile.id),
            company_id=str(profile.company_id),
            user_id=str(profile.user_id),
            name=profile.name,
            description=profile.description,
            is_default=profile.is_default,
            is_public=profile.is_public,
            base_theme=profile.base_theme,
            color_palette=profile.color_palette,
            background_color=profile.background_color,
            text_color=profile.text_color,
            grid_color=profile.grid_color,
            font_family=profile.font_family,
            font_size=profile.font_size,
            title_font_size=profile.title_font_size,
            margin_config=profile.margin_config,
            logo_url=profile.logo_url,
            logo_position=profile.logo_position,
            logo_size=profile.logo_size,
            watermark_text=profile.watermark_text,
            advanced_config=profile.advanced_config,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set default style profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default style profile: {str(e)}"
        )


@router.post("/logo/upload", response_model=LogoUploadResponse)
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload company logo.

    Placeholder implementation - stores logo reference.
    In production, this would upload to S3/cloud storage.

    Requirements:
    - Max file size: 2MB
    - Formats: PNG, JPG, SVG
    - Recommended: transparent PNG

    Args:
        file: Uploaded file
        current_user: Authenticated user

    Returns:
        LogoUploadResponse with logo URL
    """
    logger.info(f"Uploading logo: {file.filename}")

    try:
        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/svg+xml"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: PNG, JPG, SVG"
            )

        # Validate file size (2MB max)
        contents = await file.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Max size: 2MB"
            )

        # TODO: Upload to S3/cloud storage
        # For now, return a placeholder URL
        # In production, use boto3 or similar to upload to S3

        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        logo_url = f"https://storage.example.com/{current_user.company_id}/logos/{timestamp}_{file.filename}"

        logger.info(f"Logo uploaded successfully: {logo_url}")

        return LogoUploadResponse(
            logo_url=logo_url,
            file_size=len(contents),
            file_type=file.content_type,
            uploaded_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload logo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload logo: {str(e)}"
        )
