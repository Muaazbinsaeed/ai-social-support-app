#!/usr/bin/env python3
"""
Complete API Analysis - All 58 Endpoints with Success/Failure Tracking
Social Security AI - Comprehensive Status Report
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import traceback

# Configuration
BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 60  # Increased timeout for AI operations

# Test Results Storage
test_results = []
auth_token = None
auth_headers = {}
test_user_data = {}
application_data = {}
document_data = {}

class APITestResult:
    def __init__(self, endpoint: str, method: str, category: str):
        self.endpoint = endpoint
        self.method = method
        self.category = category
        self.success = False
        self.status_code = None
        self.response_time = 0
        self.error_message = ""
        self.expected_time = ""
        self.actual_response = None

    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "category": self.category,
            "success": self.success,
            "status_code": self.status_code,
            "response_time": f"{self.response_time:.2f}s",
            "expected_time": self.expected_time,
            "error_message": self.error_message,
            "has_response": self.actual_response is not None
        }

def test_endpoint(method: str, endpoint: str, data: Optional[Dict] = None,
                 files: Optional[Dict] = None, use_auth: bool = False,
                 category: str = "Unknown", expected_time: str = "< 5s") -> APITestResult:
    """Test a single endpoint and return detailed results"""

    result = APITestResult(endpoint, method, category)
    result.expected_time = expected_time

    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if use_auth and auth_headers:
        headers.update(auth_headers)

    if files:
        headers.pop("Content-Type", None)

    start_time = time.time()

    try:
        print(f"🔄 Testing {method} {endpoint}")

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, files=files, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Unsupported method: {method}")

        result.response_time = time.time() - start_time
        result.status_code = response.status_code

        # Consider 2xx and 3xx as success, some 4xx as expected (like 401 for unauthorized tests)
        if 200 <= response.status_code < 400:
            result.success = True
        elif response.status_code in [401, 403] and not use_auth:
            result.success = True  # Expected for unauthorized access
            result.error_message = "Expected unauthorized (testing security)"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"

        try:
            result.actual_response = response.json()
        except:
            result.actual_response = response.text[:500]

        # Success indicators
        status_indicator = "✅" if result.success else "❌"
        time_indicator = "⚡" if result.response_time < 5 else "⏳" if result.response_time < 30 else "🐌"

        print(f"  {status_indicator} {time_indicator} {result.status_code} ({result.response_time:.2f}s)")

        if not result.success:
            print(f"    Error: {result.error_message}")

    except requests.exceptions.Timeout:
        result.response_time = time.time() - start_time
        result.error_message = f"Timeout after {result.response_time:.2f}s"
        print(f"  ⏰ TIMEOUT ({result.response_time:.2f}s)")

    except requests.exceptions.ConnectionError:
        result.error_message = "Connection error - service may be down"
        print(f"  🚫 CONNECTION ERROR")

    except Exception as e:
        result.error_message = f"Unexpected error: {str(e)}"
        print(f"  💥 ERROR: {str(e)}")

    test_results.append(result)
    return result

def create_test_files():
    """Create sample files for testing"""
    try:
        # Create a valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Arial >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 50 >>
stream
BT
/F1 12 Tf
100 700 Td
(Sample Bank Statement) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
420
%%EOF"""

        with open("test_bank_statement.pdf", "wb") as f:
            f.write(pdf_content)

        # Create a valid PNG
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'

        with open("test_emirates_id.png", "wb") as f:
            f.write(png_content)

        return True
    except Exception as e:
        print(f"❌ Failed to create test files: {e}")
        return False

def test_all_endpoints():
    """Test all 58 endpoints systematically"""
    global auth_token, auth_headers, test_user_data, application_data, document_data

    print("🚀 COMPREHENSIVE API TESTING - ALL 58 ENDPOINTS")
    print("=" * 80)

    # Generate unique test data
    timestamp = int(time.time())
    test_user_data = {
        "username": f"apitest_{timestamp}",
        "email": f"apitest_{timestamp}@test.com",
        "password": "testpass123",
        "full_name": f"API Test User {timestamp}"
    }

    # ============================================================================
    # 1. ROOT API (1 endpoint)
    # ============================================================================
    print("\n📍 1. ROOT API")
    test_endpoint("GET", "/", category="Root", expected_time="< 1s")

    # ============================================================================
    # 2. HEALTH CHECK (3 endpoints)
    # ============================================================================
    print("\n🏥 2. HEALTH CHECK")
    test_endpoint("GET", "/health/basic", category="Health", expected_time="< 1s")
    test_endpoint("GET", "/health/database", category="Health", expected_time="< 2s")
    test_endpoint("GET", "/health/", category="Health", expected_time="< 5s")

    # ============================================================================
    # 3. AUTHENTICATION (7 endpoints)
    # ============================================================================
    print("\n🔐 3. AUTHENTICATION")

    # Register user
    result = test_endpoint("POST", "/auth/register", data=test_user_data,
                          category="Authentication", expected_time="< 3s")
    if result.success and result.actual_response:
        test_user_data.update(result.actual_response)

    # Login
    login_data = {"username": test_user_data["username"], "password": test_user_data["password"]}
    result = test_endpoint("POST", "/auth/login", data=login_data,
                          category="Authentication", expected_time="< 2s")
    if result.success and result.actual_response:
        auth_token = result.actual_response.get("access_token")
        if auth_token:
            auth_headers = {"Authorization": f"Bearer {auth_token}"}
            print(f"  🔑 Auth token obtained: {auth_token[:20]}...")

    # Other auth endpoints
    test_endpoint("GET", "/auth/me", use_auth=True, category="Authentication", expected_time="< 1s")
    test_endpoint("GET", "/auth/status", use_auth=True, category="Authentication", expected_time="< 1s")

    # Password update
    pwd_data = {"current_password": test_user_data["password"], "new_password": "newpass123"}
    test_endpoint("PUT", "/auth/password", data=pwd_data, use_auth=True,
                 category="Authentication", expected_time="< 2s")

    test_endpoint("POST", "/auth/refresh", use_auth=True, category="Authentication", expected_time="< 2s")
    test_endpoint("POST", "/auth/logout", use_auth=True, category="Authentication", expected_time="< 1s")

    # ============================================================================
    # 4. DOCUMENT UPLOAD (4 endpoints)
    # ============================================================================
    print("\n📄 4. DOCUMENT UPLOAD")

    test_endpoint("GET", "/documents/types", category="Documents", expected_time="< 1s")

    # Document status (will fail without valid ID, that's expected)
    dummy_id = str(uuid.uuid4())
    test_endpoint("GET", f"/documents/status/{dummy_id}", use_auth=True,
                 category="Documents", expected_time="< 2s")

    # Document upload
    if create_test_files():
        files = {
            'bank_statement': ('test_bank_statement.pdf', open('test_bank_statement.pdf', 'rb'), 'application/pdf'),
            'emirates_id': ('test_emirates_id.png', open('test_emirates_id.png', 'rb'), 'image/png')
        }

        result = test_endpoint("POST", "/documents/upload", files=files, use_auth=True,
                              category="Documents", expected_time="< 10s")

        # Close files
        for file_obj in files.values():
            file_obj[1].close()

        if result.success and result.actual_response:
            document_data = result.actual_response

    # Document deletion (will fail without valid ID)
    test_endpoint("DELETE", f"/documents/{dummy_id}", use_auth=True,
                 category="Documents", expected_time="< 2s")

    # ============================================================================
    # 5. DOCUMENT MANAGEMENT (8 endpoints)
    # ============================================================================
    print("\n📁 5. DOCUMENT MANAGEMENT")

    test_endpoint("GET", "/document-management/types/supported", category="Doc Management", expected_time="< 1s")
    test_endpoint("GET", "/document-management/", use_auth=True, category="Doc Management", expected_time="< 3s")

    # Upload via document management
    if os.path.exists("test_bank_statement.pdf"):
        files = {'file': ('test_bank_statement.pdf', open('test_bank_statement.pdf', 'rb'), 'application/pdf')}
        data = {'document_type': 'bank_statement'}

        result = test_endpoint("POST", "/document-management/upload", files=files, data=data, use_auth=True,
                              category="Doc Management", expected_time="< 15s")

        files['file'][1].close()

        if result.success and result.actual_response:
            doc_id = result.actual_response.get("document_id")
            if doc_id:
                test_endpoint("GET", f"/document-management/{doc_id}", use_auth=True,
                             category="Doc Management", expected_time="< 2s")
                test_endpoint("PUT", f"/document-management/{doc_id}",
                             data={"document_type": "updated"}, use_auth=True,
                             category="Doc Management", expected_time="< 3s")
                test_endpoint("GET", f"/document-management/{doc_id}/processing-logs", use_auth=True,
                             category="Doc Management", expected_time="< 2s")
                test_endpoint("GET", f"/document-management/{doc_id}/download", use_auth=True,
                             category="Doc Management", expected_time="< 5s")
                test_endpoint("DELETE", f"/document-management/{doc_id}", use_auth=True,
                             category="Doc Management", expected_time="< 3s")
            else:
                # Test with dummy IDs
                test_endpoint("GET", f"/document-management/{dummy_id}", use_auth=True,
                             category="Doc Management", expected_time="< 2s")
                test_endpoint("PUT", f"/document-management/{dummy_id}",
                             data={"document_type": "test"}, use_auth=True,
                             category="Doc Management", expected_time="< 3s")

    # ============================================================================
    # 6. WORKFLOW MANAGEMENT (4 endpoints)
    # ============================================================================
    print("\n🔄 6. WORKFLOW MANAGEMENT")

    # Start application
    app_data = {
        "full_name": "Test Application User",
        "emirates_id": "784-1990-1234567-8",
        "phone": "+971501234567",
        "email": f"app.test.{timestamp}@test.com"
    }

    result = test_endpoint("POST", "/workflow/start-application", data=app_data, use_auth=True,
                          category="Workflow", expected_time="< 5s")

    if result.success and result.actual_response:
        app_id = result.actual_response.get("application_id")
        application_data = result.actual_response

        if app_id:
            # Upload documents to application
            if os.path.exists("test_bank_statement.pdf"):
                files = {
                    'bank_statement': ('test_bank_statement.pdf', open('test_bank_statement.pdf', 'rb'), 'application/pdf'),
                    'emirates_id': ('test_emirates_id.png', open('test_emirates_id.png', 'rb'), 'image/png')
                }

                test_endpoint("POST", f"/workflow/upload-documents/{app_id}", files=files, use_auth=True,
                             category="Workflow", expected_time="< 15s")

                for file_obj in files.values():
                    file_obj[1].close()

            # Check status
            test_endpoint("GET", f"/workflow/status/{app_id}", use_auth=True,
                         category="Workflow", expected_time="< 3s")

            # Process application
            test_endpoint("POST", f"/workflow/process/{app_id}", data={"force_retry": False}, use_auth=True,
                         category="Workflow", expected_time="< 10s")
    else:
        # Test with dummy ID
        test_endpoint("GET", f"/workflow/status/{dummy_id}", use_auth=True,
                     category="Workflow", expected_time="< 3s")

    # ============================================================================
    # 7. APPLICATION MANAGEMENT (4 endpoints)
    # ============================================================================
    print("\n📋 7. APPLICATION MANAGEMENT")

    test_endpoint("GET", "/applications/", use_auth=True, category="Applications", expected_time="< 3s")

    app_id = application_data.get("application_id", dummy_id)
    test_endpoint("GET", f"/applications/{app_id}", use_auth=True, category="Applications", expected_time="< 2s")
    test_endpoint("PUT", f"/applications/{app_id}", data={"full_name": "Updated Name"}, use_auth=True,
                 category="Applications", expected_time="< 3s")
    test_endpoint("GET", f"/applications/{app_id}/results", use_auth=True,
                 category="Applications", expected_time="< 5s")

    # ============================================================================
    # 8. AI ANALYSIS (4 endpoints)
    # ============================================================================
    print("\n🧠 8. AI ANALYSIS")

    analysis_data = {"documents": ["test.pdf"], "analysis_type": "financial"}
    test_endpoint("POST", "/analysis/bulk", data=analysis_data, use_auth=True,
                 category="AI Analysis", expected_time="< 30s")

    query_data = {"query": "What is the income?", "context": "financial"}
    test_endpoint("POST", "/analysis/query", data=query_data, use_auth=True,
                 category="AI Analysis", expected_time="< 20s")

    # Upload and analyze
    if os.path.exists("test_bank_statement.pdf"):
        files = {'file': ('test_bank_statement.pdf', open('test_bank_statement.pdf', 'rb'), 'application/pdf')}
        data = {'analysis_type': 'financial'}

        test_endpoint("POST", "/analysis/upload-and-analyze", files=files, data=data, use_auth=True,
                     category="AI Analysis", expected_time="< 45s")

        files['file'][1].close()

    # Document analysis
    test_endpoint("POST", f"/analysis/documents/{dummy_id}",
                 data={"analysis_type": "full"}, use_auth=True,
                 category="AI Analysis", expected_time="< 30s")

    # ============================================================================
    # 9. OCR PROCESSING (5 endpoints)
    # ============================================================================
    print("\n👁️ 9. OCR PROCESSING")

    test_endpoint("GET", "/ocr/health", category="OCR", expected_time="< 2s")

    batch_data = {"documents": ["test.pdf"], "language_hints": ["en"]}
    test_endpoint("POST", "/ocr/batch", data=batch_data, use_auth=True,
                 category="OCR", expected_time="< 30s")

    # Direct OCR
    direct_data = {"image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+AAwMCAO+ip1sAAAAASUVORK5CYII=", "language_hints": ["en"]}
    test_endpoint("POST", "/ocr/direct", data=direct_data, use_auth=True,
                 category="OCR", expected_time="< 15s")

    # Upload and extract
    if os.path.exists("test_bank_statement.pdf"):
        files = {'file': ('test_bank_statement.pdf', open('test_bank_statement.pdf', 'rb'), 'application/pdf')}
        data = {'language_hints': '["en"]'}

        test_endpoint("POST", "/ocr/upload-and-extract", files=files, data=data, use_auth=True,
                     category="OCR", expected_time="< 30s")

        files['file'][1].close()

    # Document OCR
    test_endpoint("POST", f"/ocr/documents/{dummy_id}",
                 data={"language_hints": ["en"]}, use_auth=True,
                 category="OCR", expected_time="< 25s")

    # ============================================================================
    # 10. DECISION MAKING (5 endpoints)
    # ============================================================================
    print("\n⚖️ 10. DECISION MAKING")

    test_endpoint("GET", "/decisions/health", category="Decisions", expected_time="< 2s")
    test_endpoint("GET", "/decisions/criteria", category="Decisions", expected_time="< 1s")

    # Make decision
    decision_data = {
        "application_id": app_id,
        "factors": {"income": 5000, "balance": 10000}
    }
    result = test_endpoint("POST", "/decisions/make-decision", data=decision_data, use_auth=True,
                          category="Decisions", expected_time="< 20s")

    # Batch decisions
    batch_decision_data = {
        "applications": [
            {"application_id": str(uuid.uuid4()), "factors": {"income": 6000}},
            {"application_id": str(uuid.uuid4()), "factors": {"income": 3000}}
        ]
    }
    test_endpoint("POST", "/decisions/batch", data=batch_decision_data, use_auth=True,
                 category="Decisions", expected_time="< 30s")

    # Explain decision
    test_endpoint("POST", f"/decisions/explain/{dummy_id}", use_auth=True,
                 category="Decisions", expected_time="< 15s")

    # ============================================================================
    # 11. CHATBOT (6 endpoints)
    # ============================================================================
    print("\n💬 11. CHATBOT")

    test_endpoint("GET", "/chatbot/health", category="Chatbot", expected_time="< 2s")
    test_endpoint("GET", "/chatbot/quick-help", category="Chatbot", expected_time="< 1s")

    # Chat
    chat_data = {"message": "Hello", "session_id": f"test_session_{timestamp}"}
    test_endpoint("POST", "/chatbot/chat", data=chat_data, use_auth=True,
                 category="Chatbot", expected_time="< 20s")

    test_endpoint("GET", "/chatbot/sessions", use_auth=True, category="Chatbot", expected_time="< 2s")
    test_endpoint("GET", f"/chatbot/sessions/test_session_{timestamp}", use_auth=True,
                 category="Chatbot", expected_time="< 2s")
    test_endpoint("DELETE", f"/chatbot/sessions/test_session_{timestamp}", use_auth=True,
                 category="Chatbot", expected_time="< 2s")

    # ============================================================================
    # 12. USER MANAGEMENT (8 endpoints)
    # ============================================================================
    print("\n👥 12. USER MANAGEMENT")

    test_endpoint("GET", "/users/profile", use_auth=True, category="User Management", expected_time="< 2s")

    profile_data = {"full_name": "Updated Profile Name"}
    test_endpoint("PUT", "/users/profile", data=profile_data, use_auth=True,
                 category="User Management", expected_time="< 3s")

    pwd_change_data = {"current_password": "newpass123", "new_password": "finalpass123"}
    test_endpoint("POST", "/users/change-password", data=pwd_change_data, use_auth=True,
                 category="User Management", expected_time="< 3s")

    test_endpoint("GET", "/users/", use_auth=True, category="User Management", expected_time="< 3s")
    test_endpoint("GET", "/users/stats/overview", use_auth=True, category="User Management", expected_time="< 3s")

    user_id = test_user_data.get("id", dummy_id)
    test_endpoint("GET", f"/users/{user_id}", use_auth=True, category="User Management", expected_time="< 2s")
    test_endpoint("PUT", f"/users/{user_id}/activation", data={"is_active": True}, use_auth=True,
                 category="User Management", expected_time="< 3s")

    # Final cleanup
    test_endpoint("DELETE", "/users/account", use_auth=True, category="User Management", expected_time="< 3s")

def cleanup_files():
    """Clean up test files"""
    try:
        for filename in ["test_bank_statement.pdf", "test_emirates_id.png"]:
            if os.path.exists(filename):
                os.remove(filename)
        print("🧹 Cleaned up test files")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

def generate_comprehensive_report():
    """Generate detailed report of all test results"""

    print("\n" + "=" * 100)
    print("📊 COMPREHENSIVE API TEST RESULTS - ALL 58 ENDPOINTS")
    print("=" * 100)

    # Summary by category
    categories = {}
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r.success)

    for result in test_results:
        if result.category not in categories:
            categories[result.category] = {"total": 0, "success": 0, "failed": 0, "timeouts": 0}

        categories[result.category]["total"] += 1
        if result.success:
            categories[result.category]["success"] += 1
        else:
            categories[result.category]["failed"] += 1
            if "timeout" in result.error_message.lower():
                categories[result.category]["timeouts"] += 1

    print(f"\n🎯 OVERALL SUMMARY:")
    print(f"   Total Endpoints Tested: {total_tests}")
    print(f"   Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"   Failed: {total_tests - successful_tests} ({(total_tests - successful_tests)/total_tests*100:.1f}%)")

    print(f"\n📊 RESULTS BY CATEGORY:")
    for category, stats in categories.items():
        success_rate = stats["success"] / stats["total"] * 100
        status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
        print(f"   {status_icon} {category:15} | {stats['success']:2d}/{stats['total']:2d} ({success_rate:5.1f}%) | Timeouts: {stats['timeouts']}")

    print(f"\n📋 DETAILED RESULTS:")
    print("-" * 120)
    print(f"{'Endpoint':<45} {'Method':<6} {'Status':<6} {'Time':<8} {'Expected':<10} {'Result'}")
    print("-" * 120)

    for result in test_results:
        status_icon = "✅" if result.success else "❌"
        time_icon = "⚡" if result.response_time < 5 else "⏳" if result.response_time < 30 else "🐌"

        endpoint_display = result.endpoint[:44]
        time_display = f"{result.response_time:.1f}s"
        status_display = str(result.status_code) if result.status_code else "ERR"

        print(f"{endpoint_display:<45} {result.method:<6} {status_display:<6} {time_display:<8} {result.expected_time:<10} {status_icon} {time_icon}")

        if not result.success and result.error_message:
            print(f"{'':45}        Error: {result.error_message[:60]}")

    print("\n⏱️ TIMING ANALYSIS:")
    fast_endpoints = [r for r in test_results if r.response_time < 1.0 and r.success]
    medium_endpoints = [r for r in test_results if 1.0 <= r.response_time < 5.0 and r.success]
    slow_endpoints = [r for r in test_results if r.response_time >= 5.0 and r.success]
    timeout_endpoints = [r for r in test_results if "timeout" in r.error_message.lower()]

    print(f"   ⚡ Fast (< 1s):     {len(fast_endpoints):2d} endpoints")
    print(f"   🚀 Medium (1-5s):  {len(medium_endpoints):2d} endpoints")
    print(f"   🐌 Slow (> 5s):    {len(slow_endpoints):2d} endpoints")
    print(f"   ⏰ Timeouts:       {len(timeout_endpoints):2d} endpoints")

    if slow_endpoints:
        print(f"\n🐌 SLOW ENDPOINTS (> 5s):")
        for result in sorted(slow_endpoints, key=lambda x: x.response_time, reverse=True):
            print(f"   • {result.method} {result.endpoint} - {result.response_time:.1f}s")

    if timeout_endpoints:
        print(f"\n⏰ TIMEOUT ENDPOINTS:")
        for result in timeout_endpoints:
            print(f"   • {result.method} {result.endpoint} - {result.error_message}")

    # Failed endpoints analysis
    failed_endpoints = [r for r in test_results if not r.success]
    if failed_endpoints:
        print(f"\n❌ FAILED ENDPOINTS ({len(failed_endpoints)}):")

        # Group by error type
        error_types = {}
        for result in failed_endpoints:
            error_key = "Timeout" if "timeout" in result.error_message.lower() else \
                       "Connection" if "connection" in result.error_message.lower() else \
                       "HTTP Error" if result.status_code and result.status_code >= 400 else \
                       "Other"

            if error_key not in error_types:
                error_types[error_key] = []
            error_types[error_key].append(result)

        for error_type, results in error_types.items():
            print(f"\n   {error_type} ({len(results)} endpoints):")
            for result in results:
                print(f"     • {result.method} {result.endpoint}")
                print(f"       Status: {result.status_code}, Error: {result.error_message[:80]}")

    print(f"\n💡 RECOMMENDATIONS:")

    if len(timeout_endpoints) > 0:
        print("   🔧 Some endpoints are timing out - consider:")
        print("      • Optimizing AI model response times")
        print("      • Adding background processing for heavy operations")
        print("      • Implementing request queuing")

    if len(slow_endpoints) > 5:
        print("   ⚡ Many endpoints are slow - consider:")
        print("      • Database query optimization")
        print("      • Caching frequently accessed data")
        print("      • Reducing AI processing time")

    if any("qdrant" in r.error_message.lower() for r in failed_endpoints):
        print("   📊 Qdrant vector database is unavailable (this is optional)")

    if any("401" in str(r.status_code) for r in failed_endpoints):
        print("   🔐 Some authentication issues detected")

    print(f"\n🎭 SYSTEM STATUS:")
    if successful_tests / total_tests >= 0.9:
        print("   🟢 EXCELLENT - System is production ready")
    elif successful_tests / total_tests >= 0.8:
        print("   🟡 GOOD - System is mostly functional with minor issues")
    elif successful_tests / total_tests >= 0.7:
        print("   🟠 FAIR - System has some issues that should be addressed")
    else:
        print("   🔴 POOR - System has significant issues requiring immediate attention")

if __name__ == "__main__":
    try:
        print("🚀 Starting Comprehensive API Analysis...")
        test_all_endpoints()

    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")

    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

    finally:
        cleanup_files()
        generate_comprehensive_report()

        # Save results to JSON
        try:
            with open(f"api_test_results_{int(time.time())}.json", "w") as f:
                json.dump([r.to_dict() for r in test_results], f, indent=2)
            print(f"\n💾 Results saved to api_test_results_{int(time.time())}.json")
        except Exception as e:
            print(f"⚠️ Could not save results: {e}")