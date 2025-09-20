#!/usr/bin/env python3
"""
Corrected API Test Suite - Fixed to match actual API behavior
Tests all endpoints with correct expected responses and use cases
"""

import requests
import json
import time
import random
import string
from typing import Dict, List, Any
import sys
from datetime import datetime


class CorrectedAPITester:
    """Corrected API testing with proper expected responses"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None

    def log_test(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log test result with expected vs actual comparison"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "details": details or {}
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details and status != "PASS":
            print(f"   Details: {details}")

    def generate_test_user_data(self) -> Dict[str, str]:
        """Generate unique test user data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "username": f"testuser_{random_suffix}",
            "email": f"test_{random_suffix}@example.com",
            "password": "SecureTestPass123!",
            "full_name": f"Test User {random_suffix.upper()}"
        }

    def test_root_endpoint(self):
        """Test root API endpoint - Expected: API information"""
        try:
            response = self.session.get(f"{self.base_url}/")

            expected_fields = ["name", "version", "description", "features", "endpoints"]
            expected_status = 200

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    self.log_test("Root Endpoint", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_fields": expected_fields,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                        "use_case": "Get API information and available features"
                    })
                else:
                    self.log_test("Root Endpoint", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("Root Endpoint", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Root Endpoint", "FAIL", {"error": str(e)})

    def test_health_endpoints(self):
        """Test health check endpoints - Expected: Service status information"""
        health_endpoints = [
            ("/health/basic", "Basic Health Check", 200, ["status", "timestamp", "service"]),
            ("/health/", "Comprehensive Health Check", 200, ["status", "timestamp", "services"]),
            ("/health/database", "Database Health Check", 200, ["status", "database", "connection"])
        ]

        for endpoint, name, expected_status, expected_fields in health_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")

                if response.status_code == expected_status:
                    data = response.json()
                    if all(field in data for field in expected_fields):
                        self.log_test(name, "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_fields": expected_fields,
                            "status": data.get("status"),
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                            "use_case": f"Monitor {name.lower()} service status"
                        })
                    else:
                        self.log_test(name, "FAIL", {
                            "error": "Missing expected fields",
                            "expected_fields": expected_fields,
                            "actual_fields": list(data.keys())
                        })
                else:
                    self.log_test(name, "FAIL", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "response": response.text[:200]
                    })

            except Exception as e:
                self.log_test(name, "FAIL", {"error": str(e)})

    def test_user_registration_success(self):
        """Test successful user registration - Expected: User data with UUID"""
        try:
            self.test_user_data = self.generate_test_user_data()
            expected_status = 201
            expected_fields = ["id", "username", "email", "full_name", "is_active", "created_at"]

            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=self.test_user_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    # Verify data matches input
                    if (data["username"] == self.test_user_data["username"] and
                        data["email"] == self.test_user_data["email"]):
                        self.log_test("User Registration Success", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_fields": expected_fields,
                            "user_id": data["id"],
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                            "use_case": "Create new user account with valid data"
                        })
                    else:
                        self.log_test("User Registration Success", "FAIL", {
                            "error": "Response data doesn't match input",
                            "expected_username": self.test_user_data["username"],
                            "actual_username": data.get("username")
                        })
                else:
                    self.log_test("User Registration Success", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("User Registration Success", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:300]
                })

        except Exception as e:
            self.log_test("User Registration Success", "FAIL", {"error": str(e)})

    def test_user_registration_duplicate(self):
        """Test duplicate user registration - Expected: 409 Conflict with detail.error"""
        try:
            if not self.test_user_data:
                self.test_user_data = self.generate_test_user_data()
                # First register the user
                self.session.post(f"{self.base_url}/auth/register", json=self.test_user_data)

            expected_status = 409
            expected_structure = ["detail"]  # FastAPI returns detail field

            # Try to register same user again
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=self.test_user_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == expected_status:
                data = response.json()
                if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
                    self.log_test("User Registration Duplicate", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_structure": "detail.error format",
                        "error_code": data["detail"]["error"],
                        "message": data["detail"]["message"],
                        "use_case": "Prevent duplicate user registration with proper error"
                    })
                else:
                    self.log_test("User Registration Duplicate", "FAIL", {
                        "error": "Incorrect error response structure",
                        "expected": "detail.error format",
                        "actual": data
                    })
            else:
                self.log_test("User Registration Duplicate", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("User Registration Duplicate", "FAIL", {"error": str(e)})

    def test_user_login_success(self):
        """Test successful user login - Expected: JWT token and user info"""
        try:
            if not self.test_user_data:
                # Register a user first
                self.test_user_data = self.generate_test_user_data()
                reg_response = self.session.post(f"{self.base_url}/auth/register", json=self.test_user_data)
                if reg_response.status_code != 201:
                    raise Exception(f"Failed to register test user: {reg_response.status_code}")

            login_data = {
                "username": self.test_user_data["username"],
                "password": self.test_user_data["password"]
            }
            expected_status = 200
            expected_fields = ["access_token", "token_type", "expires_in", "user_info"]

            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    # Store token for future tests
                    self.auth_token = data["access_token"]
                    self.log_test("User Login Success", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_fields": expected_fields,
                        "token_type": data["token_type"],
                        "expires_in": data["expires_in"],
                        "user_id": data["user_info"].get("id", "unknown"),
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                        "use_case": "Authenticate user and receive JWT token for API access"
                    })
                else:
                    self.log_test("User Login Success", "FAIL", {
                        "error": "Missing required fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("User Login Success", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("User Login Success", "FAIL", {"error": str(e)})

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials - Expected: 401 with detail.error"""
        try:
            invalid_login_data = {
                "username": "nonexistent_user",
                "password": "wrong_password"
            }
            expected_status = 401
            expected_structure = "detail.error format"

            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=invalid_login_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == expected_status:
                data = response.json()
                if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
                    self.log_test("User Login Invalid Credentials", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_structure": expected_structure,
                        "error_code": data["detail"]["error"],
                        "message": data["detail"]["message"],
                        "use_case": "Reject invalid login attempts with proper error"
                    })
                else:
                    self.log_test("User Login Invalid Credentials", "FAIL", {
                        "error": "Incorrect error response structure",
                        "expected": expected_structure,
                        "actual": data
                    })
            else:
                self.log_test("User Login Invalid Credentials", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("User Login Invalid Credentials", "FAIL", {"error": str(e)})

    def test_protected_endpoints(self):
        """Test protected endpoints - Expected: 403 without auth, 200 with auth"""
        protected_endpoints = [
            ("/auth/me", "GET", "Get Current User"),
            ("/auth/status", "GET", "Get Auth Status"),
        ]

        for endpoint, method, name in protected_endpoints:
            # Test without authentication - FastAPI returns 403 for missing auth
            try:
                expected_unauth_status = 403  # FastAPI uses 403 for "Not authenticated"
                response = self.session.get(f"{self.base_url}{endpoint}")

                if response.status_code == expected_unauth_status:
                    data = response.json()
                    if "detail" in data and data["detail"] == "Not authenticated":
                        self.log_test(f"{name} - Unauthorized Access", "PASS", {
                            "expected_status": expected_unauth_status,
                            "actual_status": response.status_code,
                            "expected_response": "Not authenticated",
                            "use_case": "Block unauthorized access to protected endpoints"
                        })
                    else:
                        self.log_test(f"{name} - Unauthorized Access", "FAIL", {
                            "error": "Unexpected error response format",
                            "expected": "Not authenticated",
                            "actual": data
                        })
                else:
                    self.log_test(f"{name} - Unauthorized Access", "FAIL", {
                        "expected_status": expected_unauth_status,
                        "actual_status": response.status_code,
                        "response": response.text[:200]
                    })
            except Exception as e:
                self.log_test(f"{name} - Unauthorized Access", "FAIL", {"error": str(e)})

            # Test with authentication
            if self.auth_token:
                try:
                    expected_auth_status = 200
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)

                    if response.status_code == expected_auth_status:
                        self.log_test(f"{name} - Authorized Access", "PASS", {
                            "expected_status": expected_auth_status,
                            "actual_status": response.status_code,
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                            "use_case": "Access protected endpoints with valid JWT token"
                        })
                    else:
                        self.log_test(f"{name} - Authorized Access", "FAIL", {
                            "expected_status": expected_auth_status,
                            "actual_status": response.status_code,
                            "response": response.text[:200]
                        })
                except Exception as e:
                    self.log_test(f"{name} - Authorized Access", "FAIL", {"error": str(e)})

    def test_protected_post_endpoints(self):
        """Test POST protected endpoints - Expected: 405 without auth (method not allowed on GET), 200 with auth on POST"""
        protected_post_endpoints = [
            ("/auth/logout", "User Logout"),
            ("/auth/refresh", "Refresh Token")
        ]

        for endpoint, name in protected_post_endpoints:
            # Test GET on POST endpoint (should return 405 Method Not Allowed)
            try:
                expected_method_status = 405
                response = self.session.get(f"{self.base_url}{endpoint}")

                if response.status_code == expected_method_status:
                    self.log_test(f"{name} - Wrong Method", "PASS", {
                        "expected_status": expected_method_status,
                        "actual_status": response.status_code,
                        "use_case": "Reject wrong HTTP method on POST-only endpoints"
                    })
                else:
                    self.log_test(f"{name} - Wrong Method", "FAIL", {
                        "expected_status": expected_method_status,
                        "actual_status": response.status_code,
                        "response": response.text[:200]
                    })
            except Exception as e:
                self.log_test(f"{name} - Wrong Method", "FAIL", {"error": str(e)})

            # Test POST with authentication
            if self.auth_token:
                try:
                    expected_auth_status = 200
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = self.session.post(f"{self.base_url}{endpoint}", headers=headers)

                    if response.status_code == expected_auth_status:
                        self.log_test(f"{name} - Authorized Access", "PASS", {
                            "expected_status": expected_auth_status,
                            "actual_status": response.status_code,
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                            "use_case": f"Execute {name.lower()} with valid JWT token"
                        })
                    else:
                        self.log_test(f"{name} - Authorized Access", "FAIL", {
                            "expected_status": expected_auth_status,
                            "actual_status": response.status_code,
                            "response": response.text[:200]
                        })
                except Exception as e:
                    self.log_test(f"{name} - Authorized Access", "FAIL", {"error": str(e)})

    def test_content_type_validation(self):
        """Test content type validation - Expected: 415 for unsupported types"""
        test_cases = [
            ("text/plain", "Plain text content type"),
            ("application/xml", "XML content type"),
            ("multipart/form-data", "Form data content type")
        ]

        test_data = {"username": "test", "password": "test"}

        for content_type, description in test_cases:
            try:
                expected_status = 415
                headers = {"Content-Type": content_type}
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    json=test_data,
                    headers=headers
                )

                if response.status_code == expected_status:
                    data = response.json()
                    if "error" in data and "UNSUPPORTED_MEDIA_TYPE" in data["error"]:
                        self.log_test(f"Content Type Validation - {description}", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "rejected_content_type": content_type,
                            "error_code": data.get("error"),
                            "use_case": "Reject unsupported content types on API endpoints"
                        })
                    else:
                        self.log_test(f"Content Type Validation - {description}", "FAIL", {
                            "error": "Wrong error response format",
                            "expected": "UNSUPPORTED_MEDIA_TYPE error",
                            "actual": data
                        })
                else:
                    self.log_test(f"Content Type Validation - {description}", "FAIL", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "response": response.text[:200]
                    })

            except Exception as e:
                self.log_test(f"Content Type Validation - {description}", "FAIL", {"error": str(e)})

    def test_input_validation(self):
        """Test input validation scenarios - Expected: 422 for validation errors"""
        validation_test_cases = [
            # Missing required fields
            ({"username": "test"}, "Missing Required Fields", 422),
            # Invalid email format
            ({"username": "test", "email": "invalid-email", "password": "password123", "full_name": "Test"}, "Invalid Email Format", 422),
            # Weak password
            ({"username": "testuser", "email": "test@example.com", "password": "123", "full_name": "Test"}, "Weak Password", 422),
            # Username too short
            ({"username": "a", "email": "test@example.com", "password": "password123", "full_name": "Test"}, "Username Too Short", 422),
        ]

        for test_data, test_name, expected_status in validation_test_cases:
            try:
                headers = {"Content-Type": "application/json"}
                response = self.session.post(
                    f"{self.base_url}/auth/register",
                    json=test_data,
                    headers=headers
                )

                if response.status_code == expected_status:
                    data = response.json()
                    if "error" in data and "VALIDATION_ERROR" in data["error"]:
                        self.log_test(f"Input Validation - {test_name}", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "error_code": data.get("error"),
                            "validation_triggered": True,
                            "use_case": f"Validate {test_name.lower()} and return appropriate error"
                        })
                    else:
                        self.log_test(f"Input Validation - {test_name}", "FAIL", {
                            "error": "Unexpected validation response format",
                            "expected": "VALIDATION_ERROR",
                            "actual": data
                        })
                else:
                    self.log_test(f"Input Validation - {test_name}", "FAIL", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "response": response.text[:200]
                    })

            except Exception as e:
                self.log_test(f"Input Validation - {test_name}", "FAIL", {"error": str(e)})

    def test_performance_metrics(self):
        """Test API performance - Expected: Response times < 1000ms"""
        try:
            # Test single request performance
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health/basic")
            single_request_time = time.time() - start_time

            target_time = 1.0  # 1000ms target
            if response.status_code == 200 and single_request_time < target_time:
                self.log_test("Performance - Single Request", "PASS", {
                    "expected_max_time_ms": target_time * 1000,
                    "actual_time_ms": single_request_time * 1000,
                    "target_met": True,
                    "use_case": "Ensure API responds quickly for good user experience"
                })
            else:
                self.log_test("Performance - Single Request", "FAIL", {
                    "expected_max_time_ms": target_time * 1000,
                    "actual_time_ms": single_request_time * 1000,
                    "status_code": response.status_code
                })

            # Test concurrent requests
            import threading
            results = []

            def make_request():
                try:
                    resp = requests.get(f"{self.base_url}/health/basic", timeout=5)
                    results.append((resp.status_code == 200, resp.elapsed.total_seconds()))
                except:
                    results.append((False, 0))

            start_time = time.time()
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join(timeout=10)

            concurrent_time = time.time() - start_time
            successful_requests = sum(1 for success, _ in results if success)
            avg_response_time = sum(time for _, time in results) / len(results) if results else 0

            success_threshold = 0.8  # 80% success rate
            if successful_requests >= len(results) * success_threshold and concurrent_time < 5.0:
                self.log_test("Performance - Concurrent Requests", "PASS", {
                    "expected_min_success_rate": f"{success_threshold*100}%",
                    "actual_success_rate": f"{(successful_requests/len(results))*100:.1f}%",
                    "successful_requests": f"{successful_requests}/{len(results)}",
                    "total_time_ms": concurrent_time * 1000,
                    "avg_response_time_ms": avg_response_time * 1000,
                    "use_case": "Handle multiple concurrent requests without degradation"
                })
            else:
                self.log_test("Performance - Concurrent Requests", "FAIL", {
                    "successful_requests": f"{successful_requests}/{len(results)}",
                    "total_time_ms": concurrent_time * 1000,
                    "threshold": f"{success_threshold*100}%"
                })

        except Exception as e:
            self.log_test("Performance Tests", "FAIL", {"error": str(e)})

    def test_service_integrations(self):
        """Test service integrations - Expected: Healthy status for all services"""
        try:
            response = self.session.get(f"{self.base_url}/health/")

            if response.status_code == 200:
                data = response.json()
                services = data.get("services", {})

                service_tests = {
                    "database": "PostgreSQL Database",
                    "redis": "Redis Cache",
                    "ollama": "AI Models (Ollama)",
                    "qdrant": "Vector Database",
                    "celery_workers": "Background Workers"
                }

                for service_key, service_name in service_tests.items():
                    if service_key in services:
                        service_status = services[service_key].get("status", "unknown")
                        expected_statuses = ["healthy", "degraded"]  # Both acceptable

                        if service_status in expected_statuses:
                            self.log_test(f"Service Integration - {service_name}", "PASS", {
                                "expected_statuses": expected_statuses,
                                "actual_status": service_status,
                                "service_details": services[service_key],
                                "use_case": f"Verify {service_name.lower()} is operational"
                            })
                        else:
                            self.log_test(f"Service Integration - {service_name}", "FAIL", {
                                "expected_statuses": expected_statuses,
                                "actual_status": service_status,
                                "error": services[service_key].get("error", "Unknown error")
                            })
                    else:
                        self.log_test(f"Service Integration - {service_name}", "FAIL", {
                            "error": f"Service {service_key} not found in health check"
                        })
            else:
                self.log_test("Service Integrations", "FAIL", {
                    "error": f"Health check failed with status {response.status_code}"
                })

        except Exception as e:
            self.log_test("Service Integrations", "FAIL", {"error": str(e)})

    def run_all_tests(self):
        """Run comprehensive corrected test suite"""
        print("🚀 Starting Corrected Comprehensive Backend API Testing Suite")
        print("=" * 70)
        print("📋 Testing against actual API behavior with expected responses")
        print("=" * 70)

        test_methods = [
            self.test_root_endpoint,
            self.test_health_endpoints,
            self.test_user_registration_success,
            self.test_user_registration_duplicate,
            self.test_user_login_success,
            self.test_user_login_invalid_credentials,
            self.test_protected_endpoints,
            self.test_protected_post_endpoints,
            self.test_content_type_validation,
            self.test_input_validation,
            self.test_performance_metrics,
            self.test_service_integrations,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Error running {test_method.__name__}: {str(e)}")

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate corrected test results summary"""
        print("\n" + "=" * 70)
        print("📊 CORRECTED TEST RESULTS SUMMARY")
        print("=" * 70)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        warning_tests = len([r for r in self.test_results if r["status"] == "WARNING"])

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warning_tests}")

        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"   - {result['test_name']}: {result['details'].get('error', 'Unknown error')}")

        # Overall system status
        if success_rate >= 95:
            print(f"\n🟢 SYSTEM STATUS: EXCELLENT ({success_rate:.1f}%)")
        elif success_rate >= 85:
            print(f"\n🟡 SYSTEM STATUS: GOOD ({success_rate:.1f}%)")
        elif success_rate >= 70:
            print(f"\n🟠 SYSTEM STATUS: FAIR ({success_rate:.1f}%)")
        else:
            print(f"\n🔴 SYSTEM STATUS: POOR ({success_rate:.1f}%)")

        print("\n📋 USE CASES VALIDATED:")
        use_cases = set()
        for result in self.test_results:
            if result["status"] == "PASS" and "use_case" in result["details"]:
                use_cases.add(result["details"]["use_case"])

        for i, use_case in enumerate(sorted(use_cases), 1):
            print(f"   {i}. {use_case}")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "detailed_results": self.test_results,
            "use_cases_validated": list(use_cases)
        }


def main():
    """Main testing function"""
    tester = CorrectedAPITester()

    # Check if API is accessible
    try:
        response = requests.get("http://localhost:8000/health/basic", timeout=5)
        if response.status_code != 200:
            print("❌ API is not accessible. Please ensure the server is running.")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API at http://localhost:8000")
        print("   Please ensure Docker services are running with: docker compose up")
        sys.exit(1)

    # Run all tests
    results = tester.run_all_tests()

    # Save results to file
    with open("corrected_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Corrected test results saved to: corrected_test_results.json")

    return results


if __name__ == "__main__":
    main()