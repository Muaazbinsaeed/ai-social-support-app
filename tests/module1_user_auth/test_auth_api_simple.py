"""
Simplified API tests for authentication endpoints
Tests the actual API endpoints without complex dependencies
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-module1-auth"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

# Mock problematic dependencies before importing
mock_modules = {
    'transformers': Mock(),
    'torch': Mock(),
    'easyocr': Mock(),
    'streamlit': Mock(),
    'plotly': Mock(),
    'langgraph': Mock(),
    'langchain': Mock(),
}

for mod_name, mod_mock in mock_modules.items():
    sys.modules[mod_name] = mod_mock

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Import only what we need for auth testing
    from app.shared.database import Base, get_db
    from app.user_management.user_models import User
    from app.api.auth_router import router as auth_router
    from app.dependencies import get_current_active_user

    # Create minimal FastAPI app for testing
    test_app = FastAPI()
    test_app.include_router(auth_router)

    # Test database setup
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        """Override database dependency for testing"""
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    client = TestClient(test_app)

except ImportError as e:
    pytest.skip(f"Skipping API tests due to import error: {e}", allow_module_level=True)


@pytest.fixture(scope="module")
def setup_test_db():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def clean_db():
    """Clean database between tests"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


class TestAuthenticationAPI:
    """Test authentication API endpoints"""

    def test_register_user_success(self, setup_test_db, clean_db):
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
        assert "id" in data

    def test_register_duplicate_user(self, setup_test_db, clean_db):
        """Test registration with duplicate username"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }

        # Create first user
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 201

        # Try to create duplicate
        user_data2 = {
            "username": "testuser",
            "email": "different@example.com",
            "password": "password123"
        }
        response2 = client.post("/auth/register", json=user_data2)

        assert response2.status_code == 409
        assert "USERNAME_EXISTS" in response2.json()["detail"]["error"]

    def test_login_success(self, setup_test_db, clean_db):
        """Test successful login"""
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

    def test_login_invalid_credentials(self, setup_test_db, clean_db):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "INVALID_CREDENTIALS" in response.json()["detail"]["error"]

    def test_login_with_email(self, setup_test_db, clean_db):
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

    def test_protected_endpoint_without_token(self, setup_test_db, clean_db):
        """Test accessing protected endpoint without token"""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_token(self, setup_test_db, clean_db):
        """Test accessing protected endpoint with valid token"""
        # Register and login
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/auth/register", json=user_data)

        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_password_change(self, setup_test_db, clean_db):
        """Test password change functionality"""
        # Register and login
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "oldpassword"
        }
        client.post("/auth/register", json=user_data)

        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "oldpassword"
        })
        token = login_response.json()["access_token"]

        # Change password
        password_data = {
            "current_password": "oldpassword",
            "new_password": "newpassword123"
        }
        response = client.put(
            "/auth/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        # Verify new password works
        new_login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "newpassword123"
        })
        assert new_login_response.status_code == 200

    def test_complete_auth_flow(self, setup_test_db, clean_db):
        """Test complete authentication flow"""
        # 1. Register
        user_data = {
            "username": "flowtest",
            "email": "flowtest@example.com",
            "password": "password123",
            "full_name": "Flow Test User"
        }
        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # 2. Login
        login_response = client.post("/auth/login", json={
            "username": "flowtest",
            "password": "password123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 3. Access protected endpoint
        me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "flowtest"

        # 4. Check auth status
        status_response = client.get("/auth/status", headers={"Authorization": f"Bearer {token}"})
        assert status_response.status_code == 200
        assert status_response.json()["authenticated"] is True

        # 5. Refresh token
        refresh_response = client.post("/auth/refresh", headers={"Authorization": f"Bearer {token}"})
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]
        assert new_token != token  # Should be a new token

        # 6. Logout
        logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {new_token}"})
        assert logout_response.status_code == 200