"""
Company model for multi-tenancy.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Company(Base):
    """Company/Organization model for multi-tenant architecture."""

    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, index=True)
    logo_url = Column(String(500))

    # Configuration
    settings = Column(JSON, default={}, nullable=False)
    style_config = Column(JSON, default={})

    # Subscription
    subscription_tier = Column(String(50), default="free")
    subscription_expires_at = Column(DateTime, nullable=True)
    user_limit = Column(Integer, default=10)
    query_limit_monthly = Column(Integer, default=1000)
    storage_limit_gb = Column(Integer, default=10)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="company")

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name})>"
