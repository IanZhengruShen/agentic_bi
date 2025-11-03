"""
User schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None
    department: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100, description="User password (min 8 characters)")
    company_name: Optional[str] = Field(None, description="Company name (creates new company if provided)")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID4
    company_id: Optional[UUID4] = None
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
