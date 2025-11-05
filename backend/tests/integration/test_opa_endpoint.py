"""
OPA Endpoint Direct Tests.

Simple, focused tests that hit OPA authorization endpoint directly.
No database dependencies, no complex setup - just pure OPA testing.

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
-----------
# Run all OPA endpoint tests
uv run pytest tests/integration/test_opa_endpoint.py -v -s

# Run specific test
uv run pytest tests/integration/test_opa_endpoint.py::test_opa_deny_viewer_northwind -v -s
"""

import pytest
import requests


# OPA Service URL
OPA_URL = "https://opa.dev01.datascience-tmnl.nl"


def check_opa_permission(role: str, database: str) -> bool:
    """
    Check if a role has permission to access a database via OPA.

    Args:
        role: User role (admin, analyst, viewer, user)
        database: Database name (chinook, sakila, northwind)

    Returns:
        bool: True if allowed, False if denied
    """
    response = requests.post(
        f"{OPA_URL}/v1/data/app/rbac/allow",
        json={
            "input": {
                "user": {
                    "id": f"test-{role}-id",
                    "company_id": "test-company-id",
                    "role": role
                },
                "action": "read",
                "resource": {
                    "type": "database",
                    "data": {"database_name": database}
                }
            }
        },
        timeout=5
    )

    assert response.status_code == 200, f"OPA request failed: {response.status_code}"
    result = response.json()
    return result.get("result", False)


@pytest.mark.integration
@pytest.mark.requires_opa
class TestOPAAdminAccess:
    """Test admin has access to everything."""

    def test_admin_chinook(self):
        """Admin can access chinook."""
        assert check_opa_permission("admin", "chinook") is True
        print("✅ Admin can access chinook")

    def test_admin_sakila(self):
        """Admin can access sakila."""
        assert check_opa_permission("admin", "sakila") is True
        print("✅ Admin can access sakila")

    def test_admin_northwind(self):
        """Admin can access northwind."""
        assert check_opa_permission("admin", "northwind") is True
        print("✅ Admin can access northwind")

    def test_admin_any_database(self):
        """Admin can access any arbitrary database."""
        assert check_opa_permission("admin", "any_random_database") is True
        print("✅ Admin can access any database")


@pytest.mark.integration
@pytest.mark.requires_opa
class TestOPAAnalystAccess:
    """Test analyst has access to chinook, sakila, northwind."""

    def test_analyst_chinook_allowed(self):
        """Analyst can access chinook."""
        assert check_opa_permission("analyst", "chinook") is True
        print("✅ Analyst can access chinook")

    def test_analyst_sakila_allowed(self):
        """Analyst can access sakila."""
        assert check_opa_permission("analyst", "sakila") is True
        print("✅ Analyst can access sakila")

    def test_analyst_northwind_allowed(self):
        """Analyst can access northwind."""
        assert check_opa_permission("analyst", "northwind") is True
        print("✅ Analyst can access northwind")


@pytest.mark.integration
@pytest.mark.requires_opa
class TestOPAViewerAccess:
    """Test viewer has access to chinook, sakila but NOT northwind."""

    def test_viewer_chinook_allowed(self):
        """Viewer can access chinook."""
        assert check_opa_permission("viewer", "chinook") is True
        print("✅ Viewer can access chinook")

    def test_viewer_sakila_allowed(self):
        """Viewer can access sakila."""
        assert check_opa_permission("viewer", "sakila") is True
        print("✅ Viewer can access sakila")

    def test_viewer_northwind_denied(self):
        """Viewer CANNOT access northwind."""
        assert check_opa_permission("viewer", "northwind") is False
        print("✅ Viewer correctly denied access to northwind")


@pytest.mark.integration
@pytest.mark.requires_opa
class TestOPAUserAccess:
    """Test user has access to northwind but NOT chinook or sakila."""

    def test_user_chinook_denied(self):
        """User CANNOT access chinook."""
        assert check_opa_permission("user", "chinook") is False
        print("✅ User correctly denied access to chinook")

    def test_user_sakila_denied(self):
        """User CANNOT access sakila."""
        assert check_opa_permission("user", "sakila") is False
        print("✅ User correctly denied access to sakila")

    def test_user_northwind_allowed(self):
        """User can access northwind."""
        assert check_opa_permission("user", "northwind") is True
        print("✅ User can access northwind")


@pytest.mark.integration
@pytest.mark.requires_opa
def test_opa_access_matrix_summary():
    """
    Test complete access matrix - prints summary table.
    This test always passes but shows the full access matrix.
    """
    roles = ["admin", "analyst", "viewer", "user"]
    databases = ["chinook", "sakila", "northwind"]

    print("\n" + "="*60)
    print(" OPA ACCESS CONTROL MATRIX")
    print("="*60)
    print(f"{'Role':<12} | {'chinook':<10} | {'sakila':<10} | {'northwind':<10}")
    print("-"*60)

    for role in roles:
        row = [role]
        for db in databases:
            allowed = check_opa_permission(role, db)
            status = "✅ Yes" if allowed else "❌ No"
            row.append(status)

        print(f"{row[0]:<12} | {row[1]:<10} | {row[2]:<10} | {row[3]:<10}")

    print("="*60)
    print("\nExpected Matrix:")
    print("  admin    → chinook ✅, sakila ✅, northwind ✅")
    print("  analyst  → chinook ✅, sakila ✅, northwind ✅")
    print("  viewer   → chinook ✅, sakila ✅, northwind ❌")
    print("  user     → chinook ❌, sakila ❌, northwind ✅")
    print()


# Individual test functions for easy single-test runs
def test_opa_admin_access():
    """Quick test: Admin can access everything."""
    assert check_opa_permission("admin", "chinook") is True
    assert check_opa_permission("admin", "any_database") is True
    print("✅ Admin access verified")


def test_opa_viewer_cannot_see_northwind():
    """Quick test: Viewer cannot see northwind."""
    assert check_opa_permission("viewer", "northwind") is False
    print("✅ Viewer correctly denied northwind")


def test_opa_user_cannot_see_chinook():
    """Quick test: User cannot see chinook."""
    assert check_opa_permission("user", "chinook") is False
    print("✅ User correctly denied chinook")
