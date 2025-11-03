"""
Authentication service for user management and JWT tokens.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime, timedelta
import uuid

from app.models.user import User
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.schemas.user import UserCreate, TokenResponse
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    validate_password_strength,
)
from app.core.config import settings


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email address

        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user and optionally a company.

        Args:
            user_data: User creation data

        Returns:
            Created User

        Raises:
            HTTPException: If password is weak or email already exists
        """
        # Validate password
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check if user exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create company if provided
        company = None
        if user_data.company_name:
            company = Company(
                name=user_data.company_name,
                domain=user_data.email.split("@")[1] if "@" in user_data.email else None
            )
            self.db.add(company)
            await self.db.flush()

        # Create user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            department=user_data.department,
            company_id=company.id if company else None,
            role="admin" if company else "user"  # First user in company is admin
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    async def create_user_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for user.

        Args:
            user: User to create tokens for

        Returns:
            TokenResponse with access and refresh tokens
        """
        # Create access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "company_id": str(user.company_id) if user.company_id else None
            }
        )

        # Create refresh token
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Store refresh token hash
        token_hash = hash_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.jwt.jwt_refresh_expiration_days)

        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(db_refresh_token)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt.jwt_expiration_minutes * 60
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Create new access token using refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            TokenResponse with new tokens

        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Decode refresh token
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Verify token in database
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_active == True,
                RefreshToken.expires_at > datetime.utcnow()
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked"
            )

        # Get user
        user = await self.get_user_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new tokens
        return await self.create_user_tokens(user)

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """
        Revoke a refresh token.

        Args:
            refresh_token: Refresh token to revoke
        """
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        db_token = result.scalar_one_or_none()

        if db_token:
            db_token.is_active = False
            db_token.revoked_at = datetime.utcnow()
            await self.db.commit()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User UUID
        """
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.commit()

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password.

        Args:
            user_id: User UUID
            current_password: Current password (for verification)
            new_password: New password

        Raises:
            HTTPException: If current password is incorrect or new password is weak
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Update password
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
