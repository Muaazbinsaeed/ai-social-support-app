#!/usr/bin/env python3
"""
Test script to validate the authentication flow
"""

import httpx
import json

API_BASE_URL = "http://localhost:8000"

def test_auth_flow():
    """Test the complete authentication flow"""
    print("🔍 Testing authentication flow...")

    # 1. Test login
    print("\n1. Testing login...")
    login_data = {
        "username": "demo_user",
        "password": "demo123"
    }

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Login
        response = client.post(
            f"{API_BASE_URL}/auth/login",
            json=login_data
        )

        print(f"Login Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            print(f"✅ Login successful! Token received: {access_token[:50]}...")

            # 2. Test authenticated endpoint
            print("\n2. Testing authenticated endpoint...")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # Test workflow/start-application endpoint
            app_data = {
                "full_name": "Test User",
                "emirates_id": "784-1990-1234567-8",
                "phone": "+971501234567",
                "email": "test@example.com"
            }

            response = client.post(
                f"{API_BASE_URL}/workflow/start-application",
                json=app_data,
                headers=headers
            )

            print(f"Application Creation Status: {response.status_code}")
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Application created! ID: {result.get('application_id')}")
            else:
                print(f"❌ Application creation failed:")
                print(f"Response: {response.text}")

        else:
            print(f"❌ Login failed:")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    test_auth_flow()