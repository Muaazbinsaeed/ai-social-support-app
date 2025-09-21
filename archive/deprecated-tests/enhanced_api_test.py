#!/usr/bin/env python3
"""
Enhanced API Testing with Error Detection and Timeout Handling
Social Security AI - Comprehensive API Testing Suite
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import traceback

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
REQUEST_TIMEOUT = 30  # seconds
PROCESSING_TIMEOUT = 120  # seconds for background processing

# Global variables to store authentication and workflow data
auth_token = None
auth_headers = {}
test_user_data = {}
application_data = {}
document_data = {}
session_data = {}

# Error tracking
errors_encountered = []
timeouts_encountered = []
processing_delays = []

def log_error(endpoint: str, error: str, details: str = ""):
    """Log errors for analysis"""
    error_info = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "error": error,
        "details": details
    }
    errors_encountered.append(error_info)
    print(f"❌ ERROR [{endpoint}]: {error}")
    if details:
        print(f"   Details: {details}")

def log_timeout(endpoint: str, duration: float):
    """Log timeouts for analysis"""
    timeout_info = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "duration": duration
    }
    timeouts_encountered.append(timeout_info)
    print(f"⏰ TIMEOUT [{endpoint}]: {duration:.2f}s")

def log_processing_delay(endpoint: str, duration: float):
    """Log processing delays for analysis"""
    delay_info = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "duration": duration
    }
    processing_delays.append(delay_info)
    print(f"⏳ PROCESSING DELAY [{endpoint}]: {duration:.2f}s")

def print_response(title: str, response: requests.Response, show_full_response: bool = True):
    """Print formatted API response with error detection"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")
    print(f"URL: {response.url}")
    print(f"Status Code: {response.status_code}")

    # Check for error status codes
    if response.status_code >= 400:
        print(f"⚠️  ERROR STATUS CODE: {response.status_code}")
        log_error(response.url, f"HTTP {response.status_code}", response.text[:500])

    print(f"Headers: {dict(response.headers)}")

    if show_full_response:
        try:
            response_json = response.json()
            print(f"Response Body:")
            print(json.dumps(response_json, indent=2, default=str))

            # Check for specific error indicators in response
            if isinstance(response_json, dict):
                if "error" in response_json:
                    log_error(response.url, "API Error", str(response_json.get("error")))
                if "message" in response_json and "error" in str(response_json["message"]).lower():
                    log_error(response.url, "Error Message", response_json["message"])

        except json.JSONDecodeError as e:
            print(f"Response Text: {response.text}")
            log_error(response.url, "JSON Decode Error", str(e))
        except Exception as e:
            print(f"Response processing error: {e}")
            log_error(response.url, "Response Processing Error", str(e))
    else:
        print(f"Response Length: {len(response.text)} characters")

    print(f"{'='*60}\n")
    return response

def make_request(method: str, endpoint: str, data: Optional[Dict] = None,
                files: Optional[Dict] = None, headers: Optional[Dict] = None,
                use_auth: bool = False, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """Make HTTP request with proper error handling and timeout detection"""
    url = f"{BASE_URL}{endpoint}"
    request_headers = headers.copy() if headers else {}

    if use_auth and auth_headers:
        request_headers.update(auth_headers)

    if files:
        # Remove Content-Type for file uploads
        request_headers.pop("Content-Type", None)

    start_time = time.time()

    try:
        print(f"📤 {method} {endpoint} (timeout: {timeout}s)")

        if method.upper() == "GET":
            response = requests.get(url, headers=request_headers, timeout=timeout)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, files=files, data=data, headers=request_headers, timeout=timeout)
            else:
                response = requests.post(url, json=data, headers=request_headers, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=request_headers, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=request_headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        duration = time.time() - start_time

        # Log processing delays for requests that take longer than expected
        if duration > 5.0:
            log_processing_delay(endpoint, duration)

        return response

    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        log_timeout(endpoint, duration)
        print(f"❌ Request timeout after {duration:.2f}s: {method} {endpoint}")
        return None

    except requests.exceptions.ConnectionError as e:
        log_error(endpoint, "Connection Error", str(e))
        print(f"❌ Connection error: {e}")
        return None

    except requests.exceptions.RequestException as e:
        log_error(endpoint, "Request Exception", str(e))
        print(f"❌ Request failed: {e}")
        return None

    except Exception as e:
        log_error(endpoint, "Unexpected Error", f"{type(e).__name__}: {e}")
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return None

def wait_for_processing(application_id: str, max_wait: int = PROCESSING_TIMEOUT) -> bool:
    """Wait for background processing to complete with timeout"""
    print(f"⏳ Waiting for processing to complete (max {max_wait}s)...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = make_request("GET", f"/workflow/status/{application_id}", use_auth=True, timeout=10)

        if not response:
            time.sleep(5)
            continue

        if response.status_code == 200:
            try:
                status_data = response.json()
                current_state = status_data.get("current_state", "unknown")
                progress = status_data.get("progress", 0)

                print(f"📊 Status: {current_state} ({progress}%)")

                # Check if processing is complete
                final_states = ["approved", "rejected", "needs_review", "decision_completed", "analysis_completed"]
                if any(state in current_state.lower() for state in final_states) or progress >= 100:
                    print(f"✅ Processing completed: {current_state}")
                    return True

                # Check if processing has stalled
                if current_state in ["failed", "error"]:
                    print(f"❌ Processing failed: {current_state}")
                    log_error(f"/workflow/status/{application_id}", "Processing Failed", current_state)
                    return False

            except Exception as e:
                log_error(f"/workflow/status/{application_id}", "Status Check Error", str(e))

        # Wait before checking again
        time.sleep(5)

    # Processing timed out
    duration = time.time() - start_time
    log_timeout(f"/workflow/status/{application_id}", duration)
    print(f"⏰ Processing timeout after {duration:.2f}s")
    return False

def test_endpoint_with_retry(method: str, endpoint: str, data: Optional[Dict] = None,
                           files: Optional[Dict] = None, use_auth: bool = False,
                           max_retries: int = 2) -> Optional[requests.Response]:
    """Test endpoint with retry logic for transient failures"""
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"🔄 Retry attempt {attempt}/{max_retries}")
            time.sleep(2)  # Brief delay before retry

        response = make_request(method, endpoint, data, files, use_auth=use_auth)

        if response is not None:
            if response.status_code < 500:  # Don't retry for client errors
                return response
            else:
                log_error(endpoint, f"Server Error (attempt {attempt + 1})", f"HTTP {response.status_code}")

        if attempt == max_retries:
            log_error(endpoint, "Max Retries Exceeded", f"Failed after {max_retries + 1} attempts")

    return None

def run_comprehensive_tests():
    """Run comprehensive API tests with enhanced error detection"""
    print("🚀 Starting Enhanced API Testing with Error Detection")
    print("=" * 80)

    global auth_token, auth_headers, test_user_data, application_data, document_data, session_data

    # Generate unique test user data
    timestamp = int(time.time())
    test_user_data = {
        "username": f"testuser_{timestamp}",
        "email": f"testuser_{timestamp}@example.com",
        "password": "testpassword123",
        "full_name": f"Test User {timestamp}"
    }

    print(f"📝 Generated test user data: {test_user_data['username']}")

    # Test 1: System Health Checks
    print("\n🏥 Testing System Health...")

    response = test_endpoint_with_retry("GET", "/")
    if response:
        print_response("Root API Information", response)

    response = test_endpoint_with_retry("GET", "/health/basic")
    if response:
        print_response("Basic Health Check", response)

    response = test_endpoint_with_retry("GET", "/health/database")
    if response:
        print_response("Database Health Check", response)

    response = test_endpoint_with_retry("GET", "/health/")
    if response:
        print_response("Comprehensive Health Check", response)

    # Test 2: Authentication Flow
    print("\n🔐 Testing Authentication Flow...")

    # User Registration
    response = test_endpoint_with_retry("POST", "/auth/register", data=test_user_data)
    if response:
        print_response("User Registration", response)
        if response.status_code == 201:
            user_data = response.json()
            test_user_data.update(user_data)
        else:
            print("⚠️ Registration failed, trying to login with existing user")

    # User Login
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }

    response = test_endpoint_with_retry("POST", "/auth/login", data=login_data)
    if response:
        print_response("User Login", response)
        if response.status_code == 200:
            auth_data = response.json()
            auth_token = auth_data.get("access_token")
            if auth_token:
                auth_headers = {"Authorization": f"Bearer {auth_token}"}
                print(f"✅ Authentication successful. Token: {auth_token[:20]}...")
            else:
                log_error("/auth/login", "No access token in response", str(auth_data))
        else:
            log_error("/auth/login", "Login failed", f"Status: {response.status_code}")

    if not auth_token:
        print("❌ Cannot proceed without authentication token")
        return

    # Test protected endpoints
    response = test_endpoint_with_retry("GET", "/auth/me", use_auth=True)
    if response:
        print_response("Current User Info", response)

    # Test 3: Document Upload with Error Detection
    print("\n📄 Testing Document Management...")

    response = test_endpoint_with_retry("GET", "/documents/types")
    if response:
        print_response("Supported Document Types", response)

    # Create sample documents
    def create_sample_files():
        """Create sample files for testing"""
        try:
            # Create a simple PDF
            sample_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n100 700 Td\n(Sample Bank Statement) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000268 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n363\n%%EOF"

            with open("sample_bank_statement.pdf", "wb") as f:
                f.write(sample_pdf_content)

            # Create a simple PNG
            sample_png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'

            with open("sample_emirates_id.png", "wb") as f:
                f.write(sample_png_content)

            print("✅ Created sample documents for testing")
            return True

        except Exception as e:
            log_error("file_creation", "File Creation Error", str(e))
            return False

    if create_sample_files():
        # Upload Documents
        try:
            files = {
                'bank_statement': ('sample_bank_statement.pdf', open('sample_bank_statement.pdf', 'rb'), 'application/pdf'),
                'emirates_id': ('sample_emirates_id.png', open('sample_emirates_id.png', 'rb'), 'image/png')
            }

            response = test_endpoint_with_retry("POST", "/documents/upload", files=files, use_auth=True)

            # Close file handles
            for file_obj in files.values():
                file_obj[1].close()

            if response:
                print_response("Document Upload", response)
                if response.status_code in [200, 201, 202]:
                    upload_data = response.json()
                    document_data.update(upload_data)

        except Exception as e:
            log_error("/documents/upload", "File Upload Error", str(e))

    # Test 4: Application Workflow with Extended Timeouts
    print("\n🔄 Testing Application Workflow...")

    # Start New Application
    application_form_data = {
        "full_name": "Ahmed Test User",
        "emirates_id": "784-1990-1234567-8",
        "phone": "+971501234567",
        "email": f"ahmed.test.{timestamp}@example.com"
    }

    response = test_endpoint_with_retry("POST", "/workflow/start-application",
                                      data=application_form_data, use_auth=True)
    if response:
        print_response("Start Application Workflow", response)
        if response.status_code in [200, 201]:
            app_data = response.json()
            application_data.update(app_data)
            application_id = app_data.get("application_id")

            # Upload documents to application if we have an ID
            if application_id and os.path.exists("sample_bank_statement.pdf"):
                try:
                    files = {
                        'bank_statement': ('sample_bank_statement.pdf', open('sample_bank_statement.pdf', 'rb'), 'application/pdf'),
                        'emirates_id': ('sample_emirates_id.png', open('sample_emirates_id.png', 'rb'), 'image/png')
                    }

                    response = test_endpoint_with_retry("POST", f"/workflow/upload-documents/{application_id}",
                                                      files=files, use_auth=True)

                    # Close file handles
                    for file_obj in files.values():
                        file_obj[1].close()

                    if response:
                        print_response("Upload Documents to Application", response)

                        # Start processing
                        process_data = {"force_retry": False}
                        response = test_endpoint_with_retry("POST", f"/workflow/process/{application_id}",
                                                          data=process_data, use_auth=True)
                        if response:
                            print_response("Process Application", response)

                            # Wait for processing to complete
                            if wait_for_processing(application_id):
                                # Get final results
                                response = test_endpoint_with_retry("GET", f"/applications/{application_id}/results",
                                                                   use_auth=True)
                                if response:
                                    print_response("Application Results", response)

                except Exception as e:
                    log_error(f"/workflow/upload-documents/{application_id}", "Document Upload Error", str(e))

    # Test 5: AI Services with Timeout Detection
    print("\n🤖 Testing AI Services...")

    # OCR Health Check
    response = test_endpoint_with_retry("GET", "/ocr/health")
    if response:
        print_response("OCR Health Check", response)

    # Decision Health Check
    response = test_endpoint_with_retry("GET", "/decisions/health")
    if response:
        print_response("Decision Health Check", response)

    # Chatbot Health Check
    response = test_endpoint_with_retry("GET", "/chatbot/health")
    if response:
        print_response("Chatbot Health Check", response)

    # Test AI endpoints with longer timeouts
    if application_data.get("application_id"):
        decision_data = {
            "application_id": application_data["application_id"],
            "factors": {
                "income": 8500,
                "balance": 15000,
                "employment_status": "employed"
            }
        }

        response = make_request("POST", "/decisions/make-decision",
                              data=decision_data, use_auth=True, timeout=60)  # Longer timeout for AI
        if response:
            print_response("Make Decision", response)

    # Test 6: Error Scenarios
    print("\n⚠️ Testing Error Scenarios...")

    # Test with invalid data
    response = test_endpoint_with_retry("POST", "/auth/login", data={"username": "invalid", "password": "invalid"})
    if response:
        print_response("Invalid Login Test", response)

    # Test with missing authentication
    response = test_endpoint_with_retry("GET", "/auth/me", use_auth=False)
    if response:
        print_response("Unauthorized Access Test", response)

    # Cleanup
    print("\n🧹 Cleanup...")
    try:
        if os.path.exists("sample_bank_statement.pdf"):
            os.remove("sample_bank_statement.pdf")
        if os.path.exists("sample_emirates_id.png"):
            os.remove("sample_emirates_id.png")
        print("✅ Cleaned up sample files")
    except Exception as e:
        log_error("cleanup", "Cleanup Error", str(e))

def print_summary():
    """Print comprehensive test summary"""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("="*80)

    print(f"🔥 Errors Encountered: {len(errors_encountered)}")
    if errors_encountered:
        print("\n❌ ERROR DETAILS:")
        for error in errors_encountered[-10:]:  # Show last 10 errors
            print(f"  • {error['endpoint']}: {error['error']}")
            if error['details']:
                print(f"    Details: {error['details'][:100]}...")

    print(f"\n⏰ Timeouts Encountered: {len(timeouts_encountered)}")
    if timeouts_encountered:
        print("\n⏰ TIMEOUT DETAILS:")
        for timeout in timeouts_encountered:
            print(f"  • {timeout['endpoint']}: {timeout['duration']:.2f}s")

    print(f"\n⏳ Processing Delays: {len(processing_delays)}")
    if processing_delays:
        print("\n⏳ DELAY DETAILS:")
        for delay in processing_delays:
            print(f"  • {delay['endpoint']}: {delay['duration']:.2f}s")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if len(timeouts_encountered) > 0:
        print("  • Consider increasing timeout values for slow endpoints")
    if len(processing_delays) > 5:
        print("  • Background processing may need optimization")
    if any("qdrant" in error['details'].lower() for error in errors_encountered):
        print("  • Qdrant vector database appears to be unavailable (optional service)")
    if any("llm" in error['details'].lower() or "model" in error['details'].lower() for error in errors_encountered):
        print("  • AI model services may need attention")

    print(f"\n🎯 OVERALL STATUS:")
    if len(errors_encountered) == 0 and len(timeouts_encountered) == 0:
        print("  ✅ ALL TESTS PASSED - System is functioning perfectly")
    elif len(errors_encountered) < 5 and len(timeouts_encountered) < 3:
        print("  ⚠️  MINOR ISSUES - System is mostly functional with some areas for improvement")
    else:
        print("  ❌ SIGNIFICANT ISSUES - System needs attention before production use")

if __name__ == "__main__":
    try:
        run_comprehensive_tests()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        traceback.print_exc()
    finally:
        print_summary()