"""
API endpoint tests for authentication

Tests all auth endpoints:
- POST /auth/register
- POST /auth/login
- GET /auth/me
- GET /auth/status
- PUT /auth/password
- POST /auth/logout
- POST /auth/refresh
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.shared.database import get_db, Base
from app.user_management.user_models import User


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def clean_database():
    """Clean database between tests"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_user_success(self, clean_database):
        """Test successful user registration"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "password" not in data
        assert "password_hash" not in data
        assert "id" in data

    def test_register_user_duplicate_username(self, clean_database):
        """Test registration with duplicate username"""
        user_data = {
            "username": "testuser",
            "email": "test1@example.com",
            "password": "password123"
        }
        # Create first user
        client.post("/auth/register", json=user_data)

        # Try to create second user with same username
        user_data2 = {
            "username": "testuser",
            "email": "test2@example.com",
            "password": "password123"
        }

        response = client.post("/auth/register", json=user_data2)

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"] == "USERNAME_EXISTS"

    def test_register_user_duplicate_email(self, clean_database):
        """Test registration with duplicate email"""
        user_data = {
            "username": "testuser1",
            "email": "test@example.com",
            "password": "password123"
        }
        # Create first user
        client.post("/auth/register", json=user_data)

        # Try to create second user with same email
        user_data2 = {
            "username": "testuser2",
            "email": "test@example.com",
            "password": "password123"
        }

        response = client.post("/auth/register", json=user_data2)

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"] == "EMAIL_EXISTS"

    def test_register_user_invalid_data(self, clean_database):
        """Test registration with invalid data"""
        # Missing required fields
        user_data = {
            "username": "testuser"
            # Missing email and password
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 422

    def test_register_user_invalid_email(self, clean_database):
        """Test registration with invalid email format"""
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint"""

    def test_login_success(self, clean_database):
        """Test successful user login"""
        # First register a user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        # Now login
        login_data = {
            "username": "testuser",
            "password": "password123"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_info" in data
        assert data["user_info"]["username"] == "testuser"

    def test_login_with_email(self, clean_database):
        """Test login using email instead of username"""
        # Register user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        # Login with email
        login_data = {
            "username": "test@example.com",  # Using email as username
            "password": "password123"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_credentials(self, clean_database):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_CREDENTIALS"

    def test_login_wrong_password(self, clean_database):
        """Test login with correct username but wrong password"""
        # Register user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        # Login with wrong password
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_CREDENTIALS"


class TestProtectedEndpoints:
    """Test protected endpoints requiring authentication"""

    def get_auth_token(self, clean_database):
        """Helper method to get authentication token"""
        # Register and login user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post("/auth/login", json=login_data)
        return response.json()["access_token"]

    def test_get_current_user_success(self, clean_database):
        """Test getting current user info with valid token"""
        token = self.get_auth_token(clean_database)

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_current_user_no_token(self, clean_database):
        """Test getting current user without token"""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, clean_database):
        """Test getting current user with invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_auth_status(self, clean_database):
        """Test auth status endpoint"""
        token = self.get_auth_token(clean_database)

        response = client.get(
            "/auth/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert "user" in data

    def test_auth_status_no_token(self, clean_database):
        """Test auth status without token"""
        response = client.get("/auth/status")

        # Should still return 200 but with authenticated: false
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestPasswordChange:
    """Test password change endpoint"""

    def get_auth_token(self, clean_database):
        """Helper method to get authentication token"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post("/auth/login", json=login_data)
        return response.json()["access_token"]

    def test_change_password_success(self, clean_database):
        """Test successful password change"""
        token = self.get_auth_token(clean_database)

        password_data = {
            "current_password": "password123",
            "new_password": "newpassword456"
        }

        response = client.put(
            "/auth/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Verify new password works
        login_data = {
            "username": "testuser",
            "password": "newpassword456"
        }
        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, clean_database):
        """Test password change with wrong current password"""
        token = self.get_auth_token(clean_database)

        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword456"
        }

        response = client.put(
            "/auth/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_PASSWORD"

    def test_change_password_no_token(self, clean_database):
        """Test password change without authentication"""
        password_data = {
            "current_password": "password123",
            "new_password": "newpassword456"
        }

        response = client.put("/auth/password", json=password_data)

        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint"""

    def get_auth_token(self, clean_database):
        """Helper method to get authentication token"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post("/auth/login", json=login_data)
        return response.json()["access_token"]

    def test_logout_success(self, clean_database):
        """Test successful logout"""
        token = self.get_auth_token(clean_database)

        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_logout_no_token(self, clean_database):
        """Test logout without token"""
        response = client.post("/auth/logout")

        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh endpoint"""

    def get_auth_token(self, clean_database):
        """Helper method to get authentication token"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post("/auth/login", json=login_data)
        return response.json()["access_token"]

    def test_refresh_token_success(self, clean_database):
        """Test successful token refresh"""
        token = self.get_auth_token(clean_database)

        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, clean_database):
        """Test token refresh with invalid token"""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_refresh_token_no_token(self, clean_database):
        """Test token refresh without token"""
        response = client.post("/auth/refresh")

        assert response.status_code == 401


# Integration test for complete auth flow
class TestCompleteAuthFlow:
    """Test complete authentication flow"""

    def test_complete_flow(self, clean_database):
        """Test complete authentication flow from registration to logout"""
        # 1. Register user
        user_data = {
            "username": "flowtest",
            "email": "flowtest@example.com",
            "password": "password123",
            "full_name": "Flow Test User"
        }
        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # 2. Login
        login_data = {
            "username": "flowtest",
            "password": "password123"
        }
        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 3. Access protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "flowtest"

        # 4. Change password
        password_data = {
            "current_password": "password123",
            "new_password": "newpassword456"
        }
        password_response = client.put(
            "/auth/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert password_response.status_code == 200

        # 5. Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        # 6. Logout
        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert logout_response.status_code == 200

        # 7. Verify new password works
        new_login_data = {
            "username": "flowtest",
            "password": "newpassword456"
        }
        new_login_response = client.post("/auth/login", json=new_login_data)
        assert new_login_response.status_code == 200