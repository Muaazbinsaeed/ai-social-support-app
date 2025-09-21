#!/usr/bin/env python3
"""
Integration Tests
End-to-end workflow testing and system integration validation
"""

import pytest
import requests
import json
import time
import random
import string
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import subprocess
import sys


class IntegrationTestSuite:
    """Base class for integration testing"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.fixtures_path = Path(__file__).parent / "fixtures" / "sample_documents"

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
        if details and status != "PASS":
            print(f"   Details: {details}")

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to be available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False


class TestSystemIntegration(IntegrationTestSuite):
    """Test system-wide integration"""

    def test_all_services_running(self):
        """Test that all required services are running"""
        try:
            services = {
                "FastAPI Backend": f"{self.base_url}/health/basic",
                "Ollama AI": "http://localhost:11434/api/tags",
                "PostgreSQL": f"{self.base_url}/health/database",
                "Redis": f"{self.base_url}/health/",  # Comprehensive health includes Redis
                "Qdrant": "http://localhost:6333/collections"
            }

            all_healthy = True
            service_status = {}

            for service_name, url in services.items():
                try:
                    if service_name == "Ollama AI":
                        # Special handling for Ollama
                        response = requests.get(url, timeout=10)
                        is_healthy = response.status_code == 200
                    elif service_name == "Qdrant":
                        # Special handling for Qdrant
                        response = requests.get(url, timeout=5)
                        is_healthy = response.status_code == 200
                    else:
                        # Standard health check
                        response = requests.get(url, timeout=5)
                        is_healthy = response.status_code == 200

                    service_status[service_name] = "healthy" if is_healthy else "unhealthy"
                    if not is_healthy:
                        all_healthy = False

                except Exception as e:
                    service_status[service_name] = f"error: {str(e)}"
                    all_healthy = False

            if all_healthy:
                self.log_test("All Services Running", "PASS", {"services": service_status})
            else:
                self.log_test("All Services Running", "FAIL", {"services": service_status})

        except Exception as e:
            self.log_test("All Services Running", "FAIL", {"error": str(e)})

    def test_database_connectivity(self):
        """Test database connectivity and basic operations"""
        try:
            # Test database health
            response = requests.get(f"{self.base_url}/health/database")
            assert response.status_code == 200

            data = response.json()
            assert data["database"] == "postgresql"
            assert data["connection"] == "ok"

            self.log_test("Database Connectivity", "PASS")

        except Exception as e:
            self.log_test("Database Connectivity", "FAIL", {"error": str(e)})

    def test_ai_model_availability(self):
        """Test AI model availability and basic inference"""
        try:
            # Check Ollama models
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            assert response.status_code == 200

            models_data = response.json()
            available_models = [model["name"] for model in models_data.get("models", [])]

            # Check for required models
            required_models = ["moondream:1.8b", "qwen2:1.5b", "nomic-embed-text"]
            missing_models = []

            for required in required_models:
                if not any(required in available for available in available_models):
                    missing_models.append(required)

            if missing_models:
                self.log_test("AI Model Availability", "FAIL",
                             {"missing_models": missing_models})
            else:
                self.log_test("AI Model Availability", "PASS",
                             {"available_models": available_models})

        except Exception as e:
            self.log_test("AI Model Availability", "FAIL", {"error": str(e)})

    def test_worker_queue_system(self):
        """Test Celery worker and queue system"""
        try:
            # Check Redis connection (used by Celery)
            response = requests.get(f"{self.base_url}/health/")
            assert response.status_code == 200

            data = response.json()
            redis_status = data.get("services", {}).get("redis", {})
            celery_status = data.get("services", {}).get("celery_workers", {})

            assert redis_status.get("status") == "healthy"

            self.log_test("Worker Queue System", "PASS",
                         {"redis": redis_status, "celery": celery_status})

        except Exception as e:
            self.log_test("Worker Queue System", "FAIL", {"error": str(e)})


class TestCompleteUserWorkflow(IntegrationTestSuite):
    """Test complete user workflow from registration to decision"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_data = None
        self.auth_token = None
        self.application_id = None

    def generate_test_user(self):
        """Generate test user data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.user_data = {
            "username": f"workflow_user_{random_suffix}",
            "email": f"workflow_{random_suffix}@example.com",
            "password": "WorkflowTest123!",
            "full_name": f"Workflow Test User {random_suffix.upper()}"
        }

    def test_step_1_user_registration(self):
        """Step 1: User registration"""
        try:
            self.generate_test_user()

            response = self.session.post(
                f"{self.base_url}/auth/register",
                headers={"Content-Type": "application/json"},
                json=self.user_data
            )

            assert response.status_code == 201
            data = response.json()

            assert "id" in data
            assert data["username"] == self.user_data["username"]

            self.log_test("Workflow Step 1: Registration", "PASS")

        except Exception as e:
            self.log_test("Workflow Step 1: Registration", "FAIL", {"error": str(e)})

    def test_step_2_user_authentication(self):
        """Step 2: User authentication"""
        try:
            login_data = {
                "username": self.user_data["username"],
                "password": self.user_data["password"]
            }

            response = self.session.post(
                f"{self.base_url}/auth/login",
                headers={"Content-Type": "application/json"},
                json=login_data
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            self.auth_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

            self.log_test("Workflow Step 2: Authentication", "PASS")

        except Exception as e:
            self.log_test("Workflow Step 2: Authentication", "FAIL", {"error": str(e)})

    def test_step_3_application_creation(self):
        """Step 3: Create application"""
        try:
            application_data = {
                "full_name": "Integration Test Applicant",
                "emirates_id": "784-1990-1234567-8",
                "phone": "+971501234567",
                "email": "integration@test.com"
            }

            response = self.session.post(
                f"{self.base_url}/workflow/start-application",
                headers={"Content-Type": "application/json"},
                json=application_data
            )

            assert response.status_code == 201
            data = response.json()

            assert "application_id" in data
            self.application_id = data["application_id"]

            self.log_test("Workflow Step 3: Application Creation", "PASS")

        except Exception as e:
            self.log_test("Workflow Step 3: Application Creation", "FAIL", {"error": str(e)})

    def test_step_4_document_upload(self):
        """Step 4: Document upload"""
        try:
            bank_statement_path = self.fixtures_path / "test_bank_statement.pdf"
            emirates_id_path = self.fixtures_path / "test_emirates_id.png"

            if not bank_statement_path.exists() or not emirates_id_path.exists():
                self.log_test("Workflow Step 4: Document Upload", "SKIP",
                             {"reason": "Test documents not found"})
                return

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

                assert "documents" in data
                assert "bank_statement" in data["documents"]
                assert "emirates_id" in data["documents"]

                self.log_test("Workflow Step 4: Document Upload", "PASS")

        except Exception as e:
            self.log_test("Workflow Step 4: Document Upload", "FAIL", {"error": str(e)})

    def test_step_5_workflow_status_tracking(self):
        """Step 5: Track workflow status"""
        try:
            if not self.application_id:
                self.log_test("Workflow Step 5: Status Tracking", "SKIP",
                             {"reason": "No application ID available"})
                return

            response = self.session.get(
                f"{self.base_url}/workflow/status/{self.application_id}"
            )

            assert response.status_code == 200
            data = response.json()

            assert "application_id" in data
            assert "current_state" in data
            assert "progress" in data
            assert "steps" in data

            self.log_test("Workflow Step 5: Status Tracking", "PASS",
                         {"current_state": data["current_state"],
                          "progress": data["progress"]})

        except Exception as e:
            self.log_test("Workflow Step 5: Status Tracking", "FAIL", {"error": str(e)})

    def test_step_6_application_processing(self):
        """Step 6: Start application processing"""
        try:
            if not self.application_id:
                self.log_test("Workflow Step 6: Processing", "SKIP",
                             {"reason": "No application ID available"})
                return

            response = self.session.post(
                f"{self.base_url}/workflow/process/{self.application_id}",
                headers={"Content-Type": "application/json"},
                json={"force_retry": False}
            )

            # Should accept processing request
            assert response.status_code in [202, 400, 409]  # 400/409 if not ready or already processing

            if response.status_code == 202:
                data = response.json()
                assert "processing_job_id" in data
                self.log_test("Workflow Step 6: Processing", "PASS")
            else:
                # Still valid if application is in wrong state
                self.log_test("Workflow Step 6: Processing", "PASS",
                             {"note": "Application not ready for processing (expected)"})

        except Exception as e:
            self.log_test("Workflow Step 6: Processing", "FAIL", {"error": str(e)})

    def test_step_7_results_retrieval(self):
        """Step 7: Retrieve application results"""
        try:
            if not self.application_id:
                self.log_test("Workflow Step 7: Results", "SKIP",
                             {"reason": "No application ID available"})
                return

            response = self.session.get(
                f"{self.base_url}/applications/{self.application_id}/results"
            )

            # Might be 202 if still processing, 200 if complete
            assert response.status_code in [200, 202]

            if response.status_code == 200:
                data = response.json()
                assert "decision" in data
                assert "reasoning" in data
                self.log_test("Workflow Step 7: Results", "PASS",
                             {"decision": data["decision"]["outcome"]})
            else:
                self.log_test("Workflow Step 7: Results", "PASS",
                             {"note": "Still processing (expected)"})

        except Exception as e:
            self.log_test("Workflow Step 7: Results", "FAIL", {"error": str(e)})


class TestErrorHandlingAndRecovery(IntegrationTestSuite):
    """Test error handling and recovery scenarios"""

    def test_network_resilience(self):
        """Test system resilience to network issues"""
        try:
            # Test timeout handling
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/health/basic", timeout=1)
                response_time = time.time() - start_time

                if response.status_code == 200 and response_time < 5:
                    self.log_test("Network Resilience", "PASS",
                                 {"response_time": f"{response_time:.2f}s"})
                else:
                    self.log_test("Network Resilience", "FAIL",
                                 {"response_time": f"{response_time:.2f}s"})

            except requests.exceptions.Timeout:
                self.log_test("Network Resilience", "FAIL",
                             {"error": "Request timeout"})

        except Exception as e:
            self.log_test("Network Resilience", "FAIL", {"error": str(e)})

    def test_invalid_authentication_handling(self):
        """Test handling of invalid authentication"""
        try:
            # Test with invalid token
            invalid_session = requests.Session()
            invalid_session.headers.update({"Authorization": "Bearer invalid_token"})

            response = invalid_session.get(f"{self.base_url}/auth/me")
            assert response.status_code == 401

            # Test with malformed token
            malformed_session = requests.Session()
            malformed_session.headers.update({"Authorization": "Bearer malformed.jwt.token"})

            response = malformed_session.get(f"{self.base_url}/auth/me")
            assert response.status_code == 401

            self.log_test("Invalid Authentication Handling", "PASS")

        except Exception as e:
            self.log_test("Invalid Authentication Handling", "FAIL", {"error": str(e)})

    def test_rate_limiting_behavior(self):
        """Test rate limiting behavior"""
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(10):
                response = requests.get(f"{self.base_url}/health/basic")
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay

            # Should handle requests gracefully
            success_count = len([r for r in responses if r == 200])

            if success_count >= 8:  # Allow some flexibility
                self.log_test("Rate Limiting Behavior", "PASS",
                             {"success_rate": f"{success_count}/10"})
            else:
                self.log_test("Rate Limiting Behavior", "FAIL",
                             {"success_rate": f"{success_count}/10"})

        except Exception as e:
            self.log_test("Rate Limiting Behavior", "FAIL", {"error": str(e)})

    def test_large_file_handling(self):
        """Test handling of large file uploads"""
        try:
            large_file_path = self.fixtures_path / "large_bank_statement.pdf"

            if not large_file_path.exists():
                self.log_test("Large File Handling", "SKIP",
                             {"reason": "Large test file not found"})
                return

            # Test authentication first
            test_user_data = {
                "username": f"largefiletest_{random.randint(1000, 9999)}",
                "email": f"largefile_{random.randint(1000, 9999)}@test.com",
                "password": "LargeFileTest123!",
                "full_name": "Large File Test User"
            }

            # Register and login
            auth_session = requests.Session()
            auth_session.post(
                f"{self.base_url}/auth/register",
                headers={"Content-Type": "application/json"},
                json=test_user_data
            )

            login_response = auth_session.post(
                f"{self.base_url}/auth/login",
                headers={"Content-Type": "application/json"},
                json={"username": test_user_data["username"], "password": test_user_data["password"]}
            )

            if login_response.status_code == 200:
                token = login_response.json()["access_token"]
                auth_session.headers.update({"Authorization": f"Bearer {token}"})

                # Try to upload large file
                with open(large_file_path, 'rb') as large_file, \
                     open(self.fixtures_path / "test_emirates_id.png", 'rb') as id_file:

                    files = {
                        'bank_statement': ('large_bank_statement.pdf', large_file, 'application/pdf'),
                        'emirates_id': ('test_emirates_id.png', id_file, 'image/png')
                    }

                    response = auth_session.post(
                        f"{self.base_url}/documents/upload",
                        files=files,
                        timeout=30  # Allow more time for large file
                    )

                    # Should handle large file appropriately (accept or reject gracefully)
                    assert response.status_code in [201, 400, 413]  # Success, bad request, or payload too large

                    self.log_test("Large File Handling", "PASS",
                                 {"response_code": response.status_code})
            else:
                self.log_test("Large File Handling", "FAIL",
                             {"error": "Authentication failed"})

        except Exception as e:
            self.log_test("Large File Handling", "FAIL", {"error": str(e)})


class TestPerformanceAndLoad(IntegrationTestSuite):
    """Test system performance under load"""

    def test_concurrent_user_handling(self):
        """Test handling of concurrent users"""
        try:
            import threading
            import queue

            results_queue = queue.Queue()

            def test_user_workflow(user_id):
                """Test workflow for a single user"""
                try:
                    session = requests.Session()

                    # Register user
                    user_data = {
                        "username": f"concurrent_user_{user_id}_{random.randint(1000, 9999)}",
                        "email": f"concurrent_{user_id}_{random.randint(1000, 9999)}@test.com",
                        "password": "ConcurrentTest123!",
                        "full_name": f"Concurrent User {user_id}"
                    }

                    reg_response = session.post(
                        f"{self.base_url}/auth/register",
                        headers={"Content-Type": "application/json"},
                        json=user_data
                    )

                    if reg_response.status_code == 201:
                        # Login
                        login_response = session.post(
                            f"{self.base_url}/auth/login",
                            headers={"Content-Type": "application/json"},
                            json={"username": user_data["username"], "password": user_data["password"]}
                        )

                        if login_response.status_code == 200:
                            results_queue.put(("success", user_id))
                        else:
                            results_queue.put(("login_failed", user_id))
                    else:
                        results_queue.put(("registration_failed", user_id))

                except Exception as e:
                    results_queue.put(("error", user_id, str(e)))

            # Start concurrent threads
            threads = []
            num_users = 5  # Reasonable number for integration test

            for i in range(num_users):
                thread = threading.Thread(target=test_user_workflow, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=30)

            # Collect results
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())

            success_count = len([r for r in results if r[0] == "success"])
            success_rate = (success_count / num_users) * 100

            if success_rate >= 80:  # Allow for some failures
                self.log_test("Concurrent User Handling", "PASS",
                             {"success_rate": f"{success_rate:.1f}%",
                              "successful_users": success_count,
                              "total_users": num_users})
            else:
                self.log_test("Concurrent User Handling", "FAIL",
                             {"success_rate": f"{success_rate:.1f}%",
                              "results": results})

        except Exception as e:
            self.log_test("Concurrent User Handling", "FAIL", {"error": str(e)})

    def test_api_response_times(self):
        """Test API response times"""
        try:
            endpoints = [
                "/",
                "/health/basic",
                "/health/",
                "/documents/types"
            ]

            response_times = {}

            for endpoint in endpoints:
                times = []
                for _ in range(5):  # Test each endpoint 5 times
                    start_time = time.time()
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    end_time = time.time()

                    if response.status_code == 200:
                        times.append((end_time - start_time) * 1000)  # Convert to milliseconds

                if times:
                    avg_time = sum(times) / len(times)
                    response_times[endpoint] = avg_time

            # Check if response times are acceptable (under 1000ms)
            slow_endpoints = [ep for ep, time in response_times.items() if time > 1000]

            if not slow_endpoints:
                self.log_test("API Response Times", "PASS",
                             {"response_times_ms": response_times})
            else:
                self.log_test("API Response Times", "FAIL",
                             {"response_times_ms": response_times,
                              "slow_endpoints": slow_endpoints})

        except Exception as e:
            self.log_test("API Response Times", "FAIL", {"error": str(e)})


def run_comprehensive_integration_tests():
    """Run all integration tests"""

    print("🚀 Starting Comprehensive Integration Tests")
    print("=" * 60)

    # System Integration Tests
    system_tests = TestSystemIntegration()
    system_tests.test_all_services_running()
    system_tests.test_database_connectivity()
    system_tests.test_ai_model_availability()
    system_tests.test_worker_queue_system()

    # Complete User Workflow Tests
    workflow_tests = TestCompleteUserWorkflow()
    workflow_tests.test_step_1_user_registration()
    workflow_tests.test_step_2_user_authentication()
    workflow_tests.test_step_3_application_creation()
    workflow_tests.test_step_4_document_upload()
    workflow_tests.test_step_5_workflow_status_tracking()
    workflow_tests.test_step_6_application_processing()
    workflow_tests.test_step_7_results_retrieval()

    # Error Handling Tests
    error_tests = TestErrorHandlingAndRecovery()
    error_tests.test_network_resilience()
    error_tests.test_invalid_authentication_handling()
    error_tests.test_rate_limiting_behavior()
    error_tests.test_large_file_handling()

    # Performance Tests
    perf_tests = TestPerformanceAndLoad()
    perf_tests.test_concurrent_user_handling()
    perf_tests.test_api_response_times()

    # Collect all results
    all_results = (system_tests.test_results +
                  workflow_tests.test_results +
                  error_tests.test_results +
                  perf_tests.test_results)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TESTS SUMMARY")
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
    with open("test_results_integration.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: test_results_integration.json")

    return all_results


if __name__ == "__main__":
    run_comprehensive_integration_tests()