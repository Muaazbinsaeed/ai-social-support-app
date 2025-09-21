#!/usr/bin/env python3
"""
Test script to validate the complete frontend flow
"""

import httpx
import json

API_BASE_URL = "http://localhost:8000"

def test_complete_flow():
    """Test the complete frontend flow with existing application"""
    print("🔍 Testing complete frontend flow...")

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # 1. Login
        print("\n1. Testing login...")
        login_data = {
            "username": "demo_user",
            "password": "demo123"
        }

        response = client.post(f"{API_BASE_URL}/auth/login", json=login_data)
        print(f"Login Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            print(f"✅ Login successful! Token: {access_token[:30]}...")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 2. Check for existing applications
            print("\n2. Checking for existing applications...")
            response = client.get(f"{API_BASE_URL}/applications/", headers=headers)
            print(f"Get Applications Status: {response.status_code}")

            if response.status_code == 200:
                apps_result = response.json()
                applications = apps_result.get('applications', [])
                print(f"Found {len(applications)} applications")

                # Find active application
                active_app = None
                for app in applications:
                    status = app.get('status')
                    app_id = app.get('id') or 'unknown'
                    app_id_short = app_id[:8] if app_id != 'unknown' else 'unknown'
                    print(f"  - App {app_id_short}... Status: {status}")
                    if status in ['draft', 'form_submitted', 'documents_uploaded', 'scanning_documents',
                                'ocr_completed', 'analyzing_income', 'analyzing_identity',
                                'analysis_completed', 'making_decision']:
                        active_app = app
                        break

                if active_app:
                    print(f"✅ Found active application!")
                    print(f"   Full app data: {active_app}")
                    app_id = active_app.get('id') or active_app.get('application_id')
                    if app_id:
                        print(f"   ID: {app_id}")
                    print(f"   Status: {active_app.get('status')}")
                    print(f"   Created: {active_app.get('created_at')}")

                    # 3. Test document upload for existing application
                    print(f"\n3. Testing document management for existing app...")

                    # Create a dummy PDF file content
                    dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"

                    files = {"file": ("test_bank_statement.pdf", dummy_pdf, "application/pdf")}
                    data = {
                        "document_type": "bank_statement",
                        "application_id": active_app['id']
                    }

                    response = client.post(
                        f"{API_BASE_URL}/document-management/",
                        files=files,
                        data=data,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )

                    print(f"Document Upload Status: {response.status_code}")
                    if response.status_code == 201:
                        print("✅ Document upload successful!")
                    else:
                        print(f"❌ Document upload failed: {response.text}")
                else:
                    print("ℹ️ No active applications found")
            else:
                print(f"❌ Failed to get applications: {response.text}")

        else:
            print(f"❌ Login failed: {response.text}")

if __name__ == "__main__":
    test_complete_flow()