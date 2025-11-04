"""
HITL Repository for database operations.

Provides CRUD operations and queries for HITL requests and responses.
Handles persistence, retrieval, updates, and cleanup of HITL data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hitl_models import HITLRequest, HITLResponse

logger = logging.getLogger(__name__)


class HITLRepository:
    """
    Repository for HITL database operations.

    Provides data access methods for HITL requests and responses,
    with support for querying, filtering, and cleanup operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # ==================== HITLRequest CRUD ====================

    async def create_request(
        self,
        workflow_id: str,
        intervention_type: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        timeout_seconds: int = 300,
        conversation_id: Optional[str] = None,
        requester_user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        required: bool = True,
    ) -> HITLRequest:
        """
        Create a new HITL request.

        Args:
            workflow_id: Workflow identifier
            intervention_type: Type of intervention
            context: Context data for the intervention
            options: List of available options
            timeout_seconds: Timeout in seconds
            conversation_id: Optional conversation ID
            requester_user_id: Optional requester user ID
            company_id: Optional company ID
            required: Whether intervention is required

        Returns:
            Created HITLRequest instance
        """
        request_id = str(uuid4())
        requested_at = datetime.utcnow()
        timeout_at = requested_at + timedelta(seconds=timeout_seconds)

        request = HITLRequest(
            request_id=request_id,
            workflow_id=workflow_id,
            conversation_id=conversation_id,
            intervention_type=intervention_type,
            context=context,
            options=options,
            requester_user_id=requester_user_id,
            company_id=company_id,
            status="pending",
            requested_at=requested_at,
            timeout_seconds=timeout_seconds,
            timeout_at=timeout_at,
            required=required,
        )

        self.session.add(request)
        await self.session.flush()

        logger.info(
            f"Created HITL request {request_id} for workflow {workflow_id}: "
            f"{intervention_type} (timeout: {timeout_seconds}s)"
        )

        return request

    async def get_request(
        self, request_id: str, include_response: bool = False
    ) -> Optional[HITLRequest]:
        """
        Get HITL request by ID.

        Args:
            request_id: Request identifier
            include_response: Whether to eagerly load the response

        Returns:
            HITLRequest if found, None otherwise
        """
        query = select(HITLRequest).where(HITLRequest.request_id == request_id)

        if include_response:
            query = query.options(selectinload(HITLRequest.response))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_requests(
        self, workflow_id: str, include_expired: bool = False
    ) -> List[HITLRequest]:
        """
        Get pending requests for a workflow.

        Args:
            workflow_id: Workflow identifier
            include_expired: Whether to include expired requests

        Returns:
            List of pending HITLRequest instances
        """
        query = select(HITLRequest).where(
            and_(
                HITLRequest.workflow_id == workflow_id,
                HITLRequest.status == "pending",
            )
        )

        if not include_expired:
            query = query.where(HITLRequest.timeout_at > datetime.utcnow())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_requests_by_status(
        self,
        status: str,
        company_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[HITLRequest]:
        """
        Get requests by status, optionally filtered by company.

        Args:
            status: Request status
            company_id: Optional company ID filter
            limit: Maximum number of requests to return

        Returns:
            List of HITLRequest instances
        """
        query = select(HITLRequest).where(HITLRequest.status == status)

        if company_id:
            query = query.where(HITLRequest.company_id == company_id)

        query = query.order_by(HITLRequest.requested_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired_requests(self, limit: int = 100) -> List[HITLRequest]:
        """
        Get expired pending requests that need timeout handling.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of expired HITLRequest instances
        """
        query = (
            select(HITLRequest)
            .where(
                and_(
                    HITLRequest.status == "pending",
                    HITLRequest.timeout_at <= datetime.utcnow(),
                )
            )
            .order_by(HITLRequest.timeout_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_request_status(
        self,
        request_id: str,
        status: str,
        responded_at: Optional[datetime] = None,
        response_time_ms: Optional[int] = None,
    ) -> bool:
        """
        Update request status and response timing.

        Args:
            request_id: Request identifier
            status: New status
            responded_at: Optional response timestamp
            response_time_ms: Optional response time in milliseconds

        Returns:
            True if updated, False if not found
        """
        update_data = {"status": status, "updated_at": datetime.utcnow()}

        if responded_at:
            update_data["responded_at"] = responded_at

        if response_time_ms is not None:
            update_data["response_time_ms"] = response_time_ms

        stmt = (
            update(HITLRequest)
            .where(HITLRequest.request_id == request_id)
            .values(**update_data)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        success = result.rowcount > 0

        if success:
            logger.info(f"Updated HITL request {request_id} status to {status}")
        else:
            logger.warning(f"Failed to update HITL request {request_id}: not found")

        return success

    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.

        Args:
            request_id: Request identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        return await self.update_request_status(request_id, "cancelled")

    # ==================== HITLResponse CRUD ====================

    async def create_response(
        self,
        request_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
        modified_sql: Optional[str] = None,
        responder_user_id: Optional[str] = None,
        responder_name: Optional[str] = None,
        responder_email: Optional[str] = None,
    ) -> HITLResponse:
        """
        Create a response to a HITL request.

        Args:
            request_id: Request identifier
            action: Action taken (approve, reject, modify, abort)
            data: Optional additional data
            feedback: Optional feedback text
            modified_sql: Optional modified SQL
            responder_user_id: Optional responder user ID
            responder_name: Optional responder name
            responder_email: Optional responder email

        Returns:
            Created HITLResponse instance
        """
        response = HITLResponse(
            request_id=request_id,
            action=action,
            data=data or {},
            feedback=feedback,
            modified_sql=modified_sql,
            responder_user_id=responder_user_id,
            responder_name=responder_name,
            responder_email=responder_email,
        )

        self.session.add(response)
        await self.session.flush()

        logger.info(f"Created HITL response for request {request_id}: {action}")

        return response

    async def get_response(self, request_id: str) -> Optional[HITLResponse]:
        """
        Get response by request ID.

        Args:
            request_id: Request identifier

        Returns:
            HITLResponse if found, None otherwise
        """
        query = select(HITLResponse).where(HITLResponse.request_id == request_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_responses_by_user(
        self, user_id: str, limit: int = 100
    ) -> List[HITLResponse]:
        """
        Get responses by user ID.

        Args:
            user_id: User identifier
            limit: Maximum number of responses to return

        Returns:
            List of HITLResponse instances
        """
        query = (
            select(HITLResponse)
            .where(HITLResponse.responder_user_id == user_id)
            .order_by(HITLResponse.responded_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==================== Cleanup Operations ====================

    async def cleanup_old_requests(
        self, days: int = 90, batch_size: int = 100
    ) -> int:
        """
        Delete requests older than specified days.

        Args:
            days: Number of days to retain
            batch_size: Maximum number of requests to delete

        Returns:
            Number of requests deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            delete(HITLRequest)
            .where(HITLRequest.created_at < cutoff_date)
            .execution_options(synchronize_session=False)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} HITL requests older than {days} days"
            )

        return deleted_count

    # ==================== Query/Analytics Operations ====================

    async def get_requests_by_type(
        self,
        intervention_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        company_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[HITLRequest]:
        """
        Get requests by intervention type with optional filters.

        Args:
            intervention_type: Intervention type
            start_date: Optional start date filter
            end_date: Optional end date filter
            company_id: Optional company ID filter
            limit: Maximum number of requests to return

        Returns:
            List of HITLRequest instances
        """
        conditions = [HITLRequest.intervention_type == intervention_type]

        if start_date:
            conditions.append(HITLRequest.requested_at >= start_date)

        if end_date:
            conditions.append(HITLRequest.requested_at <= end_date)

        if company_id:
            conditions.append(HITLRequest.company_id == company_id)

        query = (
            select(HITLRequest)
            .where(and_(*conditions))
            .order_by(HITLRequest.requested_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_workflow_history(
        self, workflow_id: str, include_responses: bool = True
    ) -> List[HITLRequest]:
        """
        Get all HITL requests for a workflow (audit trail).

        Args:
            workflow_id: Workflow identifier
            include_responses: Whether to eagerly load responses

        Returns:
            List of HITLRequest instances ordered by requested_at
        """
        query = select(HITLRequest).where(HITLRequest.workflow_id == workflow_id)

        if include_responses:
            query = query.options(selectinload(HITLRequest.response))

        query = query.order_by(HITLRequest.requested_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
