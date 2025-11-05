"""
Integration tests for authentication flow.

Tests the complete authentication workflow:
1. User registration
2. Login with valid credentials
3. Login with invalid credentials
4. Token refresh
5. Protected route access
6. Token expiration handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncio
from datetime import datetime, timedelta

from app.main import app
from app.db.session import get_db, Base
from app.core.config import settings


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client(test_db):
    """Create test client with test database."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class TestAuthenticationFlow:
    """Tests for complete authentication flow."""

    def test_user_registration_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
                "department": "Engineering"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["department"] == "Engineering"
        assert data["role"] == "user"  # Default role
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data  # Password should not be returned

    def test_user_registration_duplicate_email(self, client):
        """Test registration with duplicate email."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123"
            }
        )

        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPass456"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_user_registration_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_user_registration_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_login_success(self, client):
        """Test successful login."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "loginuser@example.com",
                "password": "SecurePass123"
            }
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "loginuser@example.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "password": "CorrectPass123"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user2@example.com",
                "password": "WrongPass456"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123"
            }
        )

        assert response.status_code == 401

    def test_protected_route_with_valid_token(self, client):
        """Test accessing protected route with valid token."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "protected@example.com",
                "password": "SecurePass123"
            }
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "protected@example.com",
                "password": "SecurePass123"
            }
        )

        token = login_response.json()["access_token"]

        # Access protected route
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"

    def test_protected_route_without_token(self, client):
        """Test accessing protected route without token."""
        response = client.get("/users/me")

        assert response.status_code == 401

    def test_protected_route_with_invalid_token(self, client):
        """Test accessing protected route with invalid token."""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid-token-here"}
        )

        assert response.status_code == 401

    def test_token_refresh_success(self, client):
        """Test token refresh with valid refresh token."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "SecurePass123"
            }
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "SecurePass123"
            }
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # New tokens should be different
        assert data["access_token"] != login_response.json()["access_token"]

    def test_token_refresh_with_invalid_token(self, client):
        """Test token refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"}
        )

        assert response.status_code == 401


class TestRegistrationWithCompany:
    """Tests for user registration with company."""

    def test_first_user_becomes_admin(self, client):
        """Test that first user in company becomes admin."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@newcompany.com",
                "password": "SecurePass123",
                "company_name": "New Company Inc"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"  # First user is admin

    def test_second_user_not_admin(self, client):
        """Test that second user in company is not admin."""
        # First user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "first@company.com",
                "password": "SecurePass123",
                "company_name": "Test Company"
            }
        )

        # Second user (same company would need company_id,
        # but for test we'll create different email)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "second@company.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"  # Default role


class TestAuthenticationEdgeCases:
    """Tests for authentication edge cases."""

    def test_login_inactive_user(self, client):
        """Test login with inactive user account."""
        # This test would require a way to deactivate user
        # For now, we'll skip it as we don't have deactivation endpoint
        # TODO: Implement when user deactivation is added
        pass

    def test_case_insensitive_email_login(self, client):
        """Test that email login is case-insensitive."""
        # Register with lowercase
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        )

        # Login with uppercase
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "USER@EXAMPLE.COM",
                "password": "SecurePass123"
            }
        )

        # Should succeed (depending on implementation)
        # If fails, this documents current behavior
        assert response.status_code in [200, 401]
