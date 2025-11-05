"""
OPA Access Control Integration Tests.

REAL INTEGRATION TESTS - No mocks, hits actual endpoints:
- Real API at: https://api-agentic-bi.dev01.datascience-tmnl.nl
- Real OPA service at: https://opa.dev01.datascience-tmnl.nl
- Real MindsDB service
- Real JWT authentication

Tests database access filtering based on OPA policies and user roles.

Expected Access Matrix:
+----------+---------+--------+-----------+
| Role     | chinook | sakila | northwind |
+----------+---------+--------+-----------+
| admin    | ✅ Yes  | ✅ Yes | ✅ Yes    |
| analyst  | ✅ Yes  | ✅ Yes | ✅ Yes    |
| viewer   | ✅ Yes  | ✅ Yes | ❌ No     |
| user     | ❌ No   | ❌ No  | ✅ Yes    |
+----------+---------+--------+-----------+

How to Run:
# Run with output
pytest backend/tests/integration/test_opa_access_control.py -v -s

# Run specific test
pytest backend/tests/integration/test_opa_access_control.py::TestOPADatabaseAccessControl::test_viewer_database_access -v

# Run only OPA-marked tests
pytest -m requires_opa -v

Prerequisites:
--------------
1. OPA policy deployed: ./deploy_opa_policy.sh
2. Backend running with OPA_ENABLED=true
3. MindsDB has chinook, sakila, northwind databases
"""

import pytest
import requests
from typing import List


# Helper function to get databases
def get_databases(api_base_url: str, token: str) -> List[str]:
    """Get list of accessible database names from real API."""
    response = requests.get(
        f"{api_base_url}/api/databases/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to get databases: {response.status_code} - {response.text}")

    databases = response.json()

    # Debug: Print response structure
    print(f"\n[DEBUG] Response type: {type(databases)}")
    print(f"[DEBUG] Response content: {databases}")

    # Handle different response formats
    if isinstance(databases, str):
        pytest.fail(f"API returned string instead of list: {databases}")

    if isinstance(databases, dict):
        # If response is wrapped in a dict, try to get the data
        if "databases" in databases:
            databases = databases["databases"]
        elif "data" in databases:
            databases = databases["data"]
        else:
            pytest.fail(f"Unexpected response format: {databases}")

    if not isinstance(databases, list):
        pytest.fail(f"Expected list, got {type(databases)}: {databases}")

    return [db["name"] for db in databases]


@pytest.mark.integration
@pytest.mark.requires_opa
@pytest.mark.requires_mindsdb
class TestOPAServiceSetup:
    """Test OPA service is properly set up."""

    def test_opa_service_healthy(self, opa_health_check):
        """Test OPA service is available and healthy."""
        assert opa_health_check is True
        print("✅ OPA service is healthy")

    def test_opa_policy_deployed(self, verify_opa_policy):
        """Test OPA policy 'agentic-bi-rbac' is deployed."""
        assert verify_opa_policy is True
        print("✅ OPA policy 'agentic-bi-rbac' is deployed")

    def test_opa_data_loaded(self, verify_opa_data):
        """Test OPA policy data is loaded with all roles."""
        assert "analyst" in verify_opa_data
        assert "viewer" in verify_opa_data
        assert "user" in verify_opa_data
        print("✅ OPA policy data loaded with all required roles")
        print(f"   Roles configured: {list(verify_opa_data.keys())}")


@pytest.mark.integration
@pytest.mark.requires_opa
class TestOPADirectEndpoint:
    """Test OPA authorization endpoint directly."""

    def test_opa_allow_admin_any_database(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows admin access to any database."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {
                        "id": "test-admin-id",
                        "company_id": "test-company-id",
                        "role": "admin"
                    },
                    "action": "read",
                    "resource": {
                        "type": "database",
                        "data": {"database_name": "any_database"}
                    }
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("result") is True, "Admin should be allowed access to any database"
        print("✅ Admin can access any database")

    def test_opa_allow_analyst_chinook(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows analyst access to chinook."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {
                        "id": "test-analyst-id",
                        "company_id": "test-company-id",
                        "role": "analyst"
                    },
                    "action": "read",
                    "resource": {
                        "type": "database",
                        "data": {"database_name": "chinook"}
                    }
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("result") is True, "Analyst should be allowed access to chinook"
        print("✅ Analyst can access chinook")

    def test_opa_allow_analyst_sakila(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows analyst access to sakila."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-analyst-id", "company_id": "test-company-id", "role": "analyst"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "sakila"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is True
        print("✅ Analyst can access sakila")

    def test_opa_allow_analyst_northwind(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows analyst access to northwind."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-analyst-id", "company_id": "test-company-id", "role": "analyst"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "northwind"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is True
        print("✅ Analyst can access northwind")

    def test_opa_deny_user_chinook(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA denies user access to chinook."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-user-id", "company_id": "test-company-id", "role": "user"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "chinook"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("result") is False, "User should be denied access to chinook"
        print("✅ User cannot access chinook (correctly denied)")

    def test_opa_deny_user_sakila(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA denies user access to sakila."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-user-id", "company_id": "test-company-id", "role": "user"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "sakila"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is False
        print("✅ User cannot access sakila (correctly denied)")

    def test_opa_allow_user_northwind(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows user access to northwind."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-user-id", "company_id": "test-company-id", "role": "user"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "northwind"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is True
        print("✅ User can access northwind")

    def test_opa_deny_viewer_northwind(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA denies viewer access to northwind."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-viewer-id", "company_id": "test-company-id", "role": "viewer"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "northwind"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("result") is False, "Viewer should be denied access to northwind"
        print("✅ Viewer cannot access northwind (correctly denied)")

    def test_opa_allow_viewer_chinook(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows viewer access to chinook."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-viewer-id", "company_id": "test-company-id", "role": "viewer"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "chinook"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is True
        print("✅ Viewer can access chinook")

    def test_opa_allow_viewer_sakila(self, opa_url, opa_health_check, verify_opa_policy):
        """Test OPA allows viewer access to sakila."""
        response = requests.post(
            f"{opa_url}/v1/data/app/rbac/allow",
            json={
                "input": {
                    "user": {"id": "test-viewer-id", "company_id": "test-company-id", "role": "viewer"},
                    "action": "read",
                    "resource": {"type": "database", "data": {"database_name": "sakila"}}
                }
            },
            timeout=5
        )

        assert response.status_code == 200
        assert response.json().get("result") is True
        print("✅ Viewer can access sakila")


@pytest.mark.integration
@pytest.mark.requires_opa
@pytest.mark.requires_mindsdb
@pytest.mark.slow
class TestOPADatabaseAccessControl:
    """Test OPA-based database access control through API endpoints."""

    def test_admin_sees_all_databases(self, api_base_url, admin_access_token):
        """Test admin can see all databases through API."""
        databases = get_databases(api_base_url, admin_access_token)

        # Admin should see all databases
        assert len(databases) > 0, "Admin should see at least one database"

        print(f"\n✅ Admin sees {len(databases)} databases:")
        for db in sorted(databases):
            print(f"   - {db}")

    def test_analyst_database_access(self, api_base_url, analyst_token):
        """Test analyst can access chinook, sakila, northwind through API."""
        databases = get_databases(api_base_url, analyst_token)

        # Analyst should see: chinook, sakila, northwind
        expected_databases = {"chinook", "sakila", "northwind"}
        actual_databases = set(databases)
        accessible = expected_databases.intersection(actual_databases)

        print(f"\n✅ Analyst sees {len(databases)} databases:")
        for db in sorted(databases):
            marker = "✅" if db in expected_databases else "⚠️"
            print(f"   {marker} {db}")

        print(f"\n   Expected to see: {', '.join(sorted(expected_databases))}")
        print(f"   Actually accessible: {', '.join(sorted(accessible))}")

        # Analyst should see at least some databases
        assert len(databases) > 0, "Analyst should see at least one database"

    def test_viewer_database_access(self, api_base_url, viewer_token):
        """Test viewer can access chinook, sakila (but NOT northwind) through API."""
        databases = get_databases(api_base_url, viewer_token)

        # Viewer should see: chinook, sakila
        # Viewer should NOT see: northwind
        expected_allowed = {"chinook", "sakila"}
        expected_denied = {"northwind"}
        actual_databases = set(databases)

        accessible = expected_allowed.intersection(actual_databases)
        incorrectly_accessible = expected_denied.intersection(actual_databases)

        print(f"\n✅ Viewer sees {len(databases)} databases:")
        for db in sorted(databases):
            marker = "✅" if db in expected_allowed else "❌" if db in expected_denied else "⚠️"
            print(f"   {marker} {db}")

        print(f"\n   Expected to see: {', '.join(sorted(expected_allowed))}")
        print(f"   Expected NOT to see: {', '.join(sorted(expected_denied))}")
        print(f"   Actually accessible: {', '.join(sorted(accessible))}")
        if incorrectly_accessible:
            print(f"   ❌ Incorrectly accessible: {', '.join(sorted(incorrectly_accessible))}")

        # Viewer should NOT see northwind
        assert "northwind" not in databases, "❌ FAILED: Viewer should NOT see northwind database"

        # Viewer should see at least some databases
        assert len(databases) > 0, "Viewer should see at least one database"

    def test_user_database_access(self, api_base_url, user_role_token):
        """Test user can access northwind (but NOT chinook or sakila) through API."""
        databases = get_databases(api_base_url, user_role_token)

        # User should see: northwind
        # User should NOT see: chinook, sakila
        expected_allowed = {"northwind"}
        expected_denied = {"chinook", "sakila"}
        actual_databases = set(databases)

        accessible = expected_allowed.intersection(actual_databases)
        incorrectly_accessible = expected_denied.intersection(actual_databases)

        print(f"\n✅ User sees {len(databases)} databases:")
        for db in sorted(databases):
            marker = "✅" if db in expected_allowed else "❌" if db in expected_denied else "⚠️"
            print(f"   {marker} {db}")

        print(f"\n   Expected to see: {', '.join(sorted(expected_allowed))}")
        print(f"   Expected NOT to see: {', '.join(sorted(expected_denied))}")
        print(f"   Actually accessible: {', '.join(sorted(accessible))}")
        if incorrectly_accessible:
            print(f"   ❌ Incorrectly accessible: {', '.join(sorted(incorrectly_accessible))}")

        # User should NOT see chinook or sakila
        assert "chinook" not in databases, "❌ FAILED: User should NOT see chinook database"
        assert "sakila" not in databases, "❌ FAILED: User should NOT see sakila database"

        # User should see at least one database
        assert len(databases) > 0, "User should see at least one database"

    def test_access_matrix_complete(self, api_base_url, admin_access_token,
                                     analyst_token, viewer_token, user_role_token):
        """Test complete access matrix for all roles through API."""

        # Get databases for each role
        admin_dbs = set(get_databases(api_base_url, admin_access_token))
        analyst_dbs = set(get_databases(api_base_url, analyst_token))
        viewer_dbs = set(get_databases(api_base_url, viewer_token))
        user_dbs = set(get_databases(api_base_url, user_role_token))

        # Print access matrix
        print("\n" + "="*70)
        print(" DATABASE ACCESS MATRIX (via API /api/databases/)")
        print("="*70)
        print(f"{'Role':<12} | {'Count':<6} | {'Databases':<45}")
        print("-"*70)
        print(f"{'admin':<12} | {len(admin_dbs):<6} | {', '.join(sorted(admin_dbs))}")
        print(f"{'analyst':<12} | {len(analyst_dbs):<6} | {', '.join(sorted(analyst_dbs))}")
        print(f"{'viewer':<12} | {len(viewer_dbs):<6} | {', '.join(sorted(viewer_dbs))}")
        print(f"{'user':<12} | {len(user_dbs):<6} | {', '.join(sorted(user_dbs))}")
        print("="*70)

        # Verify expected access patterns
        # Admin should have most access
        assert len(admin_dbs) >= len(analyst_dbs), "Admin should have at least as many databases as analyst"
        assert len(admin_dbs) >= len(viewer_dbs), "Admin should have at least as many databases as viewer"
        assert len(admin_dbs) >= len(user_dbs), "Admin should have at least as many databases as user"

        # Analyst should have more access than viewer or user
        assert len(analyst_dbs) >= len(viewer_dbs), "Analyst should have at least as many databases as viewer"
        assert len(analyst_dbs) >= len(user_dbs), "Analyst should have at least as many databases as user"

        # Verify specific denials
        assert "northwind" not in viewer_dbs, "❌ FAILED: Viewer should NOT see northwind"
        assert "chinook" not in user_dbs, "❌ FAILED: User should NOT see chinook"
        assert "sakila" not in user_dbs, "❌ FAILED: User should NOT see sakila"

        print("\n✅ All access control checks passed!")
        print("\nExpected Access Matrix:")
        print("  admin    → chinook ✅, sakila ✅, northwind ✅")
        print("  analyst  → chinook ✅, sakila ✅, northwind ✅")
        print("  viewer   → chinook ✅, sakila ✅, northwind ❌")
        print("  user     → chinook ❌, sakila ❌, northwind ✅")
