#!/usr/bin/env python3
"""
Test script to verify the document persistence and processing status fixes
"""

import httpx
import json

BASE_URL = "http://localhost:8000"

def test_fixes():
    """Test the fixes for document persistence and processing status"""
    
    print("🧪 Testing Document Persistence and Processing Status Fixes")
    print("=" * 60)
    
    # Login
    print("🔐 1. Logging in...")
    login_response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"username": "testuser", "password": "Test123!@#"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Test processing status with no application (should return 404 gracefully)
    print("\n📊 2. Testing processing status with no application...")
    status_response = httpx.get(
        f"{BASE_URL}/workflow/processing-status/00000000-0000-0000-0000-000000000000",
        headers=headers
    )
    
    print(f"Status code: {status_response.status_code}")
    if status_response.status_code == 404:
        response_data = status_response.json()
        print(f"✅ 404 handled properly: {response_data.get('detail', {}).get('message', 'Not found')}")
    else:
        print(f"⚠️ Unexpected status code: {status_response.status_code}")
    
    # Test document status endpoint (should also return 404 gracefully)
    print("\n📄 3. Testing document status with no documents...")
    doc_status_response = httpx.get(
        f"{BASE_URL}/documents/application/00000000-0000-0000-0000-000000000000",
        headers=headers
    )
    
    print(f"Document status code: {doc_status_response.status_code}")
    if doc_status_response.status_code in [404, 200]:
        print("✅ Document status endpoint responding properly")
    else:
        print(f"⚠️ Unexpected document status code: {doc_status_response.status_code}")
    
    # Test download endpoint (should return 404)
    print("\n📥 4. Testing document download with invalid ID...")
    download_response = httpx.get(
        f"{BASE_URL}/documents/download/invalid-id",
        headers=headers
    )
    
    print(f"Download status code: {download_response.status_code}")
    if download_response.status_code == 404:
        print("✅ Download endpoint properly returns 404 for invalid documents")
    else:
        print(f"⚠️ Unexpected download status code: {download_response.status_code}")
    
    print("\n✅ All API endpoint tests completed!")
    print("\n📋 Frontend Test Instructions:")
    print("1. Go to http://localhost:8005")
    print("2. Login with username: testuser, password: Test123!@#")
    print("3. Check the 'Processing Status' tab - should show helpful message instead of error")
    print("4. Upload documents, submit them, then refresh the page")
    print("5. Documents should show 'Load Document' button instead of error message")
    
    return True

if __name__ == "__main__":
    try:
        test_fixes()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
