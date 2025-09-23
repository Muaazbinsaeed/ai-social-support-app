#!/usr/bin/env python3
"""
Manual API Testing Script for OCR and Document Processing
Comprehensive testing of all enhanced frontend API endpoints
"""

import requests
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:8005"
TEST_USER = {"username": "user1", "password": "password123"}

class APITester:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        print("🔐 Authenticating...")

        response = self.session.post(
            f"{API_BASE_URL}/auth/login",
            json=TEST_USER
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    def test_health_endpoints(self):
        """Test all health check endpoints"""
        print("\n🏥 Testing Health Endpoints")
        print("-" * 50)

        health_endpoints = [
            "/health",
            "/health/basic",
            "/health/database",
            "/ocr/health",
            "/analysis/health",
            "/decisions/health",
            "/chatbot/health"
        ]

        for endpoint in health_endpoints:
            try:
                response = self.session.get(f"{API_BASE_URL}{endpoint}", headers=self.headers)
                if response.status_code == 200:
                    print(f"✅ {endpoint}: {response.status_code}")
                    if "ocr" in endpoint:
                        # Show OCR health details
                        data = response.json()
                        print(f"   OCR Status: {data.get('status', 'unknown')}")
                else:
                    print(f"❌ {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint}: Error - {e}")

    def test_document_upload(self) -> Optional[str]:
        """Test document upload and return document ID"""
        print("\n📄 Testing Document Upload")
        print("-" * 50)

        # Find test documents
        test_files = [
            "docs/EmirateIDFront.jpg",
            "docs/BankStatement.pdf"
        ]

        uploaded_doc_id = None

        for file_path in test_files:
            if os.path.exists(file_path):
                print(f"📤 Uploading: {file_path}")

                with open(file_path, 'rb') as f:
                    files = {'file': (os.path.basename(file_path), f)}
                    data = {
                        'document_type': 'emirates_id' if 'Emirates' in file_path else 'bank_statement'
                    }

                    response = self.session.post(
                        f"{API_BASE_URL}/documents/upload",
                        headers=self.headers,
                        files=files,
                        data=data
                    )

                    if response.status_code in [200, 201]:
                        result = response.json()
                        doc_id = result.get('document_id')
                        print(f"✅ Upload successful: {doc_id}")
                        if uploaded_doc_id is None:
                            uploaded_doc_id = doc_id
                    else:
                        print(f"❌ Upload failed: {response.status_code}")
                        print(f"Response: {response.text}")
            else:
                print(f"⚠️ Test file not found: {file_path}")

        return uploaded_doc_id

    def test_ocr_endpoints(self, document_id: Optional[str] = None):
        """Test OCR processing endpoints"""
        print("\n🔍 Testing OCR Endpoints")
        print("-" * 50)

        # Test OCR health (already tested above but show details)
        response = self.session.get(f"{API_BASE_URL}/ocr/health", headers=self.headers)
        if response.status_code == 200:
            print("✅ OCR Health Check:")
            print(json.dumps(response.json(), indent=2))

        # Test direct OCR with file upload
        test_file = "docs/EmirateIDFront.jpg"
        if os.path.exists(test_file):
            print(f"\n📄 Testing Direct OCR: {test_file}")

            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f)}
                data = {'document_type': 'emirates_id'}

                response = self.session.post(
                    f"{API_BASE_URL}/ocr/upload-and-extract",
                    headers=self.headers,
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Direct OCR successful:")
                    print(f"   Extracted text length: {len(result.get('extracted_text', ''))}")
                    print(f"   Confidence: {result.get('confidence', 0):.1%}")

                    # Show sample text
                    sample_text = result.get('extracted_text', '')[:200]
                    if sample_text:
                        print(f"   Sample text: {sample_text}...")
                else:
                    print(f"❌ Direct OCR failed: {response.status_code}")
                    print(f"Response: {response.text}")

        # Test document OCR processing
        if document_id:
            print(f"\n🔄 Testing Document OCR Processing: {document_id}")

            response = self.session.post(
                f"{API_BASE_URL}/ocr/documents/{document_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                print("✅ Document OCR processing started")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"❌ Document OCR failed: {response.status_code}")
                print(f"Response: {response.text}")

    def test_analysis_endpoints(self, document_id: Optional[str] = None):
        """Test document analysis endpoints"""
        print("\n🔬 Testing Analysis Endpoints")
        print("-" * 50)

        if document_id:
            print(f"📊 Testing Document Analysis: {document_id}")

            response = self.session.post(
                f"{API_BASE_URL}/analysis/documents/{document_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                print("✅ Document analysis successful:")
                result = response.json()
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ Document analysis failed: {response.status_code}")
                print(f"Response: {response.text}")

        # Test upload and analyze
        test_file = "docs/BankStatement.pdf"
        if os.path.exists(test_file):
            print(f"\n📄 Testing Upload and Analyze: {test_file}")

            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f)}
                data = {'document_type': 'bank_statement'}

                response = self.session.post(
                    f"{API_BASE_URL}/analysis/upload-and-analyze",
                    headers=self.headers,
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Upload and analyze successful:")
                    print(f"   Analysis ID: {result.get('analysis_id')}")
                    print(f"   Status: {result.get('status')}")
                else:
                    print(f"❌ Upload and analyze failed: {response.status_code}")
                    print(f"Response: {response.text}")

    def test_workflow_endpoints(self):
        """Test workflow management endpoints"""
        print("\n🔄 Testing Workflow Endpoints")
        print("-" * 50)

        # Start application workflow
        print("🚀 Starting Application Workflow")

        application_data = {
            "personal_info": {
                "full_name": "Test User",
                "emirates_id": "123456789012345",
                "phone": "+971501234567",
                "email": "test@example.com"
            },
            "employment_info": {
                "employer_name": "Test Company",
                "position": "Software Engineer",
                "monthly_salary": 5000
            }
        }

        response = self.session.post(
            f"{API_BASE_URL}/workflow/start-application",
            headers=self.headers,
            json=application_data
        )

        if response.status_code in [200, 201, 409]:  # 409 = already exists
            if response.status_code == 409:
                print("⚠️ Application already exists, using existing one")
                existing_id = response.json().get('existing_application_id')
                app_id = existing_id
            else:
                result = response.json()
                app_id = result.get('application_id')
                print(f"✅ Application created: {app_id}")

            # Test workflow status
            if app_id:
                print(f"\n📊 Testing Workflow Status: {app_id}")

                response = self.session.get(
                    f"{API_BASE_URL}/workflow/status/{app_id}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    status = response.json()
                    print("✅ Workflow status retrieved:")
                    print(f"   Status: {status.get('overall_status')}")
                    print(f"   Progress: {status.get('progress', 0)}%")
                    print(f"   Documents: {len(status.get('documents', []))}")
                else:
                    print(f"❌ Workflow status failed: {response.status_code}")

                return app_id
        else:
            print(f"❌ Start application failed: {response.status_code}")
            print(f"Response: {response.text}")

        return None

    def test_processing_status(self, app_id: Optional[str] = None):
        """Test enhanced processing status endpoint"""
        print("\n📈 Testing Enhanced Processing Status")
        print("-" * 50)

        if app_id:
            # Test regular processing status
            print(f"📊 Regular Processing Status: {app_id}")
            response = self.session.get(
                f"{API_BASE_URL}/workflow/processing-status/{app_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                status = response.json()
                print("✅ Processing status retrieved:")
                print(f"   Overall Status: {status.get('overall_status')}")
                print(f"   Progress: {status.get('progress')}%")

                documents = status.get('documents', [])
                for doc in documents:
                    print(f"   Document: {doc.get('document_type')} - OCR: {doc.get('ocr_status')}")

            # Test enhanced processing status (if endpoint exists)
            print(f"\n🔍 Enhanced Processing Status: {app_id}")
            response = self.session.get(
                f"{API_BASE_URL}/workflow/enhanced-status/{app_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                print("✅ Enhanced status available")
                # Don't print full response as it might be large
            elif response.status_code == 404:
                print("ℹ️ Enhanced status endpoint not available")
            else:
                print(f"❌ Enhanced status failed: {response.status_code}")

    def test_frontend_connectivity(self):
        """Test frontend connectivity"""
        print(f"\n🌐 Testing Frontend Connectivity")
        print("-" * 50)

        try:
            response = self.session.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                print(f"✅ Frontend accessible at {FRONTEND_URL}")
                print(f"   Status: {response.status_code}")
            else:
                print(f"❌ Frontend issue: {response.status_code}")
        except Exception as e:
            print(f"❌ Frontend connection error: {e}")

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🧪 Comprehensive API Testing Suite")
        print("=" * 60)

        # Authenticate first
        if not self.authenticate():
            print("❌ Cannot proceed without authentication")
            return

        # Test all endpoints
        self.test_health_endpoints()

        # Upload a document for testing
        doc_id = self.test_document_upload()

        # Test OCR functionality
        self.test_ocr_endpoints(doc_id)

        # Test analysis functionality
        self.test_analysis_endpoints(doc_id)

        # Test workflow
        app_id = self.test_workflow_endpoints()

        # Test processing status
        self.test_processing_status(app_id)

        # Test frontend
        self.test_frontend_connectivity()

        print(f"\n🎉 Testing Complete!")
        print(f"Frontend URL: {FRONTEND_URL}")
        print(f"API Docs: {API_BASE_URL}/docs")

def main():
    """Main function to run tests"""
    tester = APITester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()