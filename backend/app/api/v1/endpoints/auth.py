"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
)
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.

    Creates a new user account and optionally a new company if company_name is provided.
    First user in a company is automatically assigned admin role.

    **Args:**
    - email: Valid email address (required)
    - password: Password (min 8 chars, must contain uppercase, lowercase, digit)
    - full_name: User's full name (optional)
    - department: User's department (optional)
    - company_name: Company name (optional, creates new company)

    **Returns:**
    - User object with ID, email, role, etc.
    """
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login - returns JWT access and refresh tokens.

    **Args:**
    - email: User email
    - password: User password

    **Returns:**
    - access_token: JWT access token (24h expiry)
    - refresh_token: JWT refresh token (7d expiry)
    - token_type: "bearer"
    - expires_in: Token expiry in seconds
    """
    auth_service = AuthService(db)

    # Authenticate user
    user = await auth_service.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate tokens
    tokens = await auth_service.create_user_tokens(user)

    # Update last login
    await auth_service.update_last_login(user.id)

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    **Args:**
    - refresh_token: Valid refresh token

    **Returns:**
    - New access and refresh tokens
    """
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_access_token(token_data.refresh_token)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.

    Requires authentication (Bearer token in Authorization header).

    **Returns:**
    - Current user object
    """
    return current_user


@router.post("/logout")
async def logout(
    token_data: TokenRefreshRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by revoking refresh token.

    **Args:**
    - refresh_token: Refresh token to revoke

    **Returns:**
    - Success message
    """
    auth_service = AuthService(db)
    await auth_service.revoke_refresh_token(token_data.refresh_token)
    return {"message": "Successfully logged out"}
