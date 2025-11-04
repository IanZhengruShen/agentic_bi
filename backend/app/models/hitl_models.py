"""
HITL (Human-in-the-Loop) database models for persistent storage.

This module provides SQLAlchemy models for storing HITL requests and responses,
enabling persistence across restarts, audit trails, and analytics.
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import uuid

from app.db.base import Base


class HITLRequest(Base):
    """
    HITL Request model for persistent storage of human intervention requests.

    Stores all details about intervention requests including context, options,
    timing, and status. Supports multi-tenant architecture with company_id.
    """

    __tablename__ = "hitl_requests"

    # Primary keys
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), unique=True, nullable=False, index=True)

    # Workflow context
    workflow_id = Column(String(255), nullable=False, index=True)
    conversation_id = Column(String(255), nullable=True)

    # Request details
    intervention_type = Column(String(100), nullable=False, index=True)
    context = Column(JSONB, nullable=False, default={})
    options = Column(JSONB, nullable=False, default=[])

    # User context (multi-tenancy)
    requester_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Status tracking
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, approved, rejected, modified, timeout, cancelled

    # Timing
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    timeout_at = Column(DateTime, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Flags
    required = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    requester = relationship("User", foreign_keys=[requester_user_id])
    company = relationship("Company")
    response = relationship(
        "HITLResponse",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Computed property for expiration check
    @property
    def is_expired(self) -> bool:
        """Check if the request has expired based on timeout_at."""
        return datetime.utcnow() > self.timeout_at

    def __repr__(self):
        return (
            f"<HITLRequest(id={self.id}, request_id={self.request_id}, "
            f"type={self.intervention_type}, status={self.status})>"
        )

    def __init__(self, **kwargs):
        """Initialize HITL request and calculate timeout_at if not provided."""
        super().__init__(**kwargs)
        if not self.timeout_at and self.requested_at and self.timeout_seconds:
            self.timeout_at = self.requested_at + timedelta(
                seconds=self.timeout_seconds
            )


# Create indexes for performance
Index("idx_hitl_workflow_status", HITLRequest.workflow_id, HITLRequest.status)
Index("idx_hitl_company_type", HITLRequest.company_id, HITLRequest.intervention_type)
Index("idx_hitl_timeout_at", HITLRequest.timeout_at)


class HITLResponse(Base):
    """
    HITL Response model for persistent storage of human responses.

    Stores the human's decision/feedback for each intervention request,
    including who responded and when.
    """

    __tablename__ = "hitl_responses"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to request (one-to-one)
    request_id = Column(
        String(255),
        ForeignKey("hitl_requests.request_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Response details
    action = Column(
        String(50), nullable=False
    )  # approve, reject, modify, abort
    data = Column(JSONB, nullable=True, default={})
    feedback = Column(Text, nullable=True)
    modified_sql = Column(Text, nullable=True)

    # Responder information
    responder_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responder_name = Column(String(255), nullable=True)
    responder_email = Column(String(255), nullable=True)

    # Timing
    responded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    request = relationship("HITLRequest", back_populates="response")
    responder = relationship("User", foreign_keys=[responder_user_id])

    def __repr__(self):
        return (
            f"<HITLResponse(id={self.id}, request_id={self.request_id}, "
            f"action={self.action})>"
        )


# Create indexes for analytics
Index("idx_hitl_response_responder", HITLResponse.responder_user_id)
Index("idx_hitl_response_responded_at", HITLResponse.responded_at)
