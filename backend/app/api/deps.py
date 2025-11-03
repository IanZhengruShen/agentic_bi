"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import uuid

from app.db.session import get_db
from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.services.opa_client import opa_client
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(uuid.UUID(user_id_str))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to get current admin user.

    Args:
        current_user: Current active user

    Returns:
        User: Admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_permission(action: str, resource_type: str, resource_data: Optional[Dict[str, Any]] = None):
    """
    Dependency factory for OPA permission checks.

    Args:
        action: Action to perform (read, write, delete, etc.)
        resource_type: Type of resource (query, visualization, etc.)
        resource_data: Optional resource context

    Returns:
        Dependency function that checks permission

    Usage:
        @app.get("/queries", dependencies=[Depends(require_permission("read", "query"))])
        async def get_queries(...):
            ...
    """
    async def _check_permission(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        await opa_client.check_permission_or_raise(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id) if current_user.company_id else None,
            role=current_user.role,
            action=action,
            resource_type=resource_type,
            resource_data=resource_data
        )
        return current_user

    return _check_permission
