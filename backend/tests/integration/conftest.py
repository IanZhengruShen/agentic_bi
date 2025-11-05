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


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in integration/ as integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
