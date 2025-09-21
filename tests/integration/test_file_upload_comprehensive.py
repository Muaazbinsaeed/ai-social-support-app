#!/usr/bin/env python3
"""
Comprehensive File Upload and PDF Processing Test Suite
Tests document upload, validation, processing, and error handling
"""

import requests
import json
import time
import random
import string
import io
import os
from typing import Dict, List, Any
import sys
from datetime import datetime


class FileUploadTester:
    """Comprehensive file upload and document processing testing"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None

    def log_test(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log test result with use case information"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "details": details or {}
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details and status != "PASS":
            print(f"   Details: {details}")

    def setup_authentication(self):
        """Setup authentication for protected endpoints"""
        try:
            # Generate unique test user
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            self.test_user_data = {
                "username": f"filetest_{random_suffix}",
                "email": f"filetest_{random_suffix}@example.com",
                "password": "FileTest123!",
                "full_name": f"File Test User {random_suffix.upper()}"
            }

            # Register user
            reg_response = self.session.post(
                f"{self.base_url}/auth/register",
                json=self.test_user_data,
                headers={"Content-Type": "application/json"}
            )

            if reg_response.status_code != 201:
                raise Exception(f"Failed to register test user: {reg_response.status_code}")

            # Login and get token
            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={
                    "username": self.test_user_data["username"],
                    "password": self.test_user_data["password"]
                },
                headers={"Content-Type": "application/json"}
            )

            if login_response.status_code != 200:
                raise Exception(f"Failed to login test user: {login_response.status_code}")

            token_data = login_response.json()
            self.auth_token = token_data["access_token"]

            self.log_test("Authentication Setup", "PASS", {
                "user_created": True,
                "token_obtained": True,
                "use_case": "Setup authentication for file upload testing"
            })

        except Exception as e:
            self.log_test("Authentication Setup", "FAIL", {"error": str(e)})
            return False

        return True

    def create_test_files(self):
        """Create test files for upload"""
        # Create a minimal PDF file
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Bank Statement) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000173 00000 n
0000000301 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""

        # Create a minimal image file (1x1 PNG)
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00'

        return {
            "valid_pdf": ("bank_statement.pdf", pdf_content, "application/pdf"),
            "valid_image": ("emirates_id.png", png_content, "image/png"),
            "invalid_file": ("document.txt", b"This is a text file", "text/plain"),
            "large_file": ("large.pdf", b"A" * (60 * 1024 * 1024), "application/pdf")  # 60MB
        }

    def test_document_types_endpoint(self):
        """Test document types information endpoint"""
        try:
            expected_status = 200
            expected_fields = ["supported_types", "limits", "requirements"]

            response = self.session.get(f"{self.base_url}/documents/types")

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    # Check specific requirements
                    supported_types = data["supported_types"]
                    if "bank_statement" in supported_types and "emirates_id" in supported_types:
                        self.log_test("Document Types Endpoint", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_fields": expected_fields,
                            "bank_statement_extensions": supported_types["bank_statement"]["extensions"],
                            "emirates_id_extensions": supported_types["emirates_id"]["extensions"],
                            "max_size_mb": data["limits"]["max_file_size_mb"],
                            "use_case": "Get supported file types and upload requirements"
                        })
                    else:
                        self.log_test("Document Types Endpoint", "FAIL", {
                            "error": "Missing required document types",
                            "supported_types": list(supported_types.keys())
                        })
                else:
                    self.log_test("Document Types Endpoint", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("Document Types Endpoint", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Document Types Endpoint", "FAIL", {"error": str(e)})

    def test_file_upload_success(self):
        """Test successful file upload with valid PDF and image"""
        if not self.auth_token:
            self.log_test("File Upload Success", "FAIL", {"error": "No authentication token"})
            return

        try:
            test_files = self.create_test_files()
            pdf_name, pdf_content, pdf_type = test_files["valid_pdf"]
            img_name, img_content, img_type = test_files["valid_image"]

            expected_status = 201
            expected_fields = ["message", "documents", "application_id", "user_id", "uploaded_at", "next_steps"]

            # Prepare multipart form data
            files = {
                'bank_statement': (pdf_name, io.BytesIO(pdf_content), pdf_type),
                'emirates_id': (img_name, io.BytesIO(img_content), img_type)
            }

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.post(
                f"{self.base_url}/documents/upload",
                files=files,
                headers=headers
            )

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    documents = data["documents"]
                    if "bank_statement" in documents and "emirates_id" in documents:
                        self.log_test("File Upload Success", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_fields": expected_fields,
                            "bank_statement_id": documents["bank_statement"]["id"],
                            "emirates_id_id": documents["emirates_id"]["id"],
                            "bank_statement_status": documents["bank_statement"]["status"],
                            "emirates_id_status": documents["emirates_id"]["status"],
                            "next_steps_count": len(data["next_steps"]),
                            "use_case": "Upload valid bank statement PDF and Emirates ID image for processing"
                        })
                    else:
                        self.log_test("File Upload Success", "FAIL", {
                            "error": "Missing document types in response",
                            "documents": list(documents.keys()) if isinstance(documents, dict) else documents
                        })
                else:
                    self.log_test("File Upload Success", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("File Upload Success", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:300]
                })

        except Exception as e:
            self.log_test("File Upload Success", "FAIL", {"error": str(e)})

    def test_file_upload_unauthorized(self):
        """Test file upload without authentication"""
        try:
            test_files = self.create_test_files()
            pdf_name, pdf_content, pdf_type = test_files["valid_pdf"]
            img_name, img_content, img_type = test_files["valid_image"]

            expected_status = 403  # FastAPI returns 403 for "Not authenticated"

            files = {
                'bank_statement': (pdf_name, io.BytesIO(pdf_content), pdf_type),
                'emirates_id': (img_name, io.BytesIO(img_content), img_type)
            }

            response = self.session.post(
                f"{self.base_url}/documents/upload",
                files=files
            )

            if response.status_code == expected_status:
                data = response.json()
                if "detail" in data and data["detail"] == "Not authenticated":
                    self.log_test("File Upload Unauthorized", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_response": "Not authenticated",
                        "use_case": "Block unauthorized file upload attempts"
                    })
                else:
                    self.log_test("File Upload Unauthorized", "FAIL", {
                        "error": "Unexpected error response format",
                        "expected": "Not authenticated",
                        "actual": data
                    })
            else:
                self.log_test("File Upload Unauthorized", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("File Upload Unauthorized", "FAIL", {"error": str(e)})

    def test_invalid_file_types(self):
        """Test upload with invalid file types"""
        if not self.auth_token:
            self.log_test("Invalid File Types", "FAIL", {"error": "No authentication token"})
            return

        try:
            test_files = self.create_test_files()
            txt_name, txt_content, txt_type = test_files["invalid_file"]
            img_name, img_content, img_type = test_files["valid_image"]

            expected_status = 400  # Bad Request for invalid file
            expected_error = "INVALID_FILE"

            # Try uploading text file as bank statement
            files = {
                'bank_statement': (txt_name, io.BytesIO(txt_content), txt_type),
                'emirates_id': (img_name, io.BytesIO(img_content), img_type)
            }

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.post(
                f"{self.base_url}/documents/upload",
                files=files,
                headers=headers
            )

            if response.status_code == expected_status:
                data = response.json()
                if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
                    if data["detail"]["error"] == expected_error:
                        self.log_test("Invalid File Types", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_error": expected_error,
                            "actual_error": data["detail"]["error"],
                            "file_type": data["detail"].get("file_type"),
                            "filename": data["detail"].get("filename"),
                            "use_case": "Reject invalid file types with appropriate error message"
                        })
                    else:
                        self.log_test("Invalid File Types", "FAIL", {
                            "error": "Wrong error code",
                            "expected_error": expected_error,
                            "actual_error": data["detail"]["error"]
                        })
                else:
                    self.log_test("Invalid File Types", "FAIL", {
                        "error": "Unexpected error response format",
                        "expected_structure": "detail.error format",
                        "actual": data
                    })
            else:
                self.log_test("Invalid File Types", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Invalid File Types", "FAIL", {"error": str(e)})

    def test_missing_files(self):
        """Test upload with missing required files"""
        if not self.auth_token:
            self.log_test("Missing Files", "FAIL", {"error": "No authentication token"})
            return

        try:
            test_files = self.create_test_files()
            pdf_name, pdf_content, pdf_type = test_files["valid_pdf"]

            expected_status = 422  # Unprocessable Entity for missing required field

            # Upload only bank statement, missing emirates_id
            files = {
                'bank_statement': (pdf_name, io.BytesIO(pdf_content), pdf_type)
            }

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.post(
                f"{self.base_url}/documents/upload",
                files=files,
                headers=headers
            )

            if response.status_code == expected_status:
                data = response.json()
                # Check for custom error format or FastAPI validation error format
                if ("detail" in data and isinstance(data["detail"], list)) or \
                   ("error" in data and data["error"] == "VALIDATION_ERROR" and "details" in data):
                    # Handle both formats - custom error handler or FastAPI default
                    if "error" in data and data["error"] == "VALIDATION_ERROR":
                        # Custom validation error format
                        validation_errors = len(data["details"]) if "details" in data else 0
                    else:
                        # FastAPI default format
                        validation_errors = len(data["detail"])

                    self.log_test("Missing Files", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "validation_errors": validation_errors,
                        "error_type": "missing_required_file",
                        "use_case": "Validate that both bank statement and Emirates ID are required"
                    })
                else:
                    self.log_test("Missing Files", "FAIL", {
                        "error": "Unexpected validation error format",
                        "expected": "FastAPI validation error list or custom error format",
                        "actual": data
                    })
            else:
                self.log_test("Missing Files", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Missing Files", "FAIL", {"error": str(e)})

    def test_document_status_endpoint(self):
        """Test document status checking"""
        if not self.auth_token:
            self.log_test("Document Status", "FAIL", {"error": "No authentication token"})
            return

        try:
            test_document_id = "test-doc-123"
            expected_status = 200
            expected_fields = ["document_id", "status", "stage", "progress", "processing_steps", "user_id"]

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/documents/status/{test_document_id}",
                headers=headers
            )

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    processing_steps = data["processing_steps"]
                    if isinstance(processing_steps, list) and len(processing_steps) > 0:
                        self.log_test("Document Status", "PASS", {
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "expected_fields": expected_fields,
                            "document_id": data["document_id"],
                            "status": data["status"],
                            "stage": data["stage"],
                            "progress": data["progress"],
                            "processing_steps_count": len(processing_steps),
                            "use_case": "Track document processing status and progress"
                        })
                    else:
                        self.log_test("Document Status", "FAIL", {
                            "error": "Invalid processing steps format",
                            "processing_steps": processing_steps
                        })
                else:
                    self.log_test("Document Status", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("Document Status", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Document Status", "FAIL", {"error": str(e)})

    def test_document_deletion(self):
        """Test document deletion"""
        if not self.auth_token:
            self.log_test("Document Deletion", "FAIL", {"error": "No authentication token"})
            return

        try:
            test_document_id = "test-doc-123"
            expected_status = 200
            expected_fields = ["message", "document_id", "deleted_at", "user_id"]

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.delete(
                f"{self.base_url}/documents/{test_document_id}",
                headers=headers
            )

            if response.status_code == expected_status:
                data = response.json()
                if all(field in data for field in expected_fields):
                    self.log_test("Document Deletion", "PASS", {
                        "expected_status": expected_status,
                        "actual_status": response.status_code,
                        "expected_fields": expected_fields,
                        "document_id": data["document_id"],
                        "message": data["message"],
                        "use_case": "Delete uploaded documents when no longer needed"
                    })
                else:
                    self.log_test("Document Deletion", "FAIL", {
                        "error": "Missing expected fields",
                        "expected_fields": expected_fields,
                        "actual_fields": list(data.keys())
                    })
            else:
                self.log_test("Document Deletion", "FAIL", {
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response.text[:200]
                })

        except Exception as e:
            self.log_test("Document Deletion", "FAIL", {"error": str(e)})

    def test_pdf_processing_flow(self):
        """Test complete PDF processing workflow"""
        if not self.auth_token:
            self.log_test("PDF Processing Flow", "FAIL", {"error": "No authentication token"})
            return

        try:
            # Step 1: Get supported types
            types_response = self.session.get(f"{self.base_url}/documents/types")
            if types_response.status_code != 200:
                raise Exception("Failed to get document types")

            # Step 2: Upload documents
            test_files = self.create_test_files()
            pdf_name, pdf_content, pdf_type = test_files["valid_pdf"]
            img_name, img_content, img_type = test_files["valid_image"]

            files = {
                'bank_statement': (pdf_name, io.BytesIO(pdf_content), pdf_type),
                'emirates_id': (img_name, io.BytesIO(img_content), img_type)
            }

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            upload_response = self.session.post(
                f"{self.base_url}/documents/upload",
                files=files,
                headers=headers
            )

            if upload_response.status_code != 201:
                raise Exception(f"Failed to upload documents: {upload_response.status_code}")

            upload_data = upload_response.json()
            bank_statement_id = upload_data["documents"]["bank_statement"]["id"]

            # Step 3: Check document status
            status_response = self.session.get(
                f"{self.base_url}/documents/status/{bank_statement_id}",
                headers=headers
            )

            if status_response.status_code != 200:
                raise Exception(f"Failed to get document status: {status_response.status_code}")

            # Step 4: Clean up (delete document)
            delete_response = self.session.delete(
                f"{self.base_url}/documents/{bank_statement_id}",
                headers=headers
            )

            if delete_response.status_code != 200:
                raise Exception(f"Failed to delete document: {delete_response.status_code}")

            self.log_test("PDF Processing Flow", "PASS", {
                "steps_completed": 4,
                "types_check": "success",
                "upload": "success",
                "status_check": "success",
                "deletion": "success",
                "document_id": bank_statement_id,
                "use_case": "Complete document lifecycle from upload to deletion"
            })

        except Exception as e:
            self.log_test("PDF Processing Flow", "FAIL", {"error": str(e)})

    def run_all_tests(self):
        """Run comprehensive file upload test suite"""
        print("📁 Starting Comprehensive File Upload & PDF Processing Test Suite")
        print("=" * 75)
        print("🎯 Testing document upload, validation, processing, and error handling")
        print("=" * 75)

        # Setup authentication first
        if not self.setup_authentication():
            print("❌ Failed to setup authentication. Cannot proceed with file upload tests.")
            return

        test_methods = [
            self.test_document_types_endpoint,
            self.test_file_upload_success,
            self.test_file_upload_unauthorized,
            self.test_invalid_file_types,
            self.test_missing_files,
            self.test_document_status_endpoint,
            self.test_document_deletion,
            self.test_pdf_processing_flow,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Error running {test_method.__name__}: {str(e)}")

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate file upload test results summary"""
        print("\n" + "=" * 75)
        print("📊 FILE UPLOAD TEST RESULTS SUMMARY")
        print("=" * 75)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 File Upload Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")

        if failed_tests > 0:
            print(f"\n❌ Failed File Upload Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"   - {result['test_name']}: {result['details'].get('error', 'Unknown error')}")

        # Overall system status
        if success_rate >= 95:
            print(f"\n🟢 FILE UPLOAD STATUS: EXCELLENT ({success_rate:.1f}%)")
        elif success_rate >= 85:
            print(f"\n🟡 FILE UPLOAD STATUS: GOOD ({success_rate:.1f}%)")
        elif success_rate >= 70:
            print(f"\n🟠 FILE UPLOAD STATUS: FAIR ({success_rate:.1f}%)")
        else:
            print(f"\n🔴 FILE UPLOAD STATUS: POOR ({success_rate:.1f}%)")

        print("\n📋 FILE UPLOAD USE CASES VALIDATED:")
        use_cases = set()
        for result in self.test_results:
            if result["status"] == "PASS" and "use_case" in result["details"]:
                use_cases.add(result["details"]["use_case"])

        for i, use_case in enumerate(sorted(use_cases), 1):
            print(f"   {i}. {use_case}")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "detailed_results": self.test_results,
            "use_cases_validated": list(use_cases)
        }


def main():
    """Main testing function"""
    tester = FileUploadTester()

    # Check if API is accessible
    try:
        response = requests.get("http://localhost:8000/health/basic", timeout=5)
        if response.status_code != 200:
            print("❌ API is not accessible. Please ensure the server is running.")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API at http://localhost:8000")
        print("   Please ensure Docker services are running with: docker compose up")
        sys.exit(1)

    # Run all tests
    results = tester.run_all_tests()

    # Save results to file
    with open("file_upload_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 File upload test results saved to: file_upload_test_results.json")

    return results


if __name__ == "__main__":
    main()