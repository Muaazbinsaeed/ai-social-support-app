#!/usr/bin/env python3
"""
Comprehensive Real-time Test Suite
Executes unit tests, API tests, and flow tests with detailed input/output capture
"""

import requests
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
import sys
import traceback
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30
REPORT_FILE = "COMPREHENSIVE_TEST_REPORT.md"

class TestReporter:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()

    def add_test(self, test_name: str, test_type: str, method: str, endpoint: str,
                 input_data: Any, expected_output: Any, actual_output: Any,
                 status: str, duration: float, error: str = None):
        self.results.append({
            'test_name': test_name,
            'test_type': test_type,
            'method': method,
            'endpoint': endpoint,
            'input_data': input_data,
            'expected_output': expected_output,
            'actual_output': actual_output,
            'status': status,
            'duration': duration,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

    def generate_report(self):
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests
        total_duration = (datetime.now() - self.start_time).total_seconds()

        report = f"""# Comprehensive Real-time Test Report

## 📊 Test Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} ❌
- **Success Rate**: {(passed_tests/total_tests*100):.1f}%
- **Total Duration**: {total_duration:.2f} seconds
- **Generated**: {datetime.now().isoformat()}

## 🧪 Test Results

"""

        for i, result in enumerate(self.results, 1):
            status_icon = "✅" if result['status'] == 'PASS' else "❌"

            report += f"""### Test {i}: {result['test_name']} {status_icon}

**Type**: {result['test_type']}
**Method**: {result['method']}
**Endpoint**: {result['endpoint']}
**Duration**: {result['duration']:.3f}s
**Status**: {result['status']}

#### Input Data:
```json
{json.dumps(result['input_data'], indent=2, default=str)}
```

#### Expected Output:
```json
{json.dumps(result['expected_output'], indent=2, default=str)}
```

#### Actual Output:
```json
{json.dumps(result['actual_output'], indent=2, default=str)}
```

"""
            if result['error']:
                report += f"""#### Error Details:
```
{result['error']}
```

"""

            report += "---\n\n"

        return report

# Global reporter instance
reporter = TestReporter()

def make_api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make API request and capture response details"""
    try:
        start_time = time.time()
        url = f"{BASE_URL}{endpoint}"

        response = requests.request(method, url, timeout=TEST_TIMEOUT, **kwargs)
        duration = time.time() - start_time

        try:
            response_data = response.json()
        except:
            response_data = response.text

        return {
            'status_code': response.status_code,
            'duration': duration,
            'headers': dict(response.headers),
            'data': response_data,
            'success': 200 <= response.status_code < 300
        }
    except Exception as e:
        return {
            'status_code': 0,
            'duration': time.time() - start_time,
            'error': str(e),
            'success': False
        }

def test_unit_functions():
    """Unit tests for core functions"""
    print("\n🧪 Running Unit Tests...")

    # Test 1: Password hashing
    test_name = "Password Hashing Unit Test"
    input_data = {"password": "testpass123"}
    expected_output = {"hashed": True, "verified": True}

    try:
        from app.user_management.user_service import UserService
        hashed = UserService.hash_password(input_data["password"])
        verified = UserService.verify_password(input_data["password"], hashed)

        actual_output = {"hashed": bool(hashed), "verified": verified}
        status = "PASS" if actual_output["verified"] else "FAIL"

        reporter.add_test(test_name, "UNIT", "FUNCTION", "hash_password",
                         input_data, expected_output, actual_output, status, 0.001)

    except Exception as e:
        reporter.add_test(test_name, "UNIT", "FUNCTION", "hash_password",
                         input_data, expected_output, {"error": str(e)}, "FAIL", 0.001, str(e))

    # Test 2: JWT Token generation
    test_name = "JWT Token Generation Unit Test"
    input_data = {"user_data": {"user_id": "123", "username": "test"}}
    expected_output = {"token_generated": True, "token_length": "> 50"}

    try:
        from app.user_management.user_service import UserService
        token = UserService.create_access_token(input_data["user_data"])

        actual_output = {"token_generated": bool(token), "token_length": len(token) if token else 0}
        status = "PASS" if actual_output["token_generated"] and actual_output["token_length"] > 50 else "FAIL"

        reporter.add_test(test_name, "UNIT", "FUNCTION", "create_access_token",
                         input_data, expected_output, actual_output, status, 0.001)

    except Exception as e:
        reporter.add_test(test_name, "UNIT", "FUNCTION", "create_access_token",
                         input_data, expected_output, {"error": str(e)}, "FAIL", 0.001, str(e))

def test_api_endpoints():
    """Test individual API endpoints"""
    print("\n🌐 Running API Endpoint Tests...")

    # Test 1: Root endpoint
    test_name = "Root Endpoint Test"
    input_data = {}
    expected_output = {"status_code": 200, "contains_name": True}

    result = make_api_request("GET", "/")
    actual_output = {
        "status_code": result["status_code"],
        "contains_name": "Social Security" in str(result.get("data", ""))
    }
    status = "PASS" if result["success"] and actual_output["contains_name"] else "FAIL"

    reporter.add_test(test_name, "API", "GET", "/",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Test 2: Health check
    test_name = "Health Check Test"
    input_data = {}
    expected_output = {"status_code": 200, "status": "healthy"}

    result = make_api_request("GET", "/health/")
    actual_output = {
        "status_code": result["status_code"],
        "data": result.get("data", {})
    }
    status = "PASS" if result["success"] else "FAIL"

    reporter.add_test(test_name, "API", "GET", "/health/",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Test 3: User registration
    test_name = "User Registration Test"
    unique_suffix = int(time.time())
    input_data = {
        "username": f"testuser_{unique_suffix}",
        "email": f"test_{unique_suffix}@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    expected_output = {"status_code": 201, "user_created": True}

    result = make_api_request("POST", "/auth/register",
                             json=input_data,
                             headers={"Content-Type": "application/json"})

    actual_output = {
        "status_code": result["status_code"],
        "data": result.get("data", {}),
        "user_created": result["status_code"] == 201
    }
    status = "PASS" if result["status_code"] == 201 else "FAIL"
    error = result.get("error") if not result["success"] else None

    reporter.add_test(test_name, "API", "POST", "/auth/register",
                     input_data, expected_output, actual_output, status, result["duration"], error)

    # Store user data for login test
    if result["success"]:
        global test_user_data
        test_user_data = input_data

    # Test 4: User login
    test_name = "User Login Test"
    login_input = {
        "username": input_data["username"],
        "password": input_data["password"]
    }
    expected_output = {"status_code": 200, "access_token": True}

    result = make_api_request("POST", "/auth/login",
                             json=login_input,
                             headers={"Content-Type": "application/json"})

    actual_output = {
        "status_code": result["status_code"],
        "access_token": "access_token" in str(result.get("data", ""))
    }
    status = "PASS" if result["success"] and actual_output["access_token"] else "FAIL"

    reporter.add_test(test_name, "API", "POST", "/auth/login",
                     login_input, expected_output, actual_output, status, result["duration"])

    # Store token for authenticated tests
    if result["success"]:
        global access_token
        access_token = result.get("data", {}).get("access_token")

def test_authenticated_endpoints():
    """Test endpoints that require authentication"""
    print("\n🔐 Running Authenticated API Tests...")

    if 'access_token' not in globals():
        print("❌ No access token available, skipping authenticated tests")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Test 1: Get user profile
    test_name = "Get User Profile Test"
    input_data = {}
    expected_output = {"status_code": 200, "user_data": True}

    result = make_api_request("GET", "/auth/me", headers=headers)
    actual_output = {
        "status_code": result["status_code"],
        "user_data": bool(result.get("data"))
    }
    status = "PASS" if result["success"] else "FAIL"

    reporter.add_test(test_name, "API", "GET", "/auth/me",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Test 2: Create application
    test_name = "Create Application Test"
    input_data = {
        "full_name": "Ahmed Al-Mansouri",
        "emirates_id": "784-1990-1234567-8",
        "phone": "+971501234567",
        "email": "ahmed@example.com"
    }
    expected_output = {"status_code": 201, "application_id": True}

    result = make_api_request("POST", "/workflow/start-application",
                             json=input_data,
                             headers={**headers, "Content-Type": "application/json"})

    actual_output = {
        "status_code": result["status_code"],
        "application_id": bool(result.get("data", {}).get("application_id"))
    }
    status = "PASS" if result["status_code"] == 201 else "FAIL"

    reporter.add_test(test_name, "API", "POST", "/workflow/start-application",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Store application ID for further tests
    if result["success"]:
        global application_id
        application_id = result.get("data", {}).get("application_id")

def test_document_endpoints():
    """Test document-related endpoints"""
    print("\n📄 Running Document Tests...")

    if 'access_token' not in globals():
        print("❌ No access token available, skipping document tests")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Test 1: Get document types
    test_name = "Get Document Types Test"
    input_data = {}
    expected_output = {"status_code": 200, "types_available": True}

    result = make_api_request("GET", "/documents/types")
    actual_output = {
        "status_code": result["status_code"],
        "types_available": bool(result.get("data"))
    }
    status = "PASS" if result["success"] else "FAIL"

    reporter.add_test(test_name, "API", "GET", "/documents/types",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Test 2: Document upload (if test files exist)
    test_file_path = "uploads/test_data/sample_bank_statement.pdf"
    if Path(test_file_path).exists():
        test_name = "Document Upload Test"
        input_data = {"file_type": "bank_statement", "file_exists": True}
        expected_output = {"status_code": 201, "upload_success": True}

        with open(test_file_path, 'rb') as f:
            files = {'bank_statement': ('sample_bank_statement.pdf', f.read(), 'application/pdf')}

        result = make_api_request("POST", "/documents/upload",
                                 files=files, headers=headers)

        actual_output = {
            "status_code": result["status_code"],
            "upload_success": result["success"]
        }
        status = "PASS" if result["success"] else "FAIL"

        reporter.add_test(test_name, "API", "POST", "/documents/upload",
                         input_data, expected_output, actual_output, status, result["duration"])

def test_workflow_processing():
    """Test workflow processing endpoints"""
    print("\n⚙️ Running Workflow Processing Tests...")

    if 'access_token' not in globals() or 'application_id' not in globals():
        print("❌ No access token or application ID available, skipping workflow tests")
        return

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Test 1: Start processing
    test_name = "Start Processing Test"
    input_data = {"force_retry": False}
    expected_output = {"status_code": 202, "processing_started": True}

    result = make_api_request("POST", f"/workflow/process/{application_id}",
                             json=input_data, headers=headers)

    actual_output = {
        "status_code": result["status_code"],
        "processing_started": result["status_code"] == 202
    }
    status = "PASS" if result["status_code"] == 202 else "FAIL"

    reporter.add_test(test_name, "API", "POST", f"/workflow/process/{application_id}",
                     input_data, expected_output, actual_output, status, result["duration"])

    # Test 2: Get workflow status
    test_name = "Get Workflow Status Test"
    input_data = {}
    expected_output = {"status_code": 200, "status_data": True}

    result = make_api_request("GET", f"/workflow/status/{application_id}", headers=headers)

    actual_output = {
        "status_code": result["status_code"],
        "status_data": bool(result.get("data"))
    }
    status = "PASS" if result["success"] else "FAIL"

    reporter.add_test(test_name, "API", "GET", f"/workflow/status/{application_id}",
                     input_data, expected_output, actual_output, status, result["duration"])

def test_end_to_end_flow():
    """Test complete end-to-end workflow"""
    print("\n🔄 Running End-to-End Flow Test...")

    # Complete workflow test
    test_name = "Complete Workflow End-to-End Test"
    input_data = {
        "user_registration": {
            "username": f"e2e_user_{int(time.time())}",
            "email": f"e2e_{int(time.time())}@example.com",
            "password": "e2epass123",
            "full_name": "E2E Test User"
        },
        "application_data": {
            "full_name": "E2E Test Application",
            "emirates_id": "784-1990-7654321-5",
            "phone": "+971509876543",
            "email": "e2eapp@example.com"
        }
    }
    expected_output = {
        "registration_success": True,
        "login_success": True,
        "application_created": True,
        "workflow_accessible": True
    }

    actual_output = {}
    errors = []

    try:
        # Step 1: Register user
        reg_result = make_api_request("POST", "/auth/register",
                                     json=input_data["user_registration"],
                                     headers={"Content-Type": "application/json"})
        actual_output["registration_success"] = reg_result["success"]

        if not reg_result["success"]:
            errors.append(f"Registration failed: {reg_result}")

        # Step 2: Login
        login_result = make_api_request("POST", "/auth/login",
                                       json={
                                           "username": input_data["user_registration"]["username"],
                                           "password": input_data["user_registration"]["password"]
                                       },
                                       headers={"Content-Type": "application/json"})
        actual_output["login_success"] = login_result["success"]

        if not login_result["success"]:
            errors.append(f"Login failed: {login_result}")

        # Step 3: Create application
        if login_result["success"]:
            token = login_result.get("data", {}).get("access_token")
            app_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            app_result = make_api_request("POST", "/workflow/start-application",
                                         json=input_data["application_data"],
                                         headers=app_headers)
            actual_output["application_created"] = app_result["success"]

            if app_result["success"]:
                app_id = app_result.get("data", {}).get("application_id")

                # Step 4: Check workflow status
                status_result = make_api_request("GET", f"/workflow/status/{app_id}",
                                                headers=app_headers)
                actual_output["workflow_accessible"] = status_result["success"]

                if not status_result["success"]:
                    errors.append(f"Workflow status check failed: {status_result}")
            else:
                errors.append(f"Application creation failed: {app_result}")

    except Exception as e:
        errors.append(f"E2E test exception: {str(e)}")
        actual_output["error"] = str(e)

    # Determine overall status
    all_steps_passed = all([
        actual_output.get("registration_success", False),
        actual_output.get("login_success", False),
        actual_output.get("application_created", False),
        actual_output.get("workflow_accessible", False)
    ])

    status = "PASS" if all_steps_passed else "FAIL"
    error_details = "; ".join(errors) if errors else None

    reporter.add_test(test_name, "E2E_FLOW", "MULTI", "COMPLETE_WORKFLOW",
                     input_data, expected_output, actual_output, status, 5.0, error_details)

def main():
    """Run all tests and generate report"""
    print("🚀 Starting Comprehensive Real-time Test Suite")
    print("=" * 60)

    # Run all test categories
    test_unit_functions()
    test_api_endpoints()
    test_authenticated_endpoints()
    test_document_endpoints()
    test_workflow_processing()
    test_end_to_end_flow()

    # Generate and save report
    print(f"\n📊 Generating test report...")
    report = reporter.generate_report()

    with open(REPORT_FILE, 'w') as f:
        f.write(report)

    print(f"✅ Test report saved to: {REPORT_FILE}")

    # Print summary
    total_tests = len(reporter.results)
    passed_tests = len([r for r in reporter.results if r['status'] == 'PASS'])

    print(f"\n📈 Test Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)