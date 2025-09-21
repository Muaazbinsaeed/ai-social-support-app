#!/usr/bin/env python3
"""
End-to-end workflow demonstration test
Tests the complete application flow from user registration to decision making
"""

import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 10

def test_complete_workflow():
    """Test the complete social security application workflow"""
    print("🚀 Starting End-to-End Workflow Demonstration")
    print("=" * 60)

    session = requests.Session()

    # Step 1: User Authentication
    print("\n📋 Step 1: User Authentication")
    print("-" * 30)

    # Login with test user
    login_data = {
        "username": "demo_user",
        "password": "demo123"
    }

    try:
        login_response = session.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )

        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            print(f"✅ Login successful")
            print(f"   Token: {access_token[:20]}...")

            # Set authorization header for all subsequent requests
            session.headers.update({"Authorization": f"Bearer {access_token}"})
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False

    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False

    # Step 2: Start Application Workflow
    print("\n📋 Step 2: Start Application Workflow")
    print("-" * 30)

    application_data = {
        "full_name": "Ahmed Al-Mansouri",
        "emirates_id": "784-1990-1234567-8",
        "phone": "+971501234567",
        "email": "ahmed@example.com"
    }

    try:
        app_response = session.post(
            f"{BASE_URL}/workflow/start-application",
            json=application_data,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )

        if app_response.status_code == 201:
            app_data = app_response.json()
            application_id = app_data.get("application_id")
            print(f"✅ Application created successfully")
            print(f"   Application ID: {application_id}")
            print(f"   Status: {app_data.get('status')}")
            print(f"   Progress: {app_data.get('progress')}%")
        else:
            print(f"❌ Application creation failed: {app_response.status_code}")
            print(f"   Response: {app_response.text}")
            return False

    except Exception as e:
        print(f"❌ Application creation error: {str(e)}")
        return False

    # Step 3: Upload Documents
    print("\n📋 Step 3: Upload Documents")
    print("-" * 30)

    # Upload bank statement
    try:
        bank_statement_path = "uploads/test_data/sample_bank_statement.pdf"
        if Path(bank_statement_path).exists():
            with open(bank_statement_path, 'rb') as bank_file:
                files = {
                    'bank_statement': ('sample_bank_statement.pdf', bank_file, 'application/pdf')
                }

                upload_response = session.post(
                    f"{BASE_URL}/documents/upload",
                    files=files,
                    timeout=TEST_TIMEOUT
                )

                if upload_response.status_code == 201:
                    upload_data = upload_response.json()
                    print(f"✅ Bank statement uploaded successfully")
                    print(f"   Document ID: {upload_data.get('bank_statement', {}).get('document_id')}")
                else:
                    print(f"❌ Document upload failed: {upload_response.status_code}")
                    print(f"   Response: {upload_response.text}")
        else:
            print(f"❌ Test bank statement not found at {bank_statement_path}")

    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")

    # Upload Emirates ID
    try:
        emirates_id_path = "uploads/test_data/sample_emirates_id.jpg"
        if Path(emirates_id_path).exists():
            with open(emirates_id_path, 'rb') as id_file:
                files = {
                    'emirates_id': ('sample_emirates_id.jpg', id_file, 'image/jpeg')
                }

                upload_response = session.post(
                    f"{BASE_URL}/documents/upload",
                    files=files,
                    timeout=TEST_TIMEOUT
                )

                if upload_response.status_code == 201:
                    upload_data = upload_response.json()
                    print(f"✅ Emirates ID uploaded successfully")
                    print(f"   Document ID: {upload_data.get('emirates_id', {}).get('document_id')}")
                else:
                    print(f"❌ Emirates ID upload failed: {upload_response.status_code}")
                    print(f"   Response: {upload_response.text}")
        else:
            print(f"❌ Test Emirates ID not found at {emirates_id_path}")

    except Exception as e:
        print(f"❌ Emirates ID upload error: {str(e)}")

    # Step 4: Start Processing
    print("\n📋 Step 4: Start Processing Workflow")
    print("-" * 30)

    try:
        process_response = session.post(
            f"{BASE_URL}/workflow/process/{application_id}",
            json={"force_retry": False},
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )

        if process_response.status_code == 202:
            process_data = process_response.json()
            print(f"✅ Processing started successfully")
            print(f"   Status: {process_data.get('status')}")
            print(f"   Message: {process_data.get('message')}")
            print(f"   Estimated completion: {process_data.get('estimated_completion')}")
        else:
            print(f"❌ Processing start failed: {process_response.status_code}")
            print(f"   Response: {process_response.text}")

    except Exception as e:
        print(f"❌ Processing start error: {str(e)}")

    # Step 5: Monitor Progress
    print("\n📋 Step 5: Monitor Processing Progress")
    print("-" * 30)

    max_attempts = 12  # 2 minutes max
    attempt = 0

    while attempt < max_attempts:
        try:
            status_response = session.get(
                f"{BASE_URL}/workflow/status/{application_id}",
                timeout=TEST_TIMEOUT
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                current_state = status_data.get('current_state')
                progress = status_data.get('progress')
                processing_time = status_data.get('processing_time_elapsed')

                print(f"   📊 Progress: {progress}% | State: {current_state} | Time: {processing_time}s")

                # Show steps
                steps = status_data.get('steps', [])
                for step in steps[-3:]:  # Show last 3 steps
                    status_icon = "✅" if step.get('status') == 'completed' else "🔄" if step.get('status') == 'in_progress' else "⏳"
                    print(f"      {status_icon} {step.get('name')}: {step.get('message')}")

                # Check if completed
                if current_state in ['approved', 'rejected', 'needs_review']:
                    print(f"\n🎉 Processing completed!")
                    print(f"   Final Status: {current_state}")

                    # Show partial results if available
                    partial_results = status_data.get('partial_results', {})
                    if partial_results:
                        print(f"   📊 Results Summary:")
                        for key, value in partial_results.items():
                            print(f"      {key}: {value}")

                    break

            else:
                print(f"❌ Status check failed: {status_response.status_code}")

        except Exception as e:
            print(f"❌ Status check error: {str(e)}")

        attempt += 1
        time.sleep(10)  # Wait 10 seconds between checks

        if attempt >= max_attempts:
            print(f"\n⏰ Maximum monitoring time reached")
            print(f"   Processing may still be running in background")

    # Step 6: Check Final Results
    print("\n📋 Step 6: Final Results")
    print("-" * 30)

    try:
        final_response = session.get(
            f"{BASE_URL}/applications/{application_id}",
            timeout=TEST_TIMEOUT
        )

        if final_response.status_code == 200:
            final_data = final_response.json()
            print(f"✅ Final application status retrieved")
            print(f"   Decision: {final_data.get('decision', 'Pending')}")
            print(f"   Progress: {final_data.get('progress')}%")
            print(f"   Monthly Income: AED {final_data.get('monthly_income', 'N/A')}")
            print(f"   Account Balance: AED {final_data.get('account_balance', 'N/A')}")
        else:
            print(f"❌ Final results fetch failed: {final_response.status_code}")

    except Exception as e:
        print(f"❌ Final results error: {str(e)}")

    print("\n" + "=" * 60)
    print("🏁 END-TO-END WORKFLOW DEMONSTRATION COMPLETE")
    print("=" * 60)

    return True

if __name__ == "__main__":
    test_complete_workflow()