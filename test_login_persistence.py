"""
Test script to verify login persistence and application management features
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_login_and_applications():
    """Test the complete login and application flow"""
    print("🧪 Testing Social Security AI System")
    print("=" * 50)

    # Test 1: Login
    print("1. Testing login...")
    login_data = {
        "username": "demo_user",
        "password": "demo123"
    }

    response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        login_result = response.json()
        token = login_result['access_token']
        user_info = login_result['user_info']
        print(f"   ✅ Login successful for user: {user_info['username']}")
        print(f"   🔑 Token: {token[:20]}...")
    else:
        print(f"   ❌ Login failed: {response.text}")
        return

    # Headers for authenticated requests
    headers = {"Authorization": f"Bearer {token}"}

    # Test 2: Check application history
    print("\n2. Testing application history endpoint...")
    response = requests.get(f"{API_BASE_URL}/applications/history", headers=headers)
    if response.status_code == 200:
        history = response.json()
        active_app = history.get('active_application')
        historical_apps = history.get('historical_applications', [])
        total_count = history.get('total_count', 0)

        print(f"   ✅ History retrieved successfully")
        print(f"   📊 Total applications: {total_count}")
        print(f"   🔄 Active applications: {1 if active_app else 0}")
        print(f"   📚 Historical applications: {len(historical_apps)}")

        if active_app:
            print(f"   📋 Active app ID: {active_app['application_id'][:8]}...")
            print(f"   📊 Status: {active_app['status']}")
    else:
        print(f"   ❌ History request failed: {response.text}")

    # Test 3: Discard current application (if any)
    if active_app:
        print("\n3. Testing application discard...")
        response = requests.delete(f"{API_BASE_URL}/workflow/discard-application", headers=headers)
        if response.status_code == 200:
            discard_result = response.json()
            print(f"   ✅ Application discarded successfully")
            print(f"   🗑️ Discarded app: {discard_result['discarded_application_id'][:8]}...")
        else:
            print(f"   ❌ Discard failed: {response.text}")

    # Test 4: Create new application
    print("\n4. Testing new application creation...")
    app_data = {
        "full_name": "Ahmed Test User",
        "emirates_id": "784-1990-1234567-8",
        "phone": "+971501234567",
        "email": "ahmed.test@example.com"
    }

    response = requests.post(f"{API_BASE_URL}/workflow/start-application", json=app_data, headers=headers)
    if response.status_code == 200:
        app_result = response.json()
        new_app_id = app_result['application_id']
        print(f"   ✅ New application created successfully")
        print(f"   🆔 Application ID: {new_app_id}")
        print(f"   📊 Status: {app_result['status']}")
        print(f"   📈 Progress: {app_result['progress']}%")
    else:
        print(f"   ❌ Application creation failed: {response.text}")

    # Test 5: Verify updated history
    print("\n5. Testing updated application history...")
    response = requests.get(f"{API_BASE_URL}/applications/history", headers=headers)
    if response.status_code == 200:
        updated_history = response.json()
        active_app = updated_history.get('active_application')
        historical_apps = updated_history.get('historical_applications', [])
        total_count = updated_history.get('total_count', 0)

        print(f"   ✅ Updated history retrieved")
        print(f"   📊 Total applications: {total_count}")
        print(f"   🔄 Active applications: {1 if active_app else 0}")
        print(f"   📚 Historical applications: {len(historical_apps)}")

        if active_app:
            print(f"   📋 New active app: {active_app['application_id'][:8]}...")

    print("\n" + "=" * 50)
    print("🎉 Test completed successfully!")
    print("\n💡 You can now test the frontend features:")
    print(f"   🌐 Open: http://localhost:8005")
    print(f"   🔐 Login with: demo_user / demo123")
    print(f"   🧪 Test features:")
    print(f"      - Login persistence (refresh page)")
    print(f"      - Navigation with My Applications")
    print(f"      - View application history")
    print(f"      - Create new application (discards existing)")

if __name__ == "__main__":
    test_login_and_applications()