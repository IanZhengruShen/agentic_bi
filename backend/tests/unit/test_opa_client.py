"""
Unit tests for OPA client.

Tests the OPA client with mocked HTTP responses.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
import httpx

from app.services.opa_client import OPAClient


@pytest.fixture
def opa_client():
    """Create OPA client instance."""
    return OPAClient(opa_url="http://test-opa:8181", timeout=5)


@pytest.mark.asyncio
class TestOPAClientPermissionCheck:
    """Test permission checking functionality."""

    async def test_check_permission_allowed(self, opa_client):
        """Test permission check returns True when allowed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Mock OPA enabled
            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                result = await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="analyst",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                assert result is True
                mock_client.post.assert_called_once()

    async def test_check_permission_denied(self, opa_client):
        """Test permission check returns False when denied."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": False}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                result = await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="user",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                assert result is False

    async def test_check_permission_opa_error(self, opa_client):
        """Test permission check returns False on OPA error (fail-closed)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                result = await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="user",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                # Should fail-closed (deny access on error)
                assert result is False

    async def test_check_permission_timeout(self, opa_client):
        """Test permission check returns False on timeout."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                result = await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="user",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                # Should fail-closed (deny access on timeout)
                assert result is False

    async def test_check_permission_network_error(self, opa_client):
        """Test permission check returns False on network error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                result = await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="user",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                # Should fail-closed (deny access on network error)
                assert result is False


@pytest.mark.asyncio
class TestOPAClientFallbackLogic:
    """Test fallback logic when OPA is disabled."""

    async def test_fallback_admin_allowed(self, opa_client):
        """Test admin is allowed everything when OPA disabled."""
        with patch('app.services.opa_client.settings.opa.opa_enabled', False):
            result = await opa_client.check_permission(
                user_id="admin-123",
                company_id="company-123",
                role="admin",
                action="read",
                resource_type="database",
                resource_data={"database_name": "any_db"}
            )

            assert result is True

    async def test_fallback_analyst_read_allowed(self, opa_client):
        """Test analyst can read when OPA disabled."""
        with patch('app.services.opa_client.settings.opa.opa_enabled', False):
            result = await opa_client.check_permission(
                user_id="analyst-123",
                company_id="company-123",
                role="analyst",
                action="read",
                resource_type="database",
                resource_data={"database_name": "chinook"}
            )

            assert result is True

    async def test_fallback_user_read_allowed(self, opa_client):
        """Test user can read when OPA disabled."""
        with patch('app.services.opa_client.settings.opa.opa_enabled', False):
            result = await opa_client.check_permission(
                user_id="user-123",
                company_id="company-123",
                role="user",
                action="read",
                resource_type="database",
                resource_data={"database_name": "chinook"}
            )

            assert result is True

    async def test_fallback_user_create_denied(self, opa_client):
        """Test user cannot create when OPA disabled."""
        with patch('app.services.opa_client.settings.opa.opa_enabled', False):
            result = await opa_client.check_permission(
                user_id="user-123",
                company_id="company-123",
                role="user",
                action="create",
                resource_type="database",
                resource_data={"database_name": "new_db"}
            )

            assert result is False


@pytest.mark.asyncio
class TestOPAClientRaiseOnDeny:
    """Test check_permission_or_raise functionality."""

    async def test_check_permission_or_raise_allowed(self, opa_client):
        """Test no exception raised when permission allowed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                # Should not raise
                await opa_client.check_permission_or_raise(
                    user_id="user-123",
                    company_id="company-123",
                    role="analyst",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

    async def test_check_permission_or_raise_denied(self, opa_client):
        """Test HTTPException raised when permission denied."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": False}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                with pytest.raises(HTTPException) as exc_info:
                    await opa_client.check_permission_or_raise(
                        user_id="user-123",
                        company_id="company-123",
                        role="user",
                        action="read",
                        resource_type="database",
                        resource_data={"database_name": "chinook"}
                    )

                assert exc_info.value.status_code == 403
                assert "Permission denied" in exc_info.value.detail


@pytest.mark.asyncio
class TestOPAClientHealthCheck:
    """Test OPA health check functionality."""

    async def test_health_check_healthy(self, opa_client):
        """Test health check returns True when OPA is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await opa_client.health_check()
            assert result is True

    async def test_health_check_unhealthy(self, opa_client):
        """Test health check returns False when OPA is unhealthy."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await opa_client.health_check()
            assert result is False

    async def test_health_check_unreachable(self, opa_client):
        """Test health check returns False when OPA is unreachable."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            result = await opa_client.health_check()
            assert result is False


@pytest.mark.asyncio
class TestOPARequestFormat:
    """Test OPA request payload format."""

    async def test_request_payload_structure(self, opa_client):
        """Test OPA request has correct structure."""
        expected_payload = {
            "input": {
                "user": {
                    "id": "user-123",
                    "company_id": "company-123",
                    "role": "analyst"
                },
                "action": "read",
                "resource": {
                    "type": "database",
                    "data": {"database_name": "chinook"}
                }
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="analyst",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                # Verify the payload structure
                call_args = mock_client.post.call_args
                assert call_args is not None
                actual_payload = call_args.kwargs['json']
                assert actual_payload == expected_payload

    async def test_request_endpoint_format(self, opa_client):
        """Test OPA request goes to correct endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch('app.services.opa_client.settings.opa.opa_enabled', True):
                await opa_client.check_permission(
                    user_id="user-123",
                    company_id="company-123",
                    role="analyst",
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": "chinook"}
                )

                # Verify endpoint URL
                call_args = mock_client.post.call_args
                assert call_args is not None
                actual_url = call_args.args[0]
                assert actual_url == "http://test-opa:8181/v1/data/app/rbac/allow"
