"""
Refresh token model for JWT token management.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class RefreshToken(Base):
    """Refresh token for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Lifecycle
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
