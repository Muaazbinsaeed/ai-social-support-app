#!/usr/bin/env python3
"""
Comprehensive API Endpoint Tests
Covers all APIs, edge cases, and expected outputs
"""

import pytest
import requests
import json
import time
import random
import string
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from pathlib import Path


class APITestSuite:
    """Comprehensive API testing with edge cases and expected outputs"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None
        self.fixtures_path = Path(__file__).parent / "fixtures" / "sample_documents"

    def generate_test_user_data(self) -> Dict[str, str]:
        """Generate unique test user data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "username": f"testuser_{random_suffix}",
            "email": f"test_{random_suffix}@example.com",
            "password": "SecureTestPass123!",
            "full_name": f"Test User {random_suffix.upper()}"
        }

    def log_test(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "details": details or {}
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")


class TestHealthEndpoints(APITestSuite):
    """Test health check endpoints"""

    def test_root_endpoint(self):
        """Test root API information endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            assert response.status_code == 200
            data = response.json()

            # Verify expected structure
            expected_keys = ["name", "version", "description", "features", "endpoints"]
            for key in expected_keys:
                assert key in data, f"Missing key: {key}"

            assert "Social Security AI" in data["name"]
            assert isinstance(data["features"], list)
            assert isinstance(data["endpoints"], dict)

            self.log_test("Root API Information", "PASS", {"response_keys": list(data.keys())})

        except Exception as e:
            self.log_test("Root API Information", "FAIL", {"error": str(e)})

    def test_basic_health_check(self):
        """Test basic health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health/basic")
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert "timestamp" in data
            assert data["service"] == "social-security-ai"

            self.log_test("Basic Health Check", "PASS")

        except Exception as e:
            self.log_test("Basic Health Check", "FAIL", {"error": str(e)})

    def test_comprehensive_health_check(self):
        """Test comprehensive health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health/")
            assert response.status_code == 200
            data = response.json()

            assert "status" in data
            assert "services" in data

            # Check for expected services
            expected_services = ["database", "redis", "ollama", "qdrant", "celery_workers"]
            for service in expected_services:
                assert service in data["services"], f"Missing service: {service}"
                assert "status" in data["services"][service]

            self.log_test("Comprehensive Health Check", "PASS",
                         {"services": list(data["services"].keys())})

        except Exception as e:
            self.log_test("Comprehensive Health Check", "FAIL", {"error": str(e)})

    def test_database_health_check(self):
        """Test database-specific health check"""
        try:
            response = self.session.get(f"{self.base_url}/health/database")
            assert response.status_code == 200
            data = response.json()

            assert data["database"] == "postgresql"
            assert "connection" in data

            self.log_test("Database Health Check", "PASS")

        except Exception as e:
            self.log_test("Database Health Check", "FAIL", {"error": str(e)})


class TestAuthenticationEndpoints(APITestSuite):
    """Test authentication endpoints with edge cases"""

    def test_user_registration_valid(self):
        """Test valid user registration"""
        try:
            self.test_user_data = self.generate_test_user_data()

            response = self.session.post(
                f"{self.base_url}/auth/register",
                headers={"Content-Type": "application/json"},
                json=self.test_user_data
            )

            assert response.status_code == 201
            data = response.json()

            assert "id" in data
            assert data["username"] == self.test_user_data["username"]
            assert data["email"] == self.test_user_data["email"]
            assert data["is_active"] is True
            assert "created_at" in data

            self.log_test("User Registration (Valid)", "PASS")

        except Exception as e:
            self.log_test("User Registration (Valid)", "FAIL", {"error": str(e)})

    def test_user_registration_duplicate(self):
        """Test duplicate user registration"""
        try:
            # Try to register the same user again
            response = self.session.post(
                f"{self.base_url}/auth/register",
                headers={"Content-Type": "application/json"},
                json=self.test_user_data
            )

            assert response.status_code == 409
            data = response.json()
            assert "error" in data

            self.log_test("User Registration (Duplicate)", "PASS")

        except Exception as e:
            self.log_test("User Registration (Duplicate)", "FAIL", {"error": str(e)})

    def test_user_registration_invalid_data(self):
        """Test user registration with invalid data"""
        invalid_cases = [
            # Missing required fields
            {"username": "test", "password": "pass"},
            # Invalid email format
            {"username": "test", "email": "invalid-email", "password": "pass123"},
            # Short username
            {"username": "ab", "email": "test@test.com", "password": "pass123"},
            # Weak password
            {"username": "testuser", "email": "test@test.com", "password": "123"}
        ]

        for i, invalid_data in enumerate(invalid_cases):
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/register",
                    headers={"Content-Type": "application/json"},
                    json=invalid_data
                )

                assert response.status_code in [400, 422]
                self.log_test(f"Invalid Registration Case {i+1}", "PASS")

            except Exception as e:
                self.log_test(f"Invalid Registration Case {i+1}", "FAIL", {"error": str(e)})

    def test_user_login_valid(self):
        """Test valid user login"""
        try:
            login_data = {
                "username": self.test_user_data["username"],
                "password": self.test_user_data["password"]
            }

            response = self.session.post(
                f"{self.base_url}/auth/login",
                headers={"Content-Type": "application/json"},
                json=login_data
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert "user_info" in data

            # Store token for authenticated requests
            self.auth_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

            self.log_test("User Login (Valid)", "PASS")

        except Exception as e:
            self.log_test("User Login (Valid)", "FAIL", {"error": str(e)})

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        invalid_cases = [
            {"username": "nonexistent", "password": "wrongpass"},
            {"username": self.test_user_data["username"], "password": "wrongpass"},
            {"username": "wronguser", "password": self.test_user_data["password"]}
        ]

        for i, invalid_data in enumerate(invalid_cases):
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    headers={"Content-Type": "application/json"},
                    json=invalid_data
                )

                assert response.status_code == 401
                self.log_test(f"Invalid Login Case {i+1}", "PASS")

            except Exception as e:
                self.log_test(f"Invalid Login Case {i+1}", "FAIL", {"error": str(e)})

    def test_get_current_user_info(self):
        """Test getting current user information"""
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            assert response.status_code == 200
            data = response.json()

            assert data["username"] == self.test_user_data["username"]
            assert data["email"] == self.test_user_data["email"]

            self.log_test("Get Current User Info", "PASS")

        except Exception as e:
            self.log_test("Get Current User Info", "FAIL", {"error": str(e)})

    def test_authentication_status(self):
        """Test authentication status endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/auth/status")
            assert response.status_code == 200
            data = response.json()

            assert data["authenticated"] is True
            assert "user_id" in data
            assert data["username"] == self.test_user_data["username"]

            self.log_test("Authentication Status", "PASS")

        except Exception as e:
            self.log_test("Authentication Status", "FAIL", {"error": str(e)})

    def test_token_refresh(self):
        """Test JWT token refresh"""
        try:
            response = self.session.post(f"{self.base_url}/auth/refresh")
            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Update token
            self.auth_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

            self.log_test("Token Refresh", "PASS")

        except Exception as e:
            self.log_test("Token Refresh", "FAIL", {"error": str(e)})

    def test_logout(self):
        """Test user logout"""
        try:
            response = self.session.post(f"{self.base_url}/auth/logout")
            assert response.status_code == 200
            data = response.json()

            assert "message" in data
            assert "logged_out_at" in data

            self.log_test("User Logout", "PASS")

        except Exception as e:
            self.log_test("User Logout", "FAIL", {"error": str(e)})


class TestDocumentEndpoints(APITestSuite):
    """Test document upload and processing endpoints"""

    def test_get_supported_file_types(self):
        """Test getting supported file types"""
        try:
            response = self.session.get(f"{self.base_url}/documents/types")
            assert response.status_code == 200
            data = response.json()

            assert "supported_types" in data
            assert "limits" in data
            assert "bank_statement" in data["supported_types"]
            assert "emirates_id" in data["supported_types"]

            self.log_test("Get Supported File Types", "PASS")

        except Exception as e:
            self.log_test("Get Supported File Types", "FAIL", {"error": str(e)})

    def test_document_upload_valid(self):
        """Test valid document upload"""
        try:
            # Re-authenticate for document upload
            self.test_user_login_valid()

            # Prepare test files
            bank_statement_path = self.fixtures_path / "test_bank_statement.pdf"
            emirates_id_path = self.fixtures_path / "test_emirates_id.png"

            with open(bank_statement_path, 'rb') as bank_file, \
                 open(emirates_id_path, 'rb') as id_file:

                files = {
                    'bank_statement': ('test_bank_statement.pdf', bank_file, 'application/pdf'),
                    'emirates_id': ('test_emirates_id.png', id_file, 'image/png')
                }

                response = self.session.post(
                    f"{self.base_url}/documents/upload",
                    files=files
                )

                assert response.status_code == 201
                data = response.json()

                assert "message" in data
                assert "documents" in data
                assert "bank_statement" in data["documents"]
                assert "emirates_id" in data["documents"]

                # Store document IDs for further testing
                self.bank_statement_id = data["documents"]["bank_statement"]["id"]
                self.emirates_id_doc_id = data["documents"]["emirates_id"]["id"]

                self.log_test("Document Upload (Valid)", "PASS")

        except Exception as e:
            self.log_test("Document Upload (Valid)", "FAIL", {"error": str(e)})

    def test_document_upload_invalid_file_type(self):
        """Test document upload with invalid file type"""
        try:
            # Create a temporary text file
            invalid_file_path = self.fixtures_path / "invalid_document.txt"

            with open(invalid_file_path, 'rb') as invalid_file:
                files = {
                    'bank_statement': ('invalid.txt', invalid_file, 'text/plain'),
                    'emirates_id': ('test_emirates_id.png',
                                  open(self.fixtures_path / "test_emirates_id.png", 'rb'),
                                  'image/png')
                }

                response = self.session.post(
                    f"{self.base_url}/documents/upload",
                    files=files
                )

                assert response.status_code == 400

                self.log_test("Document Upload (Invalid File Type)", "PASS")

        except Exception as e:
            self.log_test("Document Upload (Invalid File Type)", "FAIL", {"error": str(e)})

    def test_document_status(self):
        """Test getting document processing status"""
        try:
            if hasattr(self, 'bank_statement_id'):
                response = self.session.get(
                    f"{self.base_url}/documents/status/{self.bank_statement_id}"
                )
                assert response.status_code == 200
                data = response.json()

                assert "document_id" in data
                assert "status" in data
                assert "processing_steps" in data

                self.log_test("Document Status", "PASS")
            else:
                self.log_test("Document Status", "SKIP", {"reason": "No document ID available"})

        except Exception as e:
            self.log_test("Document Status", "FAIL", {"error": str(e)})

    def test_document_deletion(self):
        """Test document deletion"""
        try:
            if hasattr(self, 'bank_statement_id'):
                response = self.session.delete(
                    f"{self.base_url}/documents/{self.bank_statement_id}"
                )
                assert response.status_code == 200
                data = response.json()

                assert "message" in data
                assert "deleted_at" in data

                self.log_test("Document Deletion", "PASS")
            else:
                self.log_test("Document Deletion", "SKIP", {"reason": "No document ID available"})

        except Exception as e:
            self.log_test("Document Deletion", "FAIL", {"error": str(e)})


class TestWorkflowEndpoints(APITestSuite):
    """Test workflow management endpoints"""

    def test_start_application_workflow(self):
        """Test starting an application workflow"""
        try:
            # Re-authenticate
            self.test_user_login_valid()

            application_data = {
                "full_name": "Test Applicant",
                "emirates_id": "784-1985-9876543-2",
                "phone": "+971501234567",
                "email": "applicant@test.com"
            }

            response = self.session.post(
                f"{self.base_url}/workflow/start-application",
                headers={"Content-Type": "application/json"},
                json=application_data
            )

            assert response.status_code == 201
            data = response.json()

            assert "application_id" in data
            assert "status" in data
            assert "progress" in data
            assert "next_steps" in data

            # Store application ID for further testing
            self.application_id = data["application_id"]

            self.log_test("Start Application Workflow", "PASS")

        except Exception as e:
            self.log_test("Start Application Workflow", "FAIL", {"error": str(e)})

    def test_workflow_status(self):
        """Test getting workflow status"""
        try:
            if hasattr(self, 'application_id'):
                response = self.session.get(
                    f"{self.base_url}/workflow/status/{self.application_id}"
                )
                assert response.status_code == 200
                data = response.json()

                assert "application_id" in data
                assert "current_state" in data
                assert "progress" in data
                assert "steps" in data

                self.log_test("Workflow Status", "PASS")
            else:
                self.log_test("Workflow Status", "SKIP", {"reason": "No application ID available"})

        except Exception as e:
            self.log_test("Workflow Status", "FAIL", {"error": str(e)})


class TestApplicationEndpoints(APITestSuite):
    """Test application management endpoints"""

    def test_list_applications(self):
        """Test listing user applications"""
        try:
            response = self.session.get(f"{self.base_url}/applications")
            assert response.status_code == 200
            data = response.json()

            assert "applications" in data
            assert "total_count" in data
            assert "page" in data
            assert "page_size" in data

            self.log_test("List Applications", "PASS")

        except Exception as e:
            self.log_test("List Applications", "FAIL", {"error": str(e)})

    def test_get_application_details(self):
        """Test getting application details"""
        try:
            if hasattr(self, 'application_id'):
                response = self.session.get(
                    f"{self.base_url}/applications/{self.application_id}"
                )
                assert response.status_code == 200
                data = response.json()

                assert "application_id" in data
                assert "status" in data
                assert "form_data" in data

                self.log_test("Get Application Details", "PASS")
            else:
                self.log_test("Get Application Details", "SKIP", {"reason": "No application ID available"})

        except Exception as e:
            self.log_test("Get Application Details", "FAIL", {"error": str(e)})


def run_comprehensive_api_tests():
    """Run all API endpoint tests"""

    print("🚀 Starting Comprehensive API Endpoint Tests")
    print("=" * 60)

    # Health endpoints
    health_tests = TestHealthEndpoints()
    health_tests.test_root_endpoint()
    health_tests.test_basic_health_check()
    health_tests.test_comprehensive_health_check()
    health_tests.test_database_health_check()

    # Authentication endpoints
    auth_tests = TestAuthenticationEndpoints()
    auth_tests.test_user_registration_valid()
    auth_tests.test_user_registration_duplicate()
    auth_tests.test_user_registration_invalid_data()
    auth_tests.test_user_login_valid()
    auth_tests.test_user_login_invalid_credentials()
    auth_tests.test_get_current_user_info()
    auth_tests.test_authentication_status()
    auth_tests.test_token_refresh()
    auth_tests.test_logout()

    # Document endpoints
    doc_tests = TestDocumentEndpoints()
    doc_tests.test_get_supported_file_types()
    doc_tests.test_document_upload_valid()
    doc_tests.test_document_upload_invalid_file_type()
    doc_tests.test_document_status()
    doc_tests.test_document_deletion()

    # Workflow endpoints
    workflow_tests = TestWorkflowEndpoints()
    workflow_tests.test_start_application_workflow()
    workflow_tests.test_workflow_status()

    # Application endpoints
    app_tests = TestApplicationEndpoints()
    app_tests.test_list_applications()
    app_tests.test_get_application_details()

    # Collect all results
    all_results = (health_tests.test_results +
                  auth_tests.test_results +
                  doc_tests.test_results +
                  workflow_tests.test_results +
                  app_tests.test_results)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r["status"] == "PASS"])
    failed_tests = len([r for r in all_results if r["status"] == "FAIL"])
    skipped_tests = len([r for r in all_results if r["status"] == "SKIP"])

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"⚠️ Skipped: {skipped_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    # Save results to file
    with open("test_results_api_endpoints.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: test_results_api_endpoints.json")

    return all_results


if __name__ == "__main__":
    run_comprehensive_api_tests()