#!/usr/bin/env python3
"""
Social Security AI System - Comprehensive Verification Script

This script verifies that all system modules are working correctly by:
1. Testing infrastructure connectivity
2. Verifying API endpoints
3. Testing authentication flow
4. Verifying document processing
5. Testing AI decision making
6. Checking background workers
7. Testing frontend dashboard
"""

import asyncio
import json
import os
import requests
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import base64

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Color codes for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class SystemVerifier:
    """Comprehensive system verification class"""

    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.frontend_base = "http://localhost:8005"
        self.results = {}
        self.test_user_token = None
        self.test_application_id = None

        # Test configuration
        self.test_user = {
            "username": "verify_test_user",
            "email": "verify@test.com",
            "password": "VerifyTest123!",
            "full_name": "Verification Test User"
        }

        self.test_application = {
            "full_name": "Ahmed Test User",
            "emirates_id": "784-1990-1234567-8",
            "phone": "+971501234567",
            "email": "ahmed.verify@test.com"
        }

    def print_status(self, message: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

    def print_success(self, message: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

    def print_warning(self, message: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

    def print_error(self, message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def print_header(self, message: str):
        print(f"\n{Colors.PURPLE}=== {message} ==={Colors.NC}")

    def test_infrastructure_connectivity(self) -> Dict[str, bool]:
        """Test basic infrastructure connectivity"""
        self.print_header("Testing Infrastructure Connectivity")

        results = {}

        # Test PostgreSQL
        self.print_status("Testing PostgreSQL connectivity...")
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("database") == "healthy":
                    self.print_success("PostgreSQL: Connected")
                    results["postgresql"] = True
                else:
                    self.print_error("PostgreSQL: Unhealthy")
                    results["postgresql"] = False
            else:
                self.print_error("PostgreSQL: Cannot reach health endpoint")
                results["postgresql"] = False
        except Exception as e:
            self.print_error(f"PostgreSQL: {str(e)}")
            results["postgresql"] = False

        # Test Redis
        self.print_status("Testing Redis connectivity...")
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("redis") == "healthy":
                    self.print_success("Redis: Connected")
                    results["redis"] = True
                else:
                    self.print_error("Redis: Unhealthy")
                    results["redis"] = False
            else:
                self.print_error("Redis: Cannot reach health endpoint")
                results["redis"] = False
        except Exception as e:
            self.print_error(f"Redis: {str(e)}")
            results["redis"] = False

        # Test Qdrant
        self.print_status("Testing Qdrant connectivity...")
        try:
            response = requests.get("http://localhost:6333/healthz", timeout=10)
            if response.status_code == 200:
                self.print_success("Qdrant: Connected")
                results["qdrant"] = True
            else:
                self.print_error(f"Qdrant: HTTP {response.status_code}")
                results["qdrant"] = False
        except Exception as e:
            self.print_warning(f"Qdrant: {str(e)} (may not be critical)")
            results["qdrant"] = False

        # Test Ollama
        self.print_status("Testing Ollama connectivity...")
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                self.print_success(f"Ollama: Connected ({len(models)} models available)")
                results["ollama"] = True
            else:
                self.print_warning(f"Ollama: HTTP {response.status_code} (will use fallback)")
                results["ollama"] = False
        except Exception as e:
            self.print_warning(f"Ollama: {str(e)} (will use fallback)")
            results["ollama"] = False

        return results

    def test_api_endpoints(self) -> Dict[str, bool]:
        """Test core API endpoints"""
        self.print_header("Testing API Endpoints")

        results = {}

        # Health endpoint
        self.print_status("Testing health endpoint...")
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                self.print_success("Health endpoint: OK")
                results["health"] = True
            else:
                self.print_error(f"Health endpoint: HTTP {response.status_code}")
                results["health"] = False
        except Exception as e:
            self.print_error(f"Health endpoint: {str(e)}")
            results["health"] = False

        # Documentation endpoint
        self.print_status("Testing documentation endpoint...")
        try:
            response = requests.get(f"{self.api_base}/docs", timeout=10)
            if response.status_code == 200:
                self.print_success("Documentation endpoint: OK")
                results["docs"] = True
            else:
                self.print_error(f"Documentation endpoint: HTTP {response.status_code}")
                results["docs"] = False
        except Exception as e:
            self.print_error(f"Documentation endpoint: {str(e)}")
            results["docs"] = False

        # OpenAPI schema
        self.print_status("Testing OpenAPI schema...")
        try:
            response = requests.get(f"{self.api_base}/openapi.json", timeout=10)
            if response.status_code == 200:
                schema = response.json()
                if "openapi" in schema and "paths" in schema:
                    self.print_success("OpenAPI schema: Valid")
                    results["openapi"] = True
                else:
                    self.print_error("OpenAPI schema: Invalid format")
                    results["openapi"] = False
            else:
                self.print_error(f"OpenAPI schema: HTTP {response.status_code}")
                results["openapi"] = False
        except Exception as e:
            self.print_error(f"OpenAPI schema: {str(e)}")
            results["openapi"] = False

        return results

    def test_authentication_flow(self) -> Dict[str, bool]:
        """Test user authentication flow"""
        self.print_header("Testing Authentication Flow")

        results = {}

        # User registration
        self.print_status("Testing user registration...")
        try:
            response = requests.post(
                f"{self.api_base}/auth/register",
                json=self.test_user,
                timeout=10
            )
            if response.status_code == 201:
                user_data = response.json()
                self.print_success(f"User registration: OK (User ID: {user_data.get('id')})")
                results["registration"] = True
            elif response.status_code == 409:
                self.print_warning("User already exists, continuing...")
                results["registration"] = True
            else:
                self.print_error(f"User registration: HTTP {response.status_code}")
                results["registration"] = False
        except Exception as e:
            self.print_error(f"User registration: {str(e)}")
            results["registration"] = False

        # User login
        self.print_status("Testing user login...")
        try:
            login_data = {
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
            response = requests.post(
                f"{self.api_base}/auth/login",
                json=login_data,
                timeout=10
            )
            if response.status_code == 200:
                token_data = response.json()
                self.test_user_token = token_data.get("access_token")
                self.print_success("User login: OK")
                results["login"] = True
            else:
                self.print_error(f"User login: HTTP {response.status_code}")
                results["login"] = False
        except Exception as e:
            self.print_error(f"User login: {str(e)}")
            results["login"] = False

        # Token verification
        if self.test_user_token:
            self.print_status("Testing token verification...")
            try:
                headers = {"Authorization": f"Bearer {self.test_user_token}"}
                response = requests.get(
                    f"{self.api_base}/auth/me",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    user_data = response.json()
                    self.print_success(f"Token verification: OK (User: {user_data.get('username')})")
                    results["token_verification"] = True
                else:
                    self.print_error(f"Token verification: HTTP {response.status_code}")
                    results["token_verification"] = False
            except Exception as e:
                self.print_error(f"Token verification: {str(e)}")
                results["token_verification"] = False
        else:
            results["token_verification"] = False

        return results

    def test_application_flow(self) -> Dict[str, bool]:
        """Test application submission flow"""
        self.print_header("Testing Application Flow")

        results = {}

        if not self.test_user_token:
            self.print_error("No authentication token available")
            return {"application_creation": False}

        headers = {"Authorization": f"Bearer {self.test_user_token}"}

        # Create application
        self.print_status("Testing application creation...")
        try:
            response = requests.post(
                f"{self.api_base}/applications/",
                json=self.test_application,
                headers=headers,
                timeout=10
            )
            if response.status_code == 201:
                app_data = response.json()
                self.test_application_id = app_data.get("id")
                self.print_success(f"Application creation: OK (ID: {self.test_application_id})")
                results["application_creation"] = True
            else:
                self.print_error(f"Application creation: HTTP {response.status_code}")
                results["application_creation"] = False
        except Exception as e:
            self.print_error(f"Application creation: {str(e)}")
            results["application_creation"] = False

        # Get application status
        if self.test_application_id:
            self.print_status("Testing application status retrieval...")
            try:
                response = requests.get(
                    f"{self.api_base}/applications/{self.test_application_id}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    app_data = response.json()
                    status = app_data.get("current_state", {}).get("state")
                    self.print_success(f"Application status: OK (Status: {status})")
                    results["application_status"] = True
                else:
                    self.print_error(f"Application status: HTTP {response.status_code}")
                    results["application_status"] = False
            except Exception as e:
                self.print_error(f"Application status: {str(e)}")
                results["application_status"] = False
        else:
            results["application_status"] = False

        return results

    def test_document_processing(self) -> Dict[str, bool]:
        """Test document upload and processing"""
        self.print_header("Testing Document Processing")

        results = {}

        if not self.test_user_token or not self.test_application_id:
            self.print_error("Missing authentication token or application ID")
            return {"document_upload": False, "document_processing": False}

        headers = {"Authorization": f"Bearer {self.test_user_token}"}

        # Create test document content
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF"

        # Test document upload
        self.print_status("Testing document upload...")
        try:
            files = {
                'file': ('test_bank_statement.pdf', test_pdf_content, 'application/pdf')
            }
            data = {
                'document_type': 'bank_statement',
                'application_id': self.test_application_id
            }

            response = requests.post(
                f"{self.api_base}/documents/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                doc_data = response.json()
                document_id = doc_data.get("id")
                self.print_success(f"Document upload: OK (ID: {document_id})")
                results["document_upload"] = True

                # Test document status
                self.print_status("Testing document status...")
                time.sleep(2)  # Allow processing to start

                status_response = requests.get(
                    f"{self.api_base}/documents/{document_id}/status",
                    headers=headers,
                    timeout=10
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    processing_status = status_data.get("processing_status")
                    self.print_success(f"Document status: OK (Status: {processing_status})")
                    results["document_processing"] = True
                else:
                    self.print_error(f"Document status: HTTP {status_response.status_code}")
                    results["document_processing"] = False

            else:
                self.print_error(f"Document upload: HTTP {response.status_code}")
                if response.status_code == 400:
                    self.print_error(f"Error details: {response.text}")
                results["document_upload"] = False
                results["document_processing"] = False

        except Exception as e:
            self.print_error(f"Document upload: {str(e)}")
            results["document_upload"] = False
            results["document_processing"] = False

        return results

    def test_decision_making(self) -> Dict[str, bool]:
        """Test AI decision making"""
        self.print_header("Testing AI Decision Making")

        results = {}

        if not self.test_user_token or not self.test_application_id:
            self.print_error("Missing authentication token or application ID")
            return {"decision_processing": False}

        headers = {"Authorization": f"Bearer {self.test_user_token}"}

        # Test decision endpoint
        self.print_status("Testing decision processing...")
        try:
            response = requests.post(
                f"{self.api_base}/applications/{self.test_application_id}/process-decision",
                headers=headers,
                timeout=30
            )

            if response.status_code in [200, 202]:
                self.print_success("Decision processing: Initiated")
                results["decision_processing"] = True

                # Check decision status after a delay
                time.sleep(5)
                status_response = requests.get(
                    f"{self.api_base}/applications/{self.test_application_id}",
                    headers=headers,
                    timeout=10
                )

                if status_response.status_code == 200:
                    app_data = status_response.json()
                    decision = app_data.get("decision")
                    if decision:
                        decision_status = decision.get("decision")
                        self.print_success(f"Decision result: {decision_status}")
                    else:
                        self.print_warning("Decision still processing...")

            else:
                self.print_error(f"Decision processing: HTTP {response.status_code}")
                results["decision_processing"] = False

        except Exception as e:
            self.print_error(f"Decision processing: {str(e)}")
            results["decision_processing"] = False

        return results

    def test_background_workers(self) -> Dict[str, bool]:
        """Test Celery background workers"""
        self.print_header("Testing Background Workers")

        results = {}

        # Test worker health through API
        self.print_status("Testing worker connectivity...")
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                workers_status = health_data.get("workers", "unknown")
                if workers_status == "healthy":
                    self.print_success("Background workers: Healthy")
                    results["workers_health"] = True
                else:
                    self.print_warning(f"Background workers: {workers_status}")
                    results["workers_health"] = False
            else:
                self.print_error("Cannot check worker health")
                results["workers_health"] = False
        except Exception as e:
            self.print_error(f"Worker health check: {str(e)}")
            results["workers_health"] = False

        return results

    def test_frontend_dashboard(self) -> Dict[str, bool]:
        """Test Streamlit frontend dashboard"""
        self.print_header("Testing Frontend Dashboard")

        results = {}

        # Test dashboard accessibility
        self.print_status("Testing dashboard accessibility...")
        try:
            response = requests.get(self.frontend_base, timeout=10)
            if response.status_code == 200:
                self.print_success("Dashboard: Accessible")
                results["dashboard_access"] = True
            else:
                self.print_error(f"Dashboard: HTTP {response.status_code}")
                results["dashboard_access"] = False
        except Exception as e:
            self.print_error(f"Dashboard: {str(e)}")
            results["dashboard_access"] = False

        return results

    def cleanup_test_data(self):
        """Clean up test data created during verification"""
        self.print_header("Cleaning Up Test Data")

        if not self.test_user_token:
            self.print_warning("No token available for cleanup")
            return

        headers = {"Authorization": f"Bearer {self.test_user_token}"}

        # Delete test application if created
        if self.test_application_id:
            try:
                response = requests.delete(
                    f"{self.api_base}/applications/{self.test_application_id}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code in [200, 204, 404]:
                    self.print_success("Test application cleaned up")
                else:
                    self.print_warning(f"Application cleanup: HTTP {response.status_code}")
            except Exception as e:
                self.print_warning(f"Application cleanup failed: {str(e)}")

        self.print_status("Test data cleanup completed")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        total_tests = 0
        passed_tests = 0

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {},
            "details": self.results,
            "recommendations": []
        }

        # Count results
        for category, tests in self.results.items():
            if isinstance(tests, dict):
                for test_name, result in tests.items():
                    total_tests += 1
                    if result:
                        passed_tests += 1
            elif isinstance(tests, bool):
                total_tests += 1
                if tests:
                    passed_tests += 1

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        report["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round(success_rate, 2)
        }

        # Generate recommendations
        if not self.results.get("infrastructure", {}).get("ollama", False):
            report["recommendations"].append("Consider setting up Ollama for better AI performance")

        if not self.results.get("infrastructure", {}).get("qdrant", False):
            report["recommendations"].append("Qdrant vector database is not responding (may not be critical)")

        if success_rate < 80:
            report["recommendations"].append("System has significant issues that need attention")
        elif success_rate < 95:
            report["recommendations"].append("System is mostly functional but has some issues")
        else:
            report["recommendations"].append("System is functioning well!")

        return report

    def run_full_verification(self) -> Dict[str, Any]:
        """Run complete system verification"""
        print(f"{Colors.PURPLE}🔍 Social Security AI System - Full Verification{Colors.NC}")
        print("=" * 65)

        try:
            # Run all verification tests
            self.results["infrastructure"] = self.test_infrastructure_connectivity()
            self.results["api_endpoints"] = self.test_api_endpoints()
            self.results["authentication"] = self.test_authentication_flow()
            self.results["application_flow"] = self.test_application_flow()
            self.results["document_processing"] = self.test_document_processing()
            self.results["decision_making"] = self.test_decision_making()
            self.results["background_workers"] = self.test_background_workers()
            self.results["frontend"] = self.test_frontend_dashboard()

            # Clean up test data
            self.cleanup_test_data()

            # Generate report
            report = self.generate_report()

            # Print summary
            self.print_header("Verification Summary")

            print(f"Total Tests: {Colors.CYAN}{report['summary']['total_tests']}{Colors.NC}")
            print(f"Passed: {Colors.GREEN}{report['summary']['passed_tests']}{Colors.NC}")
            print(f"Failed: {Colors.RED}{report['summary']['failed_tests']}{Colors.NC}")
            print(f"Success Rate: {Colors.CYAN}{report['summary']['success_rate']}%{Colors.NC}")

            # Print recommendations
            if report["recommendations"]:
                self.print_header("Recommendations")
                for rec in report["recommendations"]:
                    print(f"• {rec}")

            # Overall status
            if report["summary"]["success_rate"] >= 95:
                self.print_success("🎉 System verification completed successfully!")
            elif report["summary"]["success_rate"] >= 80:
                self.print_warning("⚠️ System verification completed with minor issues")
            else:
                self.print_error("❌ System verification found significant issues")

            # Save report
            report_file = PROJECT_ROOT / "logs" / f"verification_report_{int(time.time())}.json"
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"\nDetailed report saved to: {report_file}")

            return report

        except KeyboardInterrupt:
            self.print_warning("\nVerification interrupted by user")
            return {"error": "interrupted"}
        except Exception as e:
            self.print_error(f"Verification failed: {str(e)}")
            return {"error": str(e)}

def main():
    """Main entry point"""
    verifier = SystemVerifier()

    try:
        report = verifier.run_full_verification()

        # Exit with appropriate code
        if "error" in report:
            sys.exit(1)
        elif report.get("summary", {}).get("success_rate", 0) < 80:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"{Colors.RED}[FATAL]{Colors.NC} Verification script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()