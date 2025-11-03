"""
User model for authentication and user management.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    department = Column(String(100))

    # Authorization
    role = Column(String(50), default="user")  # admin, analyst, viewer, user
    permissions = Column(JSON, default={})
    preferences = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
