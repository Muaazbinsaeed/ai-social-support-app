"""
Comprehensive tests for User Management APIs
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.user_management.user_models import User
from app.user_management.user_service import hash_password

client = TestClient(app)

class TestUserManagementAPIs:
    """Test suite for User Management endpoints"""

    def setup_method(self):
        """Set up test data before each test"""
        self.test_user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "securepassword123",
            "full_name": "Test User"
        }

        self.admin_user_data = {
            "username": "admin123",
            "email": "admin@example.com",
            "password": "adminpassword123",
            "full_name": "Admin User"
        }

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create an authenticated user and return access token"""
        # Create test user
        user = User(
            username=self.test_user_data["username"],
            email=self.test_user_data["email"],
            password_hash=hash_password(self.test_user_data["password"]),
            full_name=self.test_user_data["full_name"],
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()

        # Login to get token
        login_response = client.post("/auth/login", json={
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        })

        assert login_response.status_code == 200
        return login_response.json()["access_token"]

    @pytest.fixture
    def authenticated_admin_token(self, db_session):
        """Create an authenticated admin user and return access token"""
        # Create admin user
        admin_user = User(
            username=self.admin_user_data["username"],
            email=self.admin_user_data["email"],
            password_hash=hash_password(self.admin_user_data["password"]),
            full_name=self.admin_user_data["full_name"],
            is_active=True,
            is_verified=True,
            is_admin=True
        )
        db_session.add(admin_user)
        db_session.commit()

        # Login to get token
        login_response = client.post("/auth/login", json={
            "username": self.admin_user_data["username"],
            "password": self.admin_user_data["password"]
        })

        assert login_response.status_code == 200
        return login_response.json()["access_token"]

    def test_get_user_profile_success(self, authenticated_user_token):
        """Test successful user profile retrieval"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        response = client.get("/users/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == self.test_user_data["username"]
        assert data["email"] == self.test_user_data["email"]
        assert data["full_name"] == self.test_user_data["full_name"]
        assert "id" in data
        assert "created_at" in data
        assert data["is_active"] == True
        assert data["is_verified"] == True

    def test_get_user_profile_unauthorized(self):
        """Test user profile retrieval without authentication"""
        response = client.get("/users/profile")

        assert response.status_code == 401

    def test_update_user_profile_success(self, authenticated_user_token):
        """Test successful user profile update"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        update_data = {
            "full_name": "Updated Full Name",
            "phone": "+971501234567"
        }

        response = client.put("/users/profile", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["phone"] == update_data["phone"]

    def test_update_user_profile_email_conflict(self, authenticated_user_token, db_session):
        """Test profile update with conflicting email"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create another user with conflicting email
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=hash_password("password"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        update_data = {
            "email": "other@example.com"
        }

        response = client.put("/users/profile", json=update_data, headers=headers)

        assert response.status_code == 409
        assert "EMAIL_ALREADY_EXISTS" in response.json()["detail"]["error"]

    def test_change_password_success(self, authenticated_user_token):
        """Test successful password change"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        password_data = {
            "current_password": self.test_user_data["password"],
            "new_password": "newsecurepassword123",
            "confirm_password": "newsecurepassword123"
        }

        response = client.post("/users/change-password", json=password_data, headers=headers)

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_wrong_current(self, authenticated_user_token):
        """Test password change with wrong current password"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newsecurepassword123",
            "confirm_password": "newsecurepassword123"
        }

        response = client.post("/users/change-password", json=password_data, headers=headers)

        assert response.status_code == 400
        assert "INVALID_CURRENT_PASSWORD" in response.json()["detail"]["error"]

    def test_change_password_mismatch(self, authenticated_user_token):
        """Test password change with mismatched confirmation"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        password_data = {
            "current_password": self.test_user_data["password"],
            "new_password": "newsecurepassword123",
            "confirm_password": "differentpassword123"
        }

        response = client.post("/users/change-password", json=password_data, headers=headers)

        assert response.status_code == 400
        assert "PASSWORD_MISMATCH" in response.json()["detail"]["error"]

    def test_change_password_weak(self, authenticated_user_token):
        """Test password change with weak password"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        password_data = {
            "current_password": self.test_user_data["password"],
            "new_password": "weak",
            "confirm_password": "weak"
        }

        response = client.post("/users/change-password", json=password_data, headers=headers)

        assert response.status_code == 400
        assert "WEAK_PASSWORD" in response.json()["detail"]["error"]

    def test_delete_user_account(self, authenticated_user_token):
        """Test user account deletion (soft delete)"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        response = client.delete("/users/account", headers=headers)

        assert response.status_code == 200
        assert "Account deleted successfully" in response.json()["message"]

    def test_list_users_admin_success(self, authenticated_admin_token):
        """Test admin listing all users"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        response = client.get("/users/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["users"], list)

    def test_list_users_admin_with_filters(self, authenticated_admin_token):
        """Test admin listing users with filters"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        params = {
            "page": 1,
            "page_size": 5,
            "search": "admin",
            "is_active": True
        }

        response = client.get("/users/", params=params, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_list_users_non_admin_forbidden(self, authenticated_user_token):
        """Test non-admin user accessing admin endpoint"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        response = client.get("/users/", headers=headers)

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_get_user_by_id_admin(self, authenticated_admin_token, db_session):
        """Test admin getting user by ID"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        # Create a test user to retrieve
        test_user = User(
            username="targetuser",
            email="target@example.com",
            password_hash=hash_password("password"),
            is_active=True
        )
        db_session.add(test_user)
        db_session.commit()

        response = client.get(f"/users/{test_user.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "targetuser"
        assert data["email"] == "target@example.com"

    def test_get_user_by_id_not_found(self, authenticated_admin_token):
        """Test admin getting non-existent user"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        fake_user_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/users/{fake_user_id}", headers=headers)

        assert response.status_code == 404
        assert "USER_NOT_FOUND" in response.json()["detail"]["error"]

    def test_update_user_activation_admin(self, authenticated_admin_token, db_session):
        """Test admin updating user activation status"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        # Create a test user to deactivate
        test_user = User(
            username="activetestuser",
            email="active@example.com",
            password_hash=hash_password("password"),
            is_active=True
        )
        db_session.add(test_user)
        db_session.commit()

        activation_data = {
            "is_active": False,
            "reason": "Policy violation"
        }

        response = client.put(f"/users/{test_user.id}/activation",
                            json=activation_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "deactivated" in data["message"]
        assert data["is_active"] == False
        assert data["reason"] == "Policy violation"

    def test_update_user_activation_self_deactivation_forbidden(self, authenticated_admin_token, db_session):
        """Test admin cannot deactivate their own account"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        # Get admin user ID from token
        profile_response = client.get("/users/profile", headers=headers)
        admin_user_id = profile_response.json()["id"]

        activation_data = {
            "is_active": False,
            "reason": "Self deactivation test"
        }

        response = client.put(f"/users/{admin_user_id}/activation",
                            json=activation_data, headers=headers)

        assert response.status_code == 400
        assert "SELF_DEACTIVATION_FORBIDDEN" in response.json()["detail"]["error"]

    def test_get_user_stats_admin(self, authenticated_admin_token):
        """Test admin getting user statistics"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        response = client.get("/users/stats/overview", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "verified_users" in data
        assert "registrations_this_month" in data
        assert "last_login_stats" in data
        assert isinstance(data["total_users"], int)
        assert isinstance(data["active_users"], int)

    def test_user_stats_non_admin_forbidden(self, authenticated_user_token):
        """Test non-admin accessing user statistics"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        response = client.get("/users/stats/overview", headers=headers)

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_user_profile_edge_cases(self, authenticated_user_token):
        """Test user profile edge cases and validation"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Test with empty update
        response = client.put("/users/profile", json={}, headers=headers)
        assert response.status_code == 200  # Should accept empty updates

        # Test with invalid email format
        invalid_email_data = {"email": "invalid-email-format"}
        response = client.put("/users/profile", json=invalid_email_data, headers=headers)
        assert response.status_code == 422  # Validation error

    def test_pagination_and_filtering_comprehensive(self, authenticated_admin_token, db_session):
        """Test comprehensive pagination and filtering scenarios"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        # Create multiple test users
        for i in range(15):
            user = User(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash=hash_password("password"),
                is_active=i % 2 == 0,  # Alternate active/inactive
                is_verified=i % 3 == 0  # Some verified
            )
            db_session.add(user)
        db_session.commit()

        # Test pagination
        response = client.get("/users/?page=1&page_size=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 5
        assert data["page"] == 1
        assert data["page_size"] == 5

        # Test filtering by active status
        response = client.get("/users/?is_active=true", headers=headers)
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["is_active"] == True

        # Test search functionality
        response = client.get("/users/?search=testuser1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should find users with "testuser1" in username

    def test_user_management_security_edge_cases(self):
        """Test security edge cases in user management"""

        # Test accessing endpoints without authorization
        endpoints_to_test = [
            ("GET", "/users/profile"),
            ("PUT", "/users/profile"),
            ("POST", "/users/change-password"),
            ("DELETE", "/users/account"),
            ("GET", "/users/"),
            ("GET", "/users/00000000-0000-0000-0000-000000000000"),
            ("GET", "/users/stats/overview")
        ]

        for method, endpoint in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"

    def test_malformed_requests(self, authenticated_user_token):
        """Test handling of malformed requests"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Test malformed JSON
        response = client.put("/users/profile",
                            data="invalid json",
                            headers={**headers, "Content-Type": "application/json"})
        assert response.status_code in [400, 422]

        # Test missing required fields in password change
        response = client.post("/users/change-password",
                             json={"current_password": "test"},
                             headers=headers)
        assert response.status_code == 422

    def test_concurrent_user_operations(self, authenticated_admin_token, db_session):
        """Test handling of concurrent user operations"""
        headers = {"Authorization": f"Bearer {authenticated_admin_token}"}

        # Create a test user
        test_user = User(
            username="concurrentuser",
            email="concurrent@example.com",
            password_hash=hash_password("password"),
            is_active=True
        )
        db_session.add(test_user)
        db_session.commit()

        # Simulate concurrent updates (in real scenario, this would be multiple threads)
        activation_data1 = {"is_active": False, "reason": "First update"}
        activation_data2 = {"is_active": True, "reason": "Second update"}

        response1 = client.put(f"/users/{test_user.id}/activation",
                              json=activation_data1, headers=headers)
        response2 = client.put(f"/users/{test_user.id}/activation",
                              json=activation_data2, headers=headers)

        # Both should succeed (last one wins)
        assert response1.status_code == 200
        assert response2.status_code == 200