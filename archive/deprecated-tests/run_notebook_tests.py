#!/usr/bin/env python3
"""
AI Social Security System - Complete API Testing Script
Automated execution of all notebook tests with detailed output
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Test data storage
test_results = {
    'auth': {},
    'health': {},
    'workflow': {},
    'documents': {},
    'ocr': {},
    'analysis': {},
    'decisions': {},
    'users': {},
    'applications': {},
    'chatbot': {},
    'admin': {}
}

# Global variables for test flow
global_auth = {
    'token': None,
    'user_id': None,
    'headers': {},
    'user_info': {}
}

global_data = {
    'application_id': None,
    'document_ids': [],
    'decision_id': None,
    'session_id': None
}

def make_request(method: str, endpoint: str, data: Dict = None, files: Dict = None,
                use_auth: bool = True, custom_headers: Dict = None) -> Dict:
    """Make HTTP request with proper error handling"""

    # Prepare headers
    headers = custom_headers or {}
    if use_auth and global_auth['token']:
        headers.update(global_auth['headers'])

    # If files are provided, don't set Content-Type (let requests handle it)
    if not files and 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'

    url = f"{BASE_URL}{endpoint}"

    try:
        start_time = time.time()

        print(f"\n🌐 {method.upper()} {url}")
        if data and not files:
            print(f"📤 Request Data: {json.dumps(data, indent=2)}")
        elif files:
            print(f"📤 Files: {list(files.keys())}")
            if data:
                print(f"📤 Form Data: {data}")

        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method.upper() == 'POST':
            if files:
                # For file uploads, don't include Content-Type in headers
                auth_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
                response = requests.post(url, data=data, files=files, headers=auth_headers, timeout=TIMEOUT)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=TIMEOUT)
        else:
            raise ValueError(f"Unsupported method: {method}")

        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)  # ms

        # Parse response
        try:
            response_json = response.json()
        except:
            response_json = {"text": response.text[:500]}

        # Print response
        print(f"📥 Response ({response.status_code}): {json.dumps(response_json, indent=2)}")
        print(f"⏱️ Response Time: {response_time}ms")

        return {
            'success': response.status_code < 400,
            'status_code': response.status_code,
            'response': response_json,
            'response_time': response_time,
            'url': url,
            'method': method.upper()
        }

    except requests.exceptions.Timeout:
        print(f"❌ Request timeout after {TIMEOUT}s")
        return {
            'success': False,
            'status_code': 0,
            'response': {'error': 'Request timeout'},
            'response_time': TIMEOUT * 1000,
            'url': url,
            'method': method.upper()
        }
    except Exception as e:
        print(f"❌ Request error: {str(e)}")
        return {
            'success': False,
            'status_code': 0,
            'response': {'error': str(e)},
            'response_time': 0,
            'url': url,
            'method': method.upper()
        }

def log_test_result(module: str, test_name: str, result: Dict):
    """Log test result with formatting"""
    status_icon = "✅" if result['success'] else "❌"
    print(f"\n{status_icon} {test_name}: {result['status_code']} ({result['response_time']}ms)")

    if not result['success']:
        print(f"   Error: {result['response']}")

    # Store result
    test_results[module][test_name] = result
    return result

def create_test_user():
    """Create a unique test user for this session"""
    timestamp = int(time.time())
    return {
        'username': f'test_user_{timestamp}',
        'email': f'test_{timestamp}@example.com',
        'password': 'TestPass123!',
        'full_name': 'Test User',
        'phone': '+971501234567',
        'emirates_id': '784-1995-1234567-8'
    }

def test_health_module():
    """Test all health-related endpoints"""
    print("\n🏥 TESTING HEALTH MODULE")
    print("-" * 40)

    health_endpoints = [
        ("/", "Root Endpoint"),
        ("/health/", "Basic Health Check"),
        ("/health/basic", "Basic Health Alternative"),
        ("/health/database", "Database Health"),
    ]

    for endpoint, name in health_endpoints:
        result = make_request('GET', endpoint, use_auth=False)
        log_test_result('health', name, result)

    # Test OpenAPI spec
    result = make_request('GET', '/openapi.json', use_auth=False)
    log_test_result('health', 'OpenAPI Spec', result)

    if result['success']:
        spec = result['response']
        endpoints_count = len(spec.get('paths', {}))
        print(f"   📊 API Spec: {endpoints_count} endpoints discovered")

    return test_results['health']

def test_auth_module():
    """Test all authentication endpoints and establish session"""
    print("\n🔐 TESTING AUTHENTICATION MODULE")
    print("-" * 40)

    # Create test user
    test_user = create_test_user()
    print(f"👤 Creating user: {test_user['username']}")

    # Test 1: User Registration
    result = make_request('POST', '/auth/register', data=test_user, use_auth=False)
    log_test_result('auth', 'User Registration', result)

    # Handle existing user case
    if not result['success'] and 'USERNAME_EXISTS' in str(result['response']):
        print("   ℹ️ User exists, proceeding with login")
        test_user['username'] = 'muaazbinsaeed'  # Use existing user

    # Test 2: User Login
    login_data = {
        'username': test_user['username'],
        'password': test_user['password']
    }

    result = make_request('POST', '/auth/login', data=login_data, use_auth=False)
    log_test_result('auth', 'User Login', result)

    if result['success']:
        auth_data = result['response']
        global_auth['token'] = auth_data.get('access_token')
        global_auth['user_info'] = auth_data.get('user_info', {})
        global_auth['user_id'] = global_auth['user_info'].get('id')
        global_auth['headers'] = {
            'Authorization': f'Bearer {global_auth["token"]}',
            'Content-Type': 'application/json'
        }
        print(f"   🎫 Token obtained: {global_auth['token'][:50]}...")
        print(f"   👤 User ID: {global_auth['user_id']}")
    else:
        print("   ❌ Login failed - cannot proceed with authenticated tests")
        return test_results['auth']

    # Test 3: Get Current User
    result = make_request('GET', '/auth/me')
    log_test_result('auth', 'Get Current User', result)

    # Test 4: Refresh Token
    result = make_request('POST', '/auth/refresh')
    log_test_result('auth', 'Refresh Token', result)

    # Test 5: Auth Status
    result = make_request('GET', '/auth/status')
    log_test_result('auth', 'Auth Status', result)

    # Test 6: Unauthorized access (negative test)
    result = make_request('GET', '/auth/me', use_auth=False)
    expected_fail = not result['success']
    result['success'] = expected_fail  # Invert for negative test
    log_test_result('auth', 'Unauthorized Access (Expected Fail)', result)

    return test_results['auth']

def test_workflow_module():
    """Test workflow endpoints"""
    print("\n🔄 TESTING WORKFLOW MODULE")
    print("-" * 40)

    if not global_auth['token']:
        print("❌ No authentication token - skipping workflow tests")
        return

    # Test 1: Create Application via Workflow
    app_data = {
        'full_name': global_auth['user_info'].get('full_name', 'Test User'),
        'emirates_id': '784-1995-1234567-8',
        'phone': '+971501234567',
        'email': global_auth['user_info'].get('email', 'test@example.com')
    }

    result = make_request('POST', '/workflow/start-application', data=app_data)
    log_test_result('workflow', 'Create Application', result)

    if result['success']:
        global_data['application_id'] = result['response'].get('application_id')
    elif 'APPLICATION_EXISTS' in str(result['response']):
        existing_id = result['response'].get('detail', {}).get('existing_application_id')
        if existing_id:
            global_data['application_id'] = existing_id
            print(f"   📱 Using existing application: {existing_id}")

    if not global_data['application_id']:
        print("❌ No application ID - skipping workflow tests")
        return

    app_id = global_data['application_id']

    # Test 2: Get Workflow Status
    result = make_request('GET', f'/workflow/status/{app_id}')
    log_test_result('workflow', 'Get Workflow Status', result)

    if result['success']:
        status_data = result['response']
        current_state = status_data.get('current_state')
        progress = status_data.get('progress', 0)
        print(f"   📊 Current State: {current_state} ({progress}%)")

    # Test 3: Upload Documents (if in correct state)
    emirates_id_path = 'docs/EmirateIDFront.jpg'
    bank_statement_path = 'docs/Bank Muaaz Alfalah Statement.pdf'

    if os.path.exists(emirates_id_path) and os.path.exists(bank_statement_path):
        print(f"   📄 Uploading documents: {emirates_id_path}, {bank_statement_path}")

        with open(emirates_id_path, 'rb') as eid_file, open(bank_statement_path, 'rb') as bank_file:
            files = {
                'emirates_id': ('EmirateIDFront.jpg', eid_file, 'image/jpeg'),
                'bank_statement': ('Bank_Statement.pdf', bank_file, 'application/pdf')
            }

            result = make_request('POST', f'/workflow/upload-documents/{app_id}', files=files)
            log_test_result('workflow', 'Upload Documents', result)

            if result['success']:
                doc_ids = result['response'].get('document_ids', [])
                global_data['document_ids'] = doc_ids
                print(f"   📄 Documents uploaded: {doc_ids}")
    else:
        print(f"   ⚠️ Test documents not found: {emirates_id_path}, {bank_statement_path}")

    # Test 4: Start Processing
    result = make_request('POST', f'/workflow/process/{app_id}')
    log_test_result('workflow', 'Start Processing', result)

    if result['success']:
        job_id = result['response'].get('processing_job_id')
        print(f"   ⚙️ Processing started with job ID: {job_id}")

    # Test 5: Check Status Again
    time.sleep(2)  # Wait a bit for processing to start
    result = make_request('GET', f'/workflow/status/{app_id}')
    log_test_result('workflow', 'Check Updated Status', result)

    # Test 6: Get Results
    result = make_request('GET', f'/workflow/results/{app_id}')
    log_test_result('workflow', 'Get Results', result)

    return test_results['workflow']

def main():
    """Main testing function"""
    print("🚀 AI Social Security System - Complete API Testing")
    print("=" * 70)
    print(f"📅 Started: {datetime.now()}")
    print(f"🌐 Base URL: {BASE_URL}")
    print("=" * 70)

    try:
        # Test modules in order
        print("\n🏃‍♂️ Starting comprehensive API testing...")

        # 1. Health checks first
        health_results = test_health_module()

        # 2. Authentication (required for other tests)
        auth_results = test_auth_module()

        # 3. Workflow (core functionality)
        if global_auth['token']:
            workflow_results = test_workflow_module()

        # Summary
        print("\n📊 TESTING SUMMARY")
        print("=" * 50)

        total_tests = 0
        passed_tests = 0

        for module_name, module_results in test_results.items():
            if not module_results:
                continue

            module_total = len(module_results)
            module_passed = sum(1 for result in module_results.values() if result.get('success', False))

            total_tests += module_total
            passed_tests += module_passed

            success_rate = (module_passed / module_total * 100) if module_total > 0 else 0
            status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"

            print(f"{status_icon} {module_name.upper()}: {module_passed}/{module_total} ({success_rate:.1f}%)")

        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 OVERALL: {passed_tests}/{total_tests} ({overall_success_rate:.1f}%)")

        if overall_success_rate >= 80:
            print(f"🎉 EXCELLENT: System is working well!")
        elif overall_success_rate >= 60:
            print(f"✅ GOOD: Minor issues to address")
        else:
            print(f"⚠️ NEEDS ATTENTION: Multiple issues found")

        print("\n" + "=" * 70)
        print("✅ API Testing Completed")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")

if __name__ == "__main__":
    main()