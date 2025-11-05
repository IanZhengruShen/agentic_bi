"""
Real API Integration Tests - Authentication

Tests authentication flow against live API:
- https://api-agentic-bi.dev01.datascience-tmnl.nl

NO MOCKING - Tests real endpoints.
"""

import pytest
import requests
import time


@pytest.mark.integration
class TestAuthenticationRegistration:
    """Test user registration against real API."""

    def test_register_new_user(self, api_base_url):
        """Test registering a brand new user."""
        unique_email = f"new_user_{int(time.time())}@example.com"

        response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "SecurePass123!",
                "full_name": "New Test User",
                "department": "Engineering"
            },
            timeout=30
        )

        assert response.status_code == 201, f"Registration failed: {response.text}"
        data = response.json()

        # Verify response structure
        assert data["email"] == unique_email
        assert data["full_name"] == "New Test User"
        assert data["department"] == "Engineering"
        assert data["role"] in ["admin", "user"]  # First user might be admin
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data  # Password should never be returned

    def test_register_duplicate_email(self, api_base_url, registered_user):
        """Test that duplicate email registration fails."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": registered_user["email"],
                "password": "DifferentPass456!",
            },
            timeout=30
        )

        # Should return 400 or 409 (Conflict) error
        assert response.status_code in [400, 409], f"Expected 400/409, got {response.status_code}: {response.text}"
        # Error message should mention email already registered
        assert "email" in response.text.lower() or "registered" in response.text.lower()

    def test_register_invalid_email(self, api_base_url):
        """Test that invalid email format is rejected."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!"
            },
            timeout=30
        )

        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, api_base_url):
        """Test that weak passwords are rejected."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": f"user_{int(time.time())}@example.com",
                "password": "weak"
            },
            timeout=30
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestAuthenticationLogin:
    """Test login functionality against real API."""

    def test_login_with_valid_credentials(self, api_base_url, registered_user):
        """Test successful login with correct credentials."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"]
            },
            timeout=30
        )

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()

        # Verify token response
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 20  # JWT tokens are long
        assert len(data["refresh_token"]) > 20

    def test_login_with_wrong_password(self, api_base_url, registered_user):
        """Test login fails with incorrect password."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPassword999!"
            },
            timeout=30
        )

        assert response.status_code == 401
        assert "incorrect" in response.text.lower() or "unauthorized" in response.text.lower()

    def test_login_with_nonexistent_user(self, api_base_url):
        """Test login fails for non-existent user."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/login",
            json={
                "email": "nonexistent_user_12345@example.com",
                "password": "SomePass123!"
            },
            timeout=30
        )

        assert response.status_code == 401


@pytest.mark.integration
class TestProtectedRoutes:
    """Test protected route access with tokens."""

    def test_access_protected_route_with_valid_token(self, api_base_url, auth_headers):
        """Test accessing protected route with valid token."""
        response = requests.get(
            f"{api_base_url}/users/me",
            headers=auth_headers,
            timeout=30
        )

        assert response.status_code == 200, f"Protected route access failed: {response.text}"
        data = response.json()

        # Verify user data returned
        assert "email" in data
        assert "role" in data
        assert "is_active" in data

    def test_access_protected_route_without_token(self, api_base_url):
        """Test that protected route requires authentication."""
        response = requests.get(
            f"{api_base_url}/users/me",
            timeout=30
        )

        # Should return 401 or 403 (both indicate unauthorized)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_access_protected_route_with_invalid_token(self, api_base_url):
        """Test that invalid token is rejected."""
        response = requests.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": "Bearer invalid-token-12345"},
            timeout=30
        )

        assert response.status_code == 401


@pytest.mark.integration
class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_token_success(self, api_base_url, unique_test_id):
        """Test refreshing access token with valid refresh token."""
        # Create a unique user for this specific test to avoid token conflicts
        test_email = f"refresh_test_{unique_test_id}_{int(time.time())}@example.com"

        # Register user
        register_response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": test_email,
                "password": "RefreshTestPass123!",
                "full_name": "Refresh Test User"
            },
            timeout=30
        )

        # User might already exist from previous test run, that's okay
        if register_response.status_code not in [201, 400, 409]:
            pytest.fail(f"Failed to register test user: {register_response.status_code} - {register_response.text}")

        # First login to get refresh token
        login_response = requests.post(
            f"{api_base_url}/api/v1/auth/login",
            json={
                "email": test_email,
                "password": "RefreshTestPass123!"
            },
            timeout=30
        )

        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        refresh_token = login_response.json()["refresh_token"]
        old_access_token = login_response.json()["access_token"]

        # Small delay to ensure timestamps differ
        time.sleep(0.1)

        # Refresh the token
        refresh_response = requests.post(
            f"{api_base_url}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=30
        )

        assert refresh_response.status_code == 200, f"Token refresh failed: {refresh_response.text}"
        data = refresh_response.json()

        # Verify new tokens
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # New tokens should be different from old ones
        assert data["access_token"] != old_access_token

    def test_refresh_with_invalid_token(self, api_base_url):
        """Test that invalid refresh token is rejected."""
        response = requests.post(
            f"{api_base_url}/api/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token-12345"},
            timeout=30
        )

        assert response.status_code == 401


@pytest.mark.integration
class TestCompanyCreation:
    """Test company creation during registration."""

    def test_first_user_in_company_becomes_admin(self, api_base_url):
        """Test that first user registering with company_name becomes admin."""
        unique_id = int(time.time())

        response = requests.post(
            f"{api_base_url}/api/v1/auth/register",
            json={
                "email": f"first_user_{unique_id}@example.com",
                "password": "SecurePass123!",
                "company_name": f"Brand New Company {unique_id}"
            },
            timeout=30
        )

        assert response.status_code == 201, f"Registration failed: {response.text}"
        data = response.json()

        # First user in new company should be admin
        assert data["role"] == "admin"
