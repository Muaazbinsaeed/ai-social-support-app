#!/usr/bin/env python3
"""
Quick API Test Suite for Social Security AI System
Tests all 57 endpoints with efficient execution
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 5  # seconds

# Global variables
test_results = {}
test_token = None
test_user_data = {
    "username": f"testuser_{int(time.time())}",
    "email": f"test_{int(time.time())}@example.com",
    "password": "testpass123",
    "full_name": "Test User"
}

def make_request(method: str, endpoint: str, **kwargs) -> Dict:
    """Make HTTP request with timeout and error handling"""
    try:
        url = f"{BASE_URL}{endpoint}"
        kwargs.setdefault('timeout', TEST_TIMEOUT)

        response = requests.request(method, url, **kwargs)

        return {
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_time": response.elapsed.total_seconds(),
            "content_length": len(response.content),
            "headers": dict(response.headers),
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
        }
    except requests.RequestException as e:
        return {
            "status_code": 0,
            "success": False,
            "error": str(e),
            "response_time": 0
        }
    except Exception as e:
        return {
            "status_code": 0,
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "response_time": 0
        }

def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers"""
    global test_token
    if test_token:
        return {"Authorization": f"Bearer {test_token}"}
    return {}

def setup_auth() -> bool:
    """Setup authentication token"""
    global test_token, test_user_data

    # Try to register user
    result = make_request("POST", "/auth/register",
                         json=test_user_data,
                         headers={"Content-Type": "application/json"})

    # Try to login
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }

    result = make_request("POST", "/auth/login",
                         json=login_data,
                         headers={"Content-Type": "application/json"})

    if result.get("success") and isinstance(result.get("data"), dict):
        test_token = result["data"].get("access_token")
        return test_token is not None

    return False

def test_endpoint(module: str, method: str, endpoint: str, **kwargs):
    """Test a single endpoint"""
    result = make_request(method, endpoint, **kwargs)

    # Store result
    if module not in test_results:
        test_results[module] = {}

    test_results[module][f"{method} {endpoint}"] = {
        "status_code": result.get("status_code", 0),
        "success": result.get("success", False),
        "response_time_ms": int(result.get("response_time", 0) * 1000),
        "error": result.get("error"),
        "tested_at": datetime.now().isoformat()
    }

    # Print result
    status = "✅" if result.get("success") else "❌"
    time_ms = int(result.get("response_time", 0) * 1000)
    status_code = result.get("status_code", 0)
    print(f"{status} {method:6} {endpoint:50} {status_code:3} {time_ms:4}ms")

def run_all_tests():
    """Run all API endpoint tests"""
    print("🚀 Starting Quick API Test Suite")
    print("=" * 80)
    print(f"📍 Testing API at: {BASE_URL}")
    print(f"⏱️  Timeout per request: {TEST_TIMEOUT}s")
    print("=" * 80)

    start_time = time.time()

    # Test root endpoint
    print("\n📋 Root Endpoint")
    print("-" * 50)
    test_endpoint("root", "GET", "/")

    # Test health endpoints
    print("\n📋 Health Endpoints (3 endpoints)")
    print("-" * 50)
    test_endpoint("health", "GET", "/health/")
    test_endpoint("health", "GET", "/health/basic")
    test_endpoint("health", "GET", "/health/database")

    # Setup authentication
    print("\n🔐 Setting up authentication...")
    auth_setup = setup_auth()
    if auth_setup:
        print("✅ Authentication setup successful")
    else:
        print("❌ Authentication setup failed - some tests will be skipped")

    # Test authentication endpoints
    print("\n📋 Authentication Endpoints (7 endpoints)")
    print("-" * 50)
    test_endpoint("auth", "POST", "/auth/register",
                 json={"username": f"user_{int(time.time())}", "email": f"test_{int(time.time())}@test.com", "password": "pass123", "full_name": "Test"},
                 headers={"Content-Type": "application/json"})

    test_endpoint("auth", "POST", "/auth/login",
                 json={"username": test_user_data["username"], "password": test_user_data["password"]},
                 headers={"Content-Type": "application/json"})

    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("auth", "GET", "/auth/me", headers=headers)
        test_endpoint("auth", "GET", "/auth/status", headers=headers)
        test_endpoint("auth", "PUT", "/auth/password",
                     json={"current_password": test_user_data["password"], "new_password": "newpass123"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("auth", "POST", "/auth/logout", headers=headers)
        test_endpoint("auth", "POST", "/auth/refresh", headers=headers)

    # Test document endpoints
    print("\n📋 Document Endpoints (4 endpoints)")
    print("-" * 50)
    test_endpoint("documents", "GET", "/documents/types")

    if auth_setup:
        headers = get_auth_headers()
        # Test document upload with fake files
        files = {
            "bank_statement": ("test.pdf", b"fake pdf", "application/pdf"),
            "emirates_id": ("test.jpg", b"fake image", "image/jpeg")
        }
        test_endpoint("documents", "POST", "/documents/upload", headers=headers, files=files)

        fake_doc_id = str(uuid.uuid4())
        test_endpoint("documents", "GET", f"/documents/status/{fake_doc_id}", headers=headers)
        test_endpoint("documents", "DELETE", f"/documents/{fake_doc_id}", headers=headers)

    # Test user management endpoints
    print("\n📋 User Management Endpoints (8 endpoints)")
    print("-" * 50)
    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("users", "GET", "/users/profile", headers=headers)
        test_endpoint("users", "PUT", "/users/profile",
                     json={"full_name": "Updated Name", "phone": "+971501234567"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("users", "POST", "/users/change-password",
                     json={"current_password": "testpass123", "new_password": "newpass456"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("users", "DELETE", "/users/account", headers=headers)
        test_endpoint("users", "GET", "/users/", headers=headers)  # Admin only - expect 403
        test_endpoint("users", "GET", f"/users/{uuid.uuid4()}", headers=headers)  # Admin only
        test_endpoint("users", "PUT", f"/users/{uuid.uuid4()}/activation",
                     json={"is_active": False},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("users", "GET", "/users/stats/overview", headers=headers)

    # Test document management endpoints
    print("\n📋 Document Management Endpoints (8 endpoints)")
    print("-" * 50)
    test_endpoint("doc_mgmt", "GET", "/document-management/types/supported")

    if auth_setup:
        headers = get_auth_headers()
        files = {"file": ("test.pdf", b"fake pdf", "application/pdf")}
        data = {"document_type": "bank_statement", "description": "Test doc"}
        test_endpoint("doc_mgmt", "POST", "/document-management/upload", headers=headers, files=files, data=data)

        test_endpoint("doc_mgmt", "GET", "/document-management/", headers=headers)

        fake_doc_id = str(uuid.uuid4())
        test_endpoint("doc_mgmt", "GET", f"/document-management/{fake_doc_id}", headers=headers)
        test_endpoint("doc_mgmt", "PUT", f"/document-management/{fake_doc_id}",
                     json={"description": "Updated desc"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("doc_mgmt", "DELETE", f"/document-management/{fake_doc_id}", headers=headers)
        test_endpoint("doc_mgmt", "GET", f"/document-management/{fake_doc_id}/download", headers=headers)
        test_endpoint("doc_mgmt", "GET", f"/document-management/{fake_doc_id}/processing-logs", headers=headers)

    # Test OCR endpoints
    print("\n📋 OCR Endpoints (5 endpoints)")
    print("-" * 50)
    test_endpoint("ocr", "GET", "/ocr/health")

    if auth_setup:
        headers = get_auth_headers()
        fake_doc_id = str(uuid.uuid4())
        test_endpoint("ocr", "POST", f"/ocr/documents/{fake_doc_id}",
                     json={"language_hints": ["en"], "preprocess": True},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("ocr", "POST", "/ocr/batch",
                     json={"document_ids": [str(uuid.uuid4())], "language_hints": ["en"]},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("ocr", "POST", "/ocr/direct",
                     json={"image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "language_hints": ["en"]},
                     headers={**headers, "Content-Type": "application/json"})

        files = {"file": ("test.jpg", b"fake image", "image/jpeg")}
        data = {"language_hints": "en"}
        test_endpoint("ocr", "POST", "/ocr/upload-and-extract", headers=headers, files=files, data=data)

    # Test chatbot endpoints
    print("\n📋 Chatbot Endpoints (6 endpoints)")
    print("-" * 50)
    test_endpoint("chatbot", "GET", "/chatbot/health")
    test_endpoint("chatbot", "GET", "/chatbot/quick-help")

    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("chatbot", "POST", "/chatbot/chat",
                     json={"message": "Hello", "session_id": str(uuid.uuid4())},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("chatbot", "GET", "/chatbot/sessions", headers=headers)

        fake_session_id = str(uuid.uuid4())
        test_endpoint("chatbot", "GET", f"/chatbot/sessions/{fake_session_id}", headers=headers)
        test_endpoint("chatbot", "DELETE", f"/chatbot/sessions/{fake_session_id}", headers=headers)

    # Test decision endpoints
    print("\n📋 Decision Endpoints (5 endpoints)")
    print("-" * 50)
    test_endpoint("decisions", "GET", "/decisions/health")
    test_endpoint("decisions", "GET", "/decisions/criteria")

    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("decisions", "POST", "/decisions/make-decision",
                     json={"application_id": str(uuid.uuid4()), "factors": {"income": 5000, "balance": 2000}},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("decisions", "POST", "/decisions/batch",
                     json={"applications": [{"application_id": str(uuid.uuid4()), "factors": {"income": 4000}}]},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("decisions", "POST", f"/decisions/explain/{uuid.uuid4()}",
                     json={"detail_level": "comprehensive"},
                     headers={**headers, "Content-Type": "application/json"})

    # Test analysis endpoints
    print("\n📋 Analysis Endpoints (4 endpoints)")
    print("-" * 50)
    if auth_setup:
        headers = get_auth_headers()
        fake_doc_id = str(uuid.uuid4())
        test_endpoint("analysis", "POST", f"/analysis/documents/{fake_doc_id}",
                     json={"analysis_type": "full", "custom_prompt": "Analyze this"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("analysis", "POST", "/analysis/bulk",
                     json={"document_ids": [str(uuid.uuid4())], "analysis_type": "financial"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("analysis", "POST", "/analysis/query",
                     json={"question": "What is this?", "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="},
                     headers={**headers, "Content-Type": "application/json"})

        files = {"file": ("test.pdf", b"fake pdf", "application/pdf")}
        data = {"analysis_type": "financial"}
        test_endpoint("analysis", "POST", "/analysis/upload-and-analyze", headers=headers, files=files, data=data)

    # Test application endpoints
    print("\n📋 Application Endpoints (4 endpoints)")
    print("-" * 50)
    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("applications", "GET", "/applications/", headers=headers)

        fake_app_id = str(uuid.uuid4())
        test_endpoint("applications", "GET", f"/applications/{fake_app_id}", headers=headers)
        test_endpoint("applications", "PUT", f"/applications/{fake_app_id}",
                     json={"full_name": "Updated Name"},
                     headers={**headers, "Content-Type": "application/json"})
        test_endpoint("applications", "GET", f"/applications/{fake_app_id}/results", headers=headers)

    # Test workflow endpoints
    print("\n📋 Workflow Endpoints (3 endpoints)")
    print("-" * 50)
    if auth_setup:
        headers = get_auth_headers()
        test_endpoint("workflow", "POST", "/workflow/start-application",
                     json={"full_name": "Test User", "emirates_id": "784-1990-1234567-8",
                           "phone": "+971501234567", "email": "test@example.com"},
                     headers={**headers, "Content-Type": "application/json"})

        fake_app_id = str(uuid.uuid4())
        test_endpoint("workflow", "GET", f"/workflow/status/{fake_app_id}", headers=headers)
        test_endpoint("workflow", "POST", f"/workflow/process/{fake_app_id}",
                     json={"force_retry": False},
                     headers={**headers, "Content-Type": "application/json"})

    # Calculate summary
    total_time = time.time() - start_time

    # Generate summary
    total_tests = 0
    successful_tests = 0

    for module, endpoints in test_results.items():
        for endpoint, result in endpoints.items():
            total_tests += 1
            if result["success"]:
                successful_tests += 1

    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"🔢 Total Endpoints Tested: {total_tests}")
    print(f"✅ Successful Tests: {successful_tests}")
    print(f"❌ Failed Tests: {total_tests - successful_tests}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    print(f"⏱️  Total Execution Time: {total_time:.1f}s")
    print(f"📊 Average Response Time: {sum(sum(r['response_time_ms'] for r in e.values()) for e in test_results.values()) / total_tests:.0f}ms")

    # Module breakdown
    print("\n📋 Results by Module:")
    print("-" * 50)
    for module, endpoints in test_results.items():
        module_total = len(endpoints)
        module_success = sum(1 for r in endpoints.values() if r["success"])
        module_rate = (module_success / module_total * 100) if module_total > 0 else 0
        print(f"{module:15} {module_success:2}/{module_total:2} ({module_rate:5.1f}%)")

    # Save detailed results
    output_file = "quick_api_test_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": f"{success_rate:.1f}%",
                "execution_time_seconds": round(total_time, 1),
                "tested_at": datetime.now().isoformat()
            },
            "results": test_results
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print("🏁 Quick API test completed!")

    return test_results

if __name__ == "__main__":
    run_all_tests()