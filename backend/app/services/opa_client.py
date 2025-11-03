"""
HTTP client for external OPA authorization service.

NOTE: This client calls an EXTERNAL OPA service. Policy management
is handled by that external service, not by this application.
"""
import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class OPAClient:
    """
    Client for calling external OPA authorization service.

    The OPA service is expected to have policies already configured
    for the Agentic BI platform. This client just sends authorization
    requests and receives allow/deny decisions.
    """

    def __init__(self, opa_url: str = None, timeout: int = None):
        self.opa_url = (opa_url or settings.OPA_URL).rstrip("/")
        self.timeout = timeout or settings.OPA_TIMEOUT

    async def check_permission(
        self,
        user_id: str,
        company_id: Optional[str],
        role: str,
        action: str,
        resource_type: str,
        resource_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if user has permission to perform action on resource.

        Calls external OPA service with authorization query.

        Args:
            user_id: User UUID string
            company_id: Company UUID string (optional)
            role: User role (admin, analyst, viewer, user)
            action: Action to perform (read, write, delete, execute, etc.)
            resource_type: Type of resource (query, visualization, session, etc.)
            resource_data: Additional resource context (optional)

        Returns:
            bool: True if allowed, False if denied
        """
        # Build OPA input payload
        opa_input = {
            "input": {
                "user": {
                    "id": user_id,
                    "company_id": company_id,
                    "role": role
                },
                "action": action,
                "resource": {
                    "type": resource_type,
                    "data": resource_data or {}
                }
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                # Call external OPA service
                # Adjust the path based on your OPA policy structure
                response = await client.post(
                    f"{self.opa_url}/v1/data/agentic_bi/allow",
                    json=opa_input,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logger.error(
                        f"OPA authorization check failed: {response.status_code} - {response.text}"
                    )
                    # Fail closed - deny access on OPA errors
                    return False

                result = response.json()
                # OPA returns {"result": true/false}
                return result.get("result", False)

        except httpx.TimeoutException:
            logger.error(f"OPA request timeout after {self.timeout}s")
            # Fail closed - deny access on timeout
            return False

        except Exception as e:
            logger.error(f"OPA request error: {str(e)}")
            # Fail closed - deny access on errors
            return False

    async def check_permission_or_raise(
        self,
        user_id: str,
        company_id: Optional[str],
        role: str,
        action: str,
        resource_type: str,
        resource_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Check permission and raise HTTPException if denied.

        Convenience method for use in API endpoints.

        Args:
            Same as check_permission

        Raises:
            HTTPException: If permission is denied
        """
        allowed = await self.check_permission(
            user_id, company_id, role, action, resource_type, resource_data
        )

        if not allowed:
            logger.warning(
                f"Authorization denied - User: {user_id}, Action: {action}, Resource: {resource_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {resource_type}"
            )

    async def health_check(self) -> bool:
        """
        Check if OPA service is reachable.

        Returns:
            bool: True if OPA service responds, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opa_url}/health",
                    timeout=2
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OPA health check failed: {str(e)}")
            return False


# Global OPA client instance
opa_client = OPAClient()
