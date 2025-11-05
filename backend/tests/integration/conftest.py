"""
Real Integration Test Configuration.

Tests against actual running API endpoints (no mocks).
Uses the real API at: https://api-agentic-bi.dev01.datascience-tmnl.nl
"""

import pytest
import os
import requests
from typing import Dict, Optional
import time


# Real API Configuration
API_BASE_URL = os.getenv("TEST_API_BASE_URL", "https://api-agentic-bi.dev01.datascience-tmnl.nl")
API_TIMEOUT = int(os.getenv("TEST_API_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Get API base URL for testing."""
    return API_BASE_URL


@pytest.fixture(scope="session")
def api_health_check(api_base_url: str):
    """Check if API is running before tests."""
    try:
        # Try root endpoint first
        response = requests.get(f"{api_base_url}/", timeout=5)
        if response.status_code == 200:
            return True

        # Try docs endpoint
        response = requests.get(f"{api_base_url}/docs", timeout=5)
        if response.status_code == 200:
            return True

        pytest.skip(f"API is not reachable at {api_base_url}")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"API is not running at {api_base_url}: {e}")


@pytest.fixture(scope="session")
def unique_test_id() -> str:
    """Generate unique test ID for this session."""
    return str(int(time.time()))


@pytest.fixture(scope="session")
def test_user_credentials(unique_test_id: str) -> Dict[str, str]:
    """
    Test user credentials.
    Creates unique email per test session to avoid conflicts.
    """
    return {
        "email": f"test_user_{unique_test_id}@example.com",
        "password": "TestPassword123!",
        "full_name": "Integration Test User",
        "department": "QA"
    }


@pytest.fixture(scope="session")
def admin_user_credentials(unique_test_id: str) -> Dict[str, str]:
    """Admin test user credentials (first user in new company)."""
    return {
        "email": f"test_admin_{unique_test_id}@example.com",
        "password": "AdminPassword123!",
        "full_name": "Admin Test User",
        "company_name": f"Test Company {unique_test_id}"
    }


@pytest.fixture(scope="session")
def registered_user(api_base_url: str, api_health_check, test_user_credentials: Dict) -> Dict:
    """
    Register a test user and return credentials + user data.
    Runs once per test session.
    """
    # Register user
    response = requests.post(
        f"{api_base_url}/api/v1/auth/register",
        json=test_user_credentials,
        timeout=API_TIMEOUT
    )

    if response.status_code == 400 and "already registered" in response.text.lower():
        # User already exists, try to use it
        print(f"User {test_user_credentials['email']} already exists, reusing")
        user_data = {}
    elif response.status_code == 201:
        user_data = response.json()
        print(f"Registered user: {user_data.get('email')}, role: {user_data.get('role')}")
    else:
        pytest.fail(f"Failed to register test user: {response.status_code} - {response.text}")

    return {
        **test_user_credentials,
        "id": user_data.get("id"),
        "role": user_data.get("role", "user")
    }


@pytest.fixture(scope="session")
def registered_admin(api_base_url: str, api_health_check, admin_user_credentials: Dict) -> Dict:
    """Register an admin test user (first user in new company)."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/register",
        json=admin_user_credentials,
        timeout=API_TIMEOUT
    )

    if response.status_code == 400 and "already registered" in response.text.lower():
        print(f"Admin {admin_user_credentials['email']} already exists, reusing")
        user_data = {}
    elif response.status_code == 201:
        user_data = response.json()
        print(f"Registered admin: {user_data.get('email')}, role: {user_data.get('role')}")
    else:
        pytest.fail(f"Failed to register admin user: {response.status_code} - {response.text}")

    return {
        **admin_user_credentials,
        "id": user_data.get("id"),
        "role": user_data.get("role", "admin")
    }


@pytest.fixture(scope="function")
def user_access_token(api_base_url: str, registered_user: Dict) -> str:
    """Get fresh access token for regular user (per test function)."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        },
        timeout=API_TIMEOUT
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to login test user: {response.status_code} - {response.text}")

    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_access_token(api_base_url: str, registered_admin: Dict) -> str:
    """Get fresh access token for admin user (per test function)."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": registered_admin["email"],
            "password": registered_admin["password"]
        },
        timeout=API_TIMEOUT
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to login admin user: {response.status_code} - {response.text}")

    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(user_access_token: str) -> Dict[str, str]:
    """Get authorization headers for requests."""
    return {
        "Authorization": f"Bearer {user_access_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def admin_auth_headers(admin_access_token: str) -> Dict[str, str]:
    """Get authorization headers for admin requests."""
    return {
        "Authorization": f"Bearer {admin_access_token}",
        "Content-Type": "application/json"
    }


# ============================================
# OPA-Specific Fixtures
# ============================================

@pytest.fixture(scope="session")
def opa_url() -> str:
    """Get OPA service URL."""
    return os.getenv("OPA_URL", "https://opa.dev01.datascience-tmnl.nl")


@pytest.fixture(scope="session")
def opa_health_check(opa_url: str):
    """Check if OPA service is available."""
    try:
        response = requests.get(f"{opa_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"OPA service not healthy at {opa_url}")
        return True
    except requests.exceptions.RequestException as e:
        pytest.skip(f"OPA service not reachable at {opa_url}: {e}")


@pytest.fixture(scope="session")
def verify_opa_policy(opa_url: str, opa_health_check):
    """Verify OPA policy is deployed."""
    try:
        response = requests.get(f"{opa_url}/v1/policies", timeout=5)
        if response.status_code != 200:
            pytest.skip("Cannot verify OPA policies")

        policies = response.json()
        # Check if any policies exist (don't enforce specific name)
        if not policies or (isinstance(policies, dict) and len(policies.get("result", {})) == 0):
            pytest.skip("No OPA policies found")

        return True
    except Exception as e:
        pytest.skip(f"Cannot verify OPA policy: {e}")


@pytest.fixture(scope="session")
def verify_opa_data(opa_url: str, opa_health_check):
    """Verify OPA policy data is loaded."""
    try:
        response = requests.get(f"{opa_url}/v1/data/role_permissions", timeout=5)
        if response.status_code != 200:
            pytest.skip("OPA policy data not loaded. Run: ./deploy_opa_policy.sh")

        data = response.json()
        result = data.get("result", {})

        # Verify required roles exist
        required_roles = ["analyst", "viewer", "user"]
        for role in required_roles:
            if role not in result:
                pytest.skip(f"Role '{role}' not found in OPA policy data")

        return result
    except Exception as e:
        pytest.skip(f"Cannot verify OPA data: {e}")


# Role-specific user fixtures for OPA testing
@pytest.fixture(scope="session")
def analyst_credentials(unique_test_id: str) -> Dict[str, str]:
    """Analyst user credentials for OPA testing."""
    return {
        "email": f"test_analyst_{unique_test_id}@example.com",
        "password": "AnalystPassword123!",
        "full_name": "Test Analyst User",
        "company_name": f"Test Company Analyst {unique_test_id}"
    }


@pytest.fixture(scope="session")
def viewer_credentials(unique_test_id: str) -> Dict[str, str]:
    """Viewer user credentials for OPA testing."""
    return {
        "email": f"test_viewer_{unique_test_id}@example.com",
        "password": "ViewerPassword123!",
        "full_name": "Test Viewer User",
        "company_name": f"Test Company Viewer {unique_test_id}"
    }


@pytest.fixture(scope="session")
def user_role_credentials(unique_test_id: str) -> Dict[str, str]:
    """User role credentials for OPA testing."""
    return {
        "email": f"test_user_role_{unique_test_id}@example.com",
        "password": "UserPassword123!",
        "full_name": "Test User Role",
        "company_name": f"Test Company User {unique_test_id}"
    }


def _register_and_set_role(api_base_url: str, credentials: Dict, target_role: str) -> Dict:
    """
    Helper to register user and set their role.

    NOTE: This function has a limitation - when registering with a new company_name,
    the user becomes admin (first user in company). Due to self-demotion protection,
    we cannot change admin -> non-admin role. This fixture is currently unused but
    would need refactoring if used (e.g., create 2nd admin first, then demote).
    """
    # Register user (will be admin of new company)
    response = requests.post(
        f"{api_base_url}/api/v1/auth/register",
        json=credentials,
        timeout=API_TIMEOUT
    )

    if response.status_code == 400 and "already registered" in response.text.lower():
        user_data = {"role": target_role}
    elif response.status_code == 201:
        user_data = response.json()

        # Login to get token
        login_response = requests.post(
            f"{api_base_url}/api/v1/auth/login",
            json={
                "email": credentials["email"],
                "password": credentials["password"]
            },
            timeout=API_TIMEOUT
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Change role to target role (user is admin of new company, so can change own role)
            role_response = requests.put(
                f"{api_base_url}/users/{user_data['id']}/role",
                json={"new_role": target_role},
                headers={"Authorization": f"Bearer {token}"},
                timeout=API_TIMEOUT
            )

            if role_response.status_code == 200:
                user_data["role"] = target_role
    else:
        pytest.fail(f"Failed to register {target_role} user: {response.status_code} - {response.text}")

    return {**credentials, **user_data}


@pytest.fixture(scope="session")
def registered_analyst(api_base_url: str, api_health_check, analyst_credentials: Dict) -> Dict:
    """Register and configure analyst user."""
    return _register_and_set_role(api_base_url, analyst_credentials, "analyst")


@pytest.fixture(scope="session")
def registered_viewer(api_base_url: str, api_health_check, viewer_credentials: Dict) -> Dict:
    """Register and configure viewer user."""
    return _register_and_set_role(api_base_url, viewer_credentials, "viewer")


@pytest.fixture(scope="session")
def registered_user_role(api_base_url: str, api_health_check, user_role_credentials: Dict) -> Dict:
    """Register and configure user role."""
    return _register_and_set_role(api_base_url, user_role_credentials, "user")


@pytest.fixture(scope="function")
def analyst_token(api_base_url: str, registered_analyst: Dict) -> str:
    """Get analyst access token."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": registered_analyst["email"],
            "password": registered_analyst["password"]
        },
        timeout=API_TIMEOUT
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to login analyst: {response.status_code} - {response.text}")

    return response.json()["access_token"]


@pytest.fixture(scope="function")
def viewer_token(api_base_url: str, registered_viewer: Dict) -> str:
    """Get viewer access token."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": registered_viewer["email"],
            "password": registered_viewer["password"]
        },
        timeout=API_TIMEOUT
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to login viewer: {response.status_code} - {response.text}")

    return response.json()["access_token"]


@pytest.fixture(scope="function")
def user_role_token(api_base_url: str, registered_user_role: Dict) -> str:
    """Get user role access token."""
    response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": registered_user_role["email"],
            "password": registered_user_role["password"]
        },
        timeout=API_TIMEOUT
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to login user role: {response.status_code} - {response.text}")

    return response.json()["access_token"]


@pytest.fixture(scope="function")
def analyst_headers(analyst_token: str) -> Dict[str, str]:
    """Get authorization headers for analyst."""
    return {
        "Authorization": f"Bearer {analyst_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def viewer_headers(viewer_token: str) -> Dict[str, str]:
    """Get authorization headers for viewer."""
    return {
        "Authorization": f"Bearer {viewer_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def user_role_headers(user_role_token: str) -> Dict[str, str]:
    """Get authorization headers for user role."""
    return {
        "Authorization": f"Bearer {user_role_token}",
        "Content-Type": "application/json"
    }


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as real integration test (hits live API)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (>5s)"
    )
    config.addinivalue_line(
        "markers", "requires_mindsdb: mark test as requiring MindsDB connection"
    )
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring LLM/Azure OpenAI"
    )
    config.addinivalue_line(
        "markers", "requires_opa: mark test as requiring OPA service"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in integration/ as integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
