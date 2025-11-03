"""
Company schemas for request/response validation.
"""
from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    """Base company schema."""
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None


class CompanyCreate(CompanyBase):
    """Schema for creating company."""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating company."""
    name: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None
    style_config: Optional[dict] = None


class CompanyResponse(CompanyBase):
    """Schema for company response."""
    id: UUID4
    subscription_tier: str
    user_limit: int
    query_limit_monthly: int
    storage_limit_gb: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
