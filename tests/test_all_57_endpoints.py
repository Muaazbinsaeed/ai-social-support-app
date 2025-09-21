"""
Comprehensive Test Suite for All 57 API Endpoints
Social Security AI Workflow Automation System

This test suite covers all 57 endpoints across 10 router modules:
- Authentication (7 endpoints)
- Health Checks (3 endpoints)
- User Management (8 endpoints)
- Document Upload (4 endpoints)
- Document Management (8 endpoints)
- OCR Processing (5 endpoints)
- Chatbot (6 endpoints)
- Decision Making (5 endpoints)
- Multimodal Analysis (4 endpoints)
- Applications (4 endpoints)
- Workflow (3 endpoints)
"""

import pytest
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from app.main import app

# Test configuration
client = TestClient(app)
BASE_URL = "http://localhost:8000"

# Test data storage
test_data = {
    "users": [],
    "tokens": {},
    "applications": [],
    "documents": [],
    "sessions": []
}

class TestResults:
    """Track test results and statistics"""
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.results = {}
        self.coverage = {}

    def add_result(self, module: str, endpoint: str, method: str, status: str, details: Dict = None):
        """Add test result"""
        self.total_tests += 1
        if status == "passed":
            self.passed_tests += 1
        elif status == "failed":
            self.failed_tests += 1
        elif status == "skipped":
            self.skipped_tests += 1

        if module not in self.results:
            self.results[module] = {}

        self.results[module][f"{method} {endpoint}"] = {
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

    def get_summary(self):
        """Get test summary"""
        return {
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "skipped": self.skipped_tests,
            "success_rate": f"{(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0%",
            "results_by_module": self.results
        }

# Global test results tracker
test_results = TestResults()

def create_test_user(username_suffix: str = None) -> Dict[str, Any]:
    """Create a test user and return credentials"""
    if username_suffix is None:
        username_suffix = str(int(datetime.now().timestamp()))

    user_data = {
        "username": f"testuser_{username_suffix}",
        "email": f"test_{username_suffix}@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    return user_data

def get_auth_token(user_data: Dict[str, Any]) -> Optional[str]:
    """Get authentication token for user"""
    try:
        # Try to register user first
        response = client.post("/auth/register", json=user_data)

        # Then login to get token
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = client.post("/auth/login", json=login_data)

        if response.status_code == 200:
            token = response.json().get("access_token")
            return token
        return None
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def get_auth_headers(token: str = None) -> Dict[str, str]:
    """Get authentication headers"""
    if token is None:
        # Create a new user and get token
        user_data = create_test_user()
        token = get_auth_token(user_data)

    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestAuthenticationEndpoints:
    """Test authentication endpoints (7 endpoints)"""

    def test_01_register_user(self):
        """POST /auth/register"""
        try:
            user_data = create_test_user("register_test")
            response = client.post("/auth/register", json=user_data)

            if response.status_code == 201:
                data = response.json()
                assert "id" in data
                assert data["username"] == user_data["username"]
                test_data["users"].append(user_data)
                test_results.add_result("authentication", "/auth/register", "POST", "passed",
                                      {"status_code": 201, "user_created": True})
            else:
                test_results.add_result("authentication", "/auth/register", "POST", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("authentication", "/auth/register", "POST", "failed",
                                  {"error": str(e)})

    def test_02_login_user(self):
        """POST /auth/login"""
        try:
            user_data = create_test_user("login_test")
            # Register first
            client.post("/auth/register", json=user_data)

            # Then login
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            response = client.post("/auth/login", json=login_data)

            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data
                assert "token_type" in data
                test_data["tokens"][user_data["username"]] = data["access_token"]
                test_results.add_result("authentication", "/auth/login", "POST", "passed",
                                      {"status_code": 200, "token_received": True})
            else:
                test_results.add_result("authentication", "/auth/login", "POST", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("authentication", "/auth/login", "POST", "failed",
                                  {"error": str(e)})

    def test_03_get_current_user(self):
        """GET /auth/me"""
        try:
            user_data = create_test_user("me_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/auth/me", headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    assert "username" in data
                    test_results.add_result("authentication", "/auth/me", "GET", "passed",
                                          {"status_code": 200, "user_info_retrieved": True})
                else:
                    test_results.add_result("authentication", "/auth/me", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("authentication", "/auth/me", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("authentication", "/auth/me", "GET", "failed",
                                  {"error": str(e)})

    def test_04_get_auth_status(self):
        """GET /auth/status"""
        try:
            user_data = create_test_user("status_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/auth/status", headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    assert "authenticated" in data
                    test_results.add_result("authentication", "/auth/status", "GET", "passed",
                                          {"status_code": 200, "status_retrieved": True})
                else:
                    test_results.add_result("authentication", "/auth/status", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("authentication", "/auth/status", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("authentication", "/auth/status", "GET", "failed",
                                  {"error": str(e)})

    def test_05_update_password(self):
        """PUT /auth/password"""
        try:
            user_data = create_test_user("password_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                password_data = {
                    "current_password": user_data["password"],
                    "new_password": "newpassword123"
                }
                response = client.put("/auth/password", headers=headers, json=password_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("authentication", "/auth/password", "PUT", "passed",
                                          {"status_code": response.status_code, "password_updated": True})
                else:
                    test_results.add_result("authentication", "/auth/password", "PUT", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("authentication", "/auth/password", "PUT", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("authentication", "/auth/password", "PUT", "failed",
                                  {"error": str(e)})

    def test_06_logout_user(self):
        """POST /auth/logout"""
        try:
            user_data = create_test_user("logout_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.post("/auth/logout", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("authentication", "/auth/logout", "POST", "passed",
                                          {"status_code": 200, "logout_successful": True})
                else:
                    test_results.add_result("authentication", "/auth/logout", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("authentication", "/auth/logout", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("authentication", "/auth/logout", "POST", "failed",
                                  {"error": str(e)})

    def test_07_refresh_token(self):
        """POST /auth/refresh"""
        try:
            user_data = create_test_user("refresh_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.post("/auth/refresh", headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    assert "access_token" in data
                    test_results.add_result("authentication", "/auth/refresh", "POST", "passed",
                                          {"status_code": 200, "token_refreshed": True})
                else:
                    test_results.add_result("authentication", "/auth/refresh", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("authentication", "/auth/refresh", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("authentication", "/auth/refresh", "POST", "failed",
                                  {"error": str(e)})


class TestHealthEndpoints:
    """Test health check endpoints (3 endpoints)"""

    def test_01_comprehensive_health_check(self):
        """GET /health/"""
        try:
            response = client.get("/health/")

            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                test_results.add_result("health", "/health/", "GET", "passed",
                                      {"status_code": 200, "health_check_working": True})
            else:
                test_results.add_result("health", "/health/", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("health", "/health/", "GET", "failed",
                                  {"error": str(e)})

    def test_02_basic_health_check(self):
        """GET /health/basic"""
        try:
            response = client.get("/health/basic")

            if response.status_code == 200:
                test_results.add_result("health", "/health/basic", "GET", "passed",
                                      {"status_code": 200, "basic_health_working": True})
            else:
                test_results.add_result("health", "/health/basic", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("health", "/health/basic", "GET", "failed",
                                  {"error": str(e)})

    def test_03_database_health_check(self):
        """GET /health/database"""
        try:
            response = client.get("/health/database")

            if response.status_code == 200:
                test_results.add_result("health", "/health/database", "GET", "passed",
                                      {"status_code": 200, "database_health_working": True})
            else:
                test_results.add_result("health", "/health/database", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("health", "/health/database", "GET", "failed",
                                  {"error": str(e)})


class TestUserManagementEndpoints:
    """Test user management endpoints (8 endpoints)"""

    def test_01_get_user_profile(self):
        """GET /users/profile"""
        try:
            user_data = create_test_user("profile_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/users/profile", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("user_management", "/users/profile", "GET", "passed",
                                          {"status_code": 200, "profile_retrieved": True})
                else:
                    test_results.add_result("user_management", "/users/profile", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/profile", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/profile", "GET", "failed",
                                  {"error": str(e)})

    def test_02_update_user_profile(self):
        """PUT /users/profile"""
        try:
            user_data = create_test_user("profile_update_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                update_data = {
                    "full_name": "Updated Test User",
                    "phone": "+971501234567"
                }
                response = client.put("/users/profile", headers=headers, json=update_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("user_management", "/users/profile", "PUT", "passed",
                                          {"status_code": response.status_code, "profile_updated": True})
                else:
                    test_results.add_result("user_management", "/users/profile", "PUT", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/profile", "PUT", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/profile", "PUT", "failed",
                                  {"error": str(e)})

    def test_03_change_password(self):
        """POST /users/change-password"""
        try:
            user_data = create_test_user("change_password_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                password_data = {
                    "current_password": user_data["password"],
                    "new_password": "newpassword456"
                }
                response = client.post("/users/change-password", headers=headers, json=password_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("user_management", "/users/change-password", "POST", "passed",
                                          {"status_code": response.status_code, "password_changed": True})
                else:
                    test_results.add_result("user_management", "/users/change-password", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/change-password", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/change-password", "POST", "failed",
                                  {"error": str(e)})

    def test_04_delete_user_account(self):
        """DELETE /users/account"""
        try:
            user_data = create_test_user("delete_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.delete("/users/account", headers=headers)

                if response.status_code in [200, 204]:
                    test_results.add_result("user_management", "/users/account", "DELETE", "passed",
                                          {"status_code": response.status_code, "account_deleted": True})
                else:
                    test_results.add_result("user_management", "/users/account", "DELETE", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/account", "DELETE", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/account", "DELETE", "failed",
                                  {"error": str(e)})

    def test_05_list_users_admin(self):
        """GET /users/ (Admin only)"""
        try:
            # This test expects to fail unless we have admin credentials
            user_data = create_test_user("list_users_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/users/", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("user_management", "/users/", "GET", "passed",
                                          {"status_code": 200, "users_listed": True})
                elif response.status_code == 403:
                    # Expected - user is not admin
                    test_results.add_result("user_management", "/users/", "GET", "passed",
                                          {"status_code": 403, "admin_protection_working": True})
                else:
                    test_results.add_result("user_management", "/users/", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/", "GET", "failed",
                                  {"error": str(e)})

    def test_06_get_user_by_id_admin(self):
        """GET /users/{user_id} (Admin only)"""
        try:
            user_data = create_test_user("get_user_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_user_id = str(uuid.uuid4())
                response = client.get(f"/users/{fake_user_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("user_management", "/users/{user_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                elif response.status_code == 403:
                    # Expected - user is not admin
                    test_results.add_result("user_management", "/users/{user_id}", "GET", "passed",
                                          {"status_code": 403, "admin_protection_working": True})
                else:
                    test_results.add_result("user_management", "/users/{user_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/{user_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/{user_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_07_update_user_activation_admin(self):
        """PUT /users/{user_id}/activation (Admin only)"""
        try:
            user_data = create_test_user("activation_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_user_id = str(uuid.uuid4())
                activation_data = {"is_active": False}
                response = client.put(f"/users/{fake_user_id}/activation", headers=headers, json=activation_data)

                if response.status_code in [200, 404]:
                    test_results.add_result("user_management", "/users/{user_id}/activation", "PUT", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                elif response.status_code == 403:
                    # Expected - user is not admin
                    test_results.add_result("user_management", "/users/{user_id}/activation", "PUT", "passed",
                                          {"status_code": 403, "admin_protection_working": True})
                else:
                    test_results.add_result("user_management", "/users/{user_id}/activation", "PUT", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/{user_id}/activation", "PUT", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/{user_id}/activation", "PUT", "failed",
                                  {"error": str(e)})

    def test_08_get_user_stats_admin(self):
        """GET /users/stats/overview (Admin only)"""
        try:
            user_data = create_test_user("stats_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/users/stats/overview", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("user_management", "/users/stats/overview", "GET", "passed",
                                          {"status_code": 200, "stats_retrieved": True})
                elif response.status_code == 403:
                    # Expected - user is not admin
                    test_results.add_result("user_management", "/users/stats/overview", "GET", "passed",
                                          {"status_code": 403, "admin_protection_working": True})
                else:
                    test_results.add_result("user_management", "/users/stats/overview", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("user_management", "/users/stats/overview", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("user_management", "/users/stats/overview", "GET", "failed",
                                  {"error": str(e)})


class TestDocumentEndpoints:
    """Test document upload endpoints (4 endpoints)"""

    def test_01_get_supported_file_types(self):
        """GET /documents/types"""
        try:
            response = client.get("/documents/types")

            if response.status_code == 200:
                data = response.json()
                assert "supported_types" in data
                test_results.add_result("documents", "/documents/types", "GET", "passed",
                                      {"status_code": 200, "file_types_retrieved": True})
            else:
                test_results.add_result("documents", "/documents/types", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("documents", "/documents/types", "GET", "failed",
                                  {"error": str(e)})

    def test_02_upload_documents(self):
        """POST /documents/upload"""
        try:
            user_data = create_test_user("upload_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}

                # Create mock files
                files = {
                    "bank_statement": ("test_bank_statement.pdf", b"fake pdf content", "application/pdf"),
                    "emirates_id": ("test_emirates_id.jpg", b"fake image content", "image/jpeg")
                }

                response = client.post("/documents/upload", headers=headers, files=files)

                if response.status_code in [200, 201, 202]:
                    test_results.add_result("documents", "/documents/upload", "POST", "passed",
                                          {"status_code": response.status_code, "documents_uploaded": True})
                else:
                    test_results.add_result("documents", "/documents/upload", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("documents", "/documents/upload", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("documents", "/documents/upload", "POST", "failed",
                                  {"error": str(e)})

    def test_03_get_document_status(self):
        """GET /documents/status/{document_id}"""
        try:
            user_data = create_test_user("status_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.get(f"/documents/status/{fake_document_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("documents", "/documents/status/{document_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("documents", "/documents/status/{document_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("documents", "/documents/status/{document_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("documents", "/documents/status/{document_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_04_delete_document(self):
        """DELETE /documents/{document_id}"""
        try:
            user_data = create_test_user("delete_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.delete(f"/documents/{fake_document_id}", headers=headers)

                if response.status_code in [200, 204, 404]:
                    test_results.add_result("documents", "/documents/{document_id}", "DELETE", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("documents", "/documents/{document_id}", "DELETE", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("documents", "/documents/{document_id}", "DELETE", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("documents", "/documents/{document_id}", "DELETE", "failed",
                                  {"error": str(e)})


class TestDocumentManagementEndpoints:
    """Test document management endpoints (8 endpoints)"""

    def test_01_get_supported_types(self):
        """GET /document-management/types/supported"""
        try:
            response = client.get("/document-management/types/supported")

            if response.status_code == 200:
                test_results.add_result("document_management", "/document-management/types/supported", "GET", "passed",
                                      {"status_code": 200, "supported_types_retrieved": True})
            else:
                test_results.add_result("document_management", "/document-management/types/supported", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/types/supported", "GET", "failed",
                                  {"error": str(e)})

    def test_02_upload_document(self):
        """POST /document-management/upload"""
        try:
            user_data = create_test_user("doc_mgmt_upload_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}

                files = {
                    "file": ("test_document.pdf", b"fake pdf content", "application/pdf")
                }
                data = {
                    "document_type": "bank_statement",
                    "description": "Test document upload"
                }

                response = client.post("/document-management/upload", headers=headers, files=files, data=data)

                if response.status_code in [200, 201, 202]:
                    test_results.add_result("document_management", "/document-management/upload", "POST", "passed",
                                          {"status_code": response.status_code, "document_uploaded": True})
                else:
                    test_results.add_result("document_management", "/document-management/upload", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/upload", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/upload", "POST", "failed",
                                  {"error": str(e)})

    def test_03_list_documents(self):
        """GET /document-management/"""
        try:
            user_data = create_test_user("list_docs_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/document-management/", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("document_management", "/document-management/", "GET", "passed",
                                          {"status_code": 200, "documents_listed": True})
                else:
                    test_results.add_result("document_management", "/document-management/", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/", "GET", "failed",
                                  {"error": str(e)})

    def test_04_get_document(self):
        """GET /document-management/{document_id}"""
        try:
            user_data = create_test_user("get_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.get(f"/document-management/{fake_document_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("document_management", "/document-management/{document_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("document_management", "/document-management/{document_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/{document_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/{document_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_05_update_document(self):
        """PUT /document-management/{document_id}"""
        try:
            user_data = create_test_user("update_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                update_data = {
                    "description": "Updated document description",
                    "structured_data": {"key": "value"}
                }
                response = client.put(f"/document-management/{fake_document_id}", headers=headers, json=update_data)

                if response.status_code in [200, 404]:
                    test_results.add_result("document_management", "/document-management/{document_id}", "PUT", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("document_management", "/document-management/{document_id}", "PUT", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/{document_id}", "PUT", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/{document_id}", "PUT", "failed",
                                  {"error": str(e)})

    def test_06_delete_document_mgmt(self):
        """DELETE /document-management/{document_id}"""
        try:
            user_data = create_test_user("delete_doc_mgmt_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.delete(f"/document-management/{fake_document_id}", headers=headers)

                if response.status_code in [200, 204, 404]:
                    test_results.add_result("document_management", "/document-management/{document_id}", "DELETE", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("document_management", "/document-management/{document_id}", "DELETE", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/{document_id}", "DELETE", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/{document_id}", "DELETE", "failed",
                                  {"error": str(e)})

    def test_07_download_document(self):
        """GET /document-management/{document_id}/download"""
        try:
            user_data = create_test_user("download_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.get(f"/document-management/{fake_document_id}/download", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("document_management", "/document-management/{document_id}/download", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("document_management", "/document-management/{document_id}/download", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/{document_id}/download", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/{document_id}/download", "GET", "failed",
                                  {"error": str(e)})

    def test_08_get_processing_logs(self):
        """GET /document-management/{document_id}/processing-logs"""
        try:
            user_data = create_test_user("processing_logs_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                response = client.get(f"/document-management/{fake_document_id}/processing-logs", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("document_management", "/document-management/{document_id}/processing-logs", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("document_management", "/document-management/{document_id}/processing-logs", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("document_management", "/document-management/{document_id}/processing-logs", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("document_management", "/document-management/{document_id}/processing-logs", "GET", "failed",
                                  {"error": str(e)})


class TestOCREndpoints:
    """Test OCR processing endpoints (5 endpoints)"""

    def test_01_ocr_health_check(self):
        """GET /ocr/health"""
        try:
            response = client.get("/ocr/health")

            if response.status_code == 200:
                test_results.add_result("ocr", "/ocr/health", "GET", "passed",
                                      {"status_code": 200, "ocr_health_working": True})
            else:
                test_results.add_result("ocr", "/ocr/health", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("ocr", "/ocr/health", "GET", "failed",
                                  {"error": str(e)})

    def test_02_ocr_document(self):
        """POST /ocr/documents/{document_id}"""
        try:
            user_data = create_test_user("ocr_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                ocr_data = {
                    "language_hints": ["en", "ar"],
                    "preprocess": True
                }
                response = client.post(f"/ocr/documents/{fake_document_id}", headers=headers, json=ocr_data)

                if response.status_code in [200, 202, 404]:
                    test_results.add_result("ocr", "/ocr/documents/{document_id}", "POST", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("ocr", "/ocr/documents/{document_id}", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("ocr", "/ocr/documents/{document_id}", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("ocr", "/ocr/documents/{document_id}", "POST", "failed",
                                  {"error": str(e)})

    def test_03_batch_ocr(self):
        """POST /ocr/batch"""
        try:
            user_data = create_test_user("batch_ocr_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                batch_data = {
                    "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                    "language_hints": ["en"]
                }
                response = client.post("/ocr/batch", headers=headers, json=batch_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("ocr", "/ocr/batch", "POST", "passed",
                                          {"status_code": response.status_code, "batch_ocr_accessible": True})
                else:
                    test_results.add_result("ocr", "/ocr/batch", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("ocr", "/ocr/batch", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("ocr", "/ocr/batch", "POST", "failed",
                                  {"error": str(e)})

    def test_04_direct_ocr(self):
        """POST /ocr/direct"""
        try:
            user_data = create_test_user("direct_ocr_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                # Use base64 encoded simple image data
                import base64
                fake_image_data = base64.b64encode(b"fake image data").decode()

                ocr_data = {
                    "image_data": fake_image_data,
                    "language_hints": ["en"]
                }
                response = client.post("/ocr/direct", headers=headers, json=ocr_data)

                if response.status_code in [200, 400]:  # 400 might be expected for fake data
                    test_results.add_result("ocr", "/ocr/direct", "POST", "passed",
                                          {"status_code": response.status_code, "direct_ocr_accessible": True})
                else:
                    test_results.add_result("ocr", "/ocr/direct", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("ocr", "/ocr/direct", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("ocr", "/ocr/direct", "POST", "failed",
                                  {"error": str(e)})

    def test_05_upload_and_extract(self):
        """POST /ocr/upload-and-extract"""
        try:
            user_data = create_test_user("upload_extract_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}

                files = {
                    "file": ("test_image.jpg", b"fake image content", "image/jpeg")
                }
                data = {
                    "language_hints": "en"
                }

                response = client.post("/ocr/upload-and-extract", headers=headers, files=files, data=data)

                if response.status_code in [200, 202, 400]:  # 400 might be expected for fake data
                    test_results.add_result("ocr", "/ocr/upload-and-extract", "POST", "passed",
                                          {"status_code": response.status_code, "upload_extract_accessible": True})
                else:
                    test_results.add_result("ocr", "/ocr/upload-and-extract", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("ocr", "/ocr/upload-and-extract", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("ocr", "/ocr/upload-and-extract", "POST", "failed",
                                  {"error": str(e)})


class TestChatbotEndpoints:
    """Test chatbot endpoints (6 endpoints - excluding WebSocket)"""

    def test_01_chatbot_health_check(self):
        """GET /chatbot/health"""
        try:
            response = client.get("/chatbot/health")

            if response.status_code == 200:
                test_results.add_result("chatbot", "/chatbot/health", "GET", "passed",
                                      {"status_code": 200, "chatbot_health_working": True})
            else:
                test_results.add_result("chatbot", "/chatbot/health", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/health", "GET", "failed",
                                  {"error": str(e)})

    def test_02_get_quick_help(self):
        """GET /chatbot/quick-help"""
        try:
            response = client.get("/chatbot/quick-help")

            if response.status_code == 200:
                test_results.add_result("chatbot", "/chatbot/quick-help", "GET", "passed",
                                      {"status_code": 200, "quick_help_working": True})
            else:
                test_results.add_result("chatbot", "/chatbot/quick-help", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/quick-help", "GET", "failed",
                                  {"error": str(e)})

    def test_03_chat_message(self):
        """POST /chatbot/chat"""
        try:
            user_data = create_test_user("chat_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                chat_data = {
                    "message": "Hello, can you help me with my application?",
                    "session_id": str(uuid.uuid4())
                }
                response = client.post("/chatbot/chat", headers=headers, json=chat_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("chatbot", "/chatbot/chat", "POST", "passed",
                                          {"status_code": response.status_code, "chat_message_working": True})
                else:
                    test_results.add_result("chatbot", "/chatbot/chat", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("chatbot", "/chatbot/chat", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/chat", "POST", "failed",
                                  {"error": str(e)})

    def test_04_get_chat_sessions(self):
        """GET /chatbot/sessions"""
        try:
            user_data = create_test_user("chat_sessions_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/chatbot/sessions", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("chatbot", "/chatbot/sessions", "GET", "passed",
                                          {"status_code": 200, "chat_sessions_working": True})
                else:
                    test_results.add_result("chatbot", "/chatbot/sessions", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("chatbot", "/chatbot/sessions", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/sessions", "GET", "failed",
                                  {"error": str(e)})

    def test_05_get_chat_session(self):
        """GET /chatbot/sessions/{session_id}"""
        try:
            user_data = create_test_user("chat_session_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_session_id = str(uuid.uuid4())
                response = client.get(f"/chatbot/sessions/{fake_session_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_06_delete_chat_session(self):
        """DELETE /chatbot/sessions/{session_id}"""
        try:
            user_data = create_test_user("delete_chat_session_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_session_id = str(uuid.uuid4())
                response = client.delete(f"/chatbot/sessions/{fake_session_id}", headers=headers)

                if response.status_code in [200, 204, 404]:
                    test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "DELETE", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "DELETE", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "DELETE", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("chatbot", "/chatbot/sessions/{session_id}", "DELETE", "failed",
                                  {"error": str(e)})


class TestDecisionEndpoints:
    """Test decision making endpoints (5 endpoints)"""

    def test_01_decision_health_check(self):
        """GET /decisions/health"""
        try:
            response = client.get("/decisions/health")

            if response.status_code == 200:
                test_results.add_result("decisions", "/decisions/health", "GET", "passed",
                                      {"status_code": 200, "decision_health_working": True})
            else:
                test_results.add_result("decisions", "/decisions/health", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("decisions", "/decisions/health", "GET", "failed",
                                  {"error": str(e)})

    def test_02_get_decision_criteria(self):
        """GET /decisions/criteria"""
        try:
            response = client.get("/decisions/criteria")

            if response.status_code == 200:
                test_results.add_result("decisions", "/decisions/criteria", "GET", "passed",
                                      {"status_code": 200, "decision_criteria_working": True})
            else:
                test_results.add_result("decisions", "/decisions/criteria", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("decisions", "/decisions/criteria", "GET", "failed",
                                  {"error": str(e)})

    def test_03_make_decision(self):
        """POST /decisions/make-decision"""
        try:
            user_data = create_test_user("make_decision_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                decision_data = {
                    "application_id": str(uuid.uuid4()),
                    "factors": {
                        "income": 5000,
                        "balance": 2000,
                        "employment_status": "employed"
                    }
                }
                response = client.post("/decisions/make-decision", headers=headers, json=decision_data)

                if response.status_code in [200, 202, 404]:
                    test_results.add_result("decisions", "/decisions/make-decision", "POST", "passed",
                                          {"status_code": response.status_code, "decision_endpoint_accessible": True})
                else:
                    test_results.add_result("decisions", "/decisions/make-decision", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("decisions", "/decisions/make-decision", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("decisions", "/decisions/make-decision", "POST", "failed",
                                  {"error": str(e)})

    def test_04_batch_decisions(self):
        """POST /decisions/batch"""
        try:
            user_data = create_test_user("batch_decisions_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                batch_data = {
                    "applications": [
                        {
                            "application_id": str(uuid.uuid4()),
                            "factors": {"income": 4000, "balance": 1500}
                        },
                        {
                            "application_id": str(uuid.uuid4()),
                            "factors": {"income": 6000, "balance": 3000}
                        }
                    ]
                }
                response = client.post("/decisions/batch", headers=headers, json=batch_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("decisions", "/decisions/batch", "POST", "passed",
                                          {"status_code": response.status_code, "batch_decisions_accessible": True})
                else:
                    test_results.add_result("decisions", "/decisions/batch", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("decisions", "/decisions/batch", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("decisions", "/decisions/batch", "POST", "failed",
                                  {"error": str(e)})

    def test_05_explain_decision(self):
        """POST /decisions/explain/{decision_id}"""
        try:
            user_data = create_test_user("explain_decision_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_decision_id = str(uuid.uuid4())
                explain_data = {
                    "detail_level": "comprehensive"
                }
                response = client.post(f"/decisions/explain/{fake_decision_id}", headers=headers, json=explain_data)

                if response.status_code in [200, 404]:
                    test_results.add_result("decisions", "/decisions/explain/{decision_id}", "POST", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("decisions", "/decisions/explain/{decision_id}", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("decisions", "/decisions/explain/{decision_id}", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("decisions", "/decisions/explain/{decision_id}", "POST", "failed",
                                  {"error": str(e)})


class TestAnalysisEndpoints:
    """Test multimodal analysis endpoints (4 endpoints)"""

    def test_01_analyze_document(self):
        """POST /analysis/documents/{document_id}"""
        try:
            user_data = create_test_user("analyze_doc_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_document_id = str(uuid.uuid4())
                analysis_data = {
                    "analysis_type": "full",
                    "custom_prompt": "Analyze this document for financial information"
                }
                response = client.post(f"/analysis/documents/{fake_document_id}", headers=headers, json=analysis_data)

                if response.status_code in [200, 202, 404]:
                    test_results.add_result("analysis", "/analysis/documents/{document_id}", "POST", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("analysis", "/analysis/documents/{document_id}", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("analysis", "/analysis/documents/{document_id}", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("analysis", "/analysis/documents/{document_id}", "POST", "failed",
                                  {"error": str(e)})

    def test_02_bulk_analyze_documents(self):
        """POST /analysis/bulk"""
        try:
            user_data = create_test_user("bulk_analyze_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                bulk_data = {
                    "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                    "analysis_type": "financial"
                }
                response = client.post("/analysis/bulk", headers=headers, json=bulk_data)

                if response.status_code in [200, 202]:
                    test_results.add_result("analysis", "/analysis/bulk", "POST", "passed",
                                          {"status_code": response.status_code, "bulk_analysis_accessible": True})
                else:
                    test_results.add_result("analysis", "/analysis/bulk", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("analysis", "/analysis/bulk", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("analysis", "/analysis/bulk", "POST", "failed",
                                  {"error": str(e)})

    def test_03_multimodal_query(self):
        """POST /analysis/query"""
        try:
            user_data = create_test_user("multimodal_query_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                query_data = {
                    "question": "What is the monthly income shown in this document?",
                    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                }
                response = client.post("/analysis/query", headers=headers, json=query_data)

                if response.status_code in [200, 202, 400]:  # 400 might be expected for fake data
                    test_results.add_result("analysis", "/analysis/query", "POST", "passed",
                                          {"status_code": response.status_code, "multimodal_query_accessible": True})
                else:
                    test_results.add_result("analysis", "/analysis/query", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("analysis", "/analysis/query", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("analysis", "/analysis/query", "POST", "failed",
                                  {"error": str(e)})

    def test_04_upload_and_analyze(self):
        """POST /analysis/upload-and-analyze"""
        try:
            user_data = create_test_user("upload_analyze_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}

                files = {
                    "file": ("test_document.pdf", b"fake pdf content", "application/pdf")
                }
                data = {
                    "analysis_type": "financial",
                    "custom_prompt": "Extract financial information"
                }

                response = client.post("/analysis/upload-and-analyze", headers=headers, files=files, data=data)

                if response.status_code in [200, 202, 400]:  # 400 might be expected for fake data
                    test_results.add_result("analysis", "/analysis/upload-and-analyze", "POST", "passed",
                                          {"status_code": response.status_code, "upload_analyze_accessible": True})
                else:
                    test_results.add_result("analysis", "/analysis/upload-and-analyze", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("analysis", "/analysis/upload-and-analyze", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("analysis", "/analysis/upload-and-analyze", "POST", "failed",
                                  {"error": str(e)})


class TestApplicationEndpoints:
    """Test application endpoints (4 endpoints)"""

    def test_01_list_applications(self):
        """GET /applications/"""
        try:
            user_data = create_test_user("list_apps_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get("/applications/", headers=headers)

                if response.status_code == 200:
                    test_results.add_result("applications", "/applications/", "GET", "passed",
                                          {"status_code": 200, "applications_listed": True})
                else:
                    test_results.add_result("applications", "/applications/", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("applications", "/applications/", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("applications", "/applications/", "GET", "failed",
                                  {"error": str(e)})

    def test_02_get_application(self):
        """GET /applications/{application_id}"""
        try:
            user_data = create_test_user("get_app_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_app_id = str(uuid.uuid4())
                response = client.get(f"/applications/{fake_app_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("applications", "/applications/{application_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("applications", "/applications/{application_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("applications", "/applications/{application_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("applications", "/applications/{application_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_03_update_application(self):
        """PUT /applications/{application_id}"""
        try:
            user_data = create_test_user("update_app_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_app_id = str(uuid.uuid4())
                update_data = {
                    "full_name": "Updated Name",
                    "phone": "+971501234567"
                }
                response = client.put(f"/applications/{fake_app_id}", headers=headers, json=update_data)

                if response.status_code in [200, 404, 400]:  # 400 might be expected for non-draft status
                    test_results.add_result("applications", "/applications/{application_id}", "PUT", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("applications", "/applications/{application_id}", "PUT", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("applications", "/applications/{application_id}", "PUT", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("applications", "/applications/{application_id}", "PUT", "failed",
                                  {"error": str(e)})

    def test_04_get_application_results(self):
        """GET /applications/{application_id}/results"""
        try:
            user_data = create_test_user("app_results_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_app_id = str(uuid.uuid4())
                response = client.get(f"/applications/{fake_app_id}/results", headers=headers)

                if response.status_code in [200, 202, 404]:  # 202 if still processing
                    test_results.add_result("applications", "/applications/{application_id}/results", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("applications", "/applications/{application_id}/results", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("applications", "/applications/{application_id}/results", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("applications", "/applications/{application_id}/results", "GET", "failed",
                                  {"error": str(e)})


class TestWorkflowEndpoints:
    """Test workflow endpoints (3 endpoints)"""

    def test_01_start_application(self):
        """POST /workflow/start-application"""
        try:
            user_data = create_test_user("start_app_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                application_data = {
                    "full_name": "Test Applicant",
                    "emirates_id": "784-1990-1234567-8",
                    "phone": "+971501234567",
                    "email": "test.applicant@example.com"
                }
                response = client.post("/workflow/start-application", headers=headers, json=application_data)

                if response.status_code in [200, 201]:
                    data = response.json()
                    if "application_id" in data:
                        test_data["applications"].append(data["application_id"])
                    test_results.add_result("workflow", "/workflow/start-application", "POST", "passed",
                                          {"status_code": response.status_code, "application_created": True})
                else:
                    test_results.add_result("workflow", "/workflow/start-application", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("workflow", "/workflow/start-application", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("workflow", "/workflow/start-application", "POST", "failed",
                                  {"error": str(e)})

    def test_02_get_workflow_status(self):
        """GET /workflow/status/{application_id}"""
        try:
            user_data = create_test_user("workflow_status_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_app_id = str(uuid.uuid4())
                response = client.get(f"/workflow/status/{fake_app_id}", headers=headers)

                if response.status_code in [200, 404]:
                    test_results.add_result("workflow", "/workflow/status/{application_id}", "GET", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("workflow", "/workflow/status/{application_id}", "GET", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("workflow", "/workflow/status/{application_id}", "GET", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("workflow", "/workflow/status/{application_id}", "GET", "failed",
                                  {"error": str(e)})

    def test_03_process_application(self):
        """POST /workflow/process/{application_id}"""
        try:
            user_data = create_test_user("process_app_test")
            token = get_auth_token(user_data)

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                fake_app_id = str(uuid.uuid4())
                process_data = {
                    "force_retry": False,
                    "retry_failed_steps": False
                }
                response = client.post(f"/workflow/process/{fake_app_id}", headers=headers, json=process_data)

                if response.status_code in [200, 202, 404, 400]:  # 400 might be expected for invalid state
                    test_results.add_result("workflow", "/workflow/process/{application_id}", "POST", "passed",
                                          {"status_code": response.status_code, "endpoint_accessible": True})
                else:
                    test_results.add_result("workflow", "/workflow/process/{application_id}", "POST", "failed",
                                          {"status_code": response.status_code, "error": response.text})
            else:
                test_results.add_result("workflow", "/workflow/process/{application_id}", "POST", "failed",
                                      {"error": "Could not get auth token"})
        except Exception as e:
            test_results.add_result("workflow", "/workflow/process/{application_id}", "POST", "failed",
                                  {"error": str(e)})


class TestRootEndpoint:
    """Test root endpoint"""

    def test_root_endpoint(self):
        """GET /"""
        try:
            response = client.get("/")

            if response.status_code == 200:
                data = response.json()
                assert "name" in data
                assert "endpoints" in data
                test_results.add_result("root", "/", "GET", "passed",
                                      {"status_code": 200, "api_info_working": True})
            else:
                test_results.add_result("root", "/", "GET", "failed",
                                      {"status_code": response.status_code, "error": response.text})
        except Exception as e:
            test_results.add_result("root", "/", "GET", "failed",
                                  {"error": str(e)})


def run_all_tests():
    """Run all test classes"""
    print("🚀 Starting comprehensive API test suite for all 57 endpoints...\n")

    # Test classes in order
    test_classes = [
        TestRootEndpoint(),
        TestHealthEndpoints(),
        TestAuthenticationEndpoints(),
        TestUserManagementEndpoints(),
        TestDocumentEndpoints(),
        TestDocumentManagementEndpoints(),
        TestOCREndpoints(),
        TestChatbotEndpoints(),
        TestDecisionEndpoints(),
        TestAnalysisEndpoints(),
        TestApplicationEndpoints(),
        TestWorkflowEndpoints()
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"📋 Running {class_name}...")

        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
                print(f"  ✅ {method_name}")
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")

        print()

    # Print summary
    summary = test_results.get_summary()

    print("=" * 80)
    print("🎯 COMPREHENSIVE API TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"📊 Total Tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"⏭️ Skipped: {summary['skipped']}")
    print(f"📈 Success Rate: {summary['success_rate']}")
    print()

    # Print module breakdown
    print("📋 Results by Module:")
    print("-" * 40)
    for module, results in summary['results_by_module'].items():
        passed = sum(1 for r in results.values() if r['status'] == 'passed')
        total = len(results)
        success_rate = f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        print(f"{module:20} {passed:2}/{total:2} ({success_rate})")

    return summary


if __name__ == "__main__":
    print("🎯 Social Security AI - Comprehensive API Test Suite")
    print("Testing all 57 endpoints across 10 router modules")
    print("=" * 80)

    results = run_all_tests()

    # Save results to file
    with open("api_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to api_test_results.json")
    print("🏁 Test suite completed!")