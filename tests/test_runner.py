"""
Comprehensive test runner for the Social Security AI system
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Comprehensive test runner with reporting"""

    def __init__(self):
        self.test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "test_suites": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
            }
        }

    def run_test_suite(self, test_file, description):
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {description}")
        print(f"Test file: {test_file}")
        print(f"{'='*60}")

        try:
            # Run pytest with verbose output
            result = subprocess.run([
                "python", "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--json-report",
                f"--json-report-file=test_results_{test_file.split('/')[-1]}.json"
            ], capture_output=True, text=True, cwd=project_root)

            suite_result = {
                "name": description,
                "file": test_file,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "passed" if result.returncode == 0 else "failed"
            }

            self.test_suites.append(suite_result)

            if result.returncode == 0:
                print(f"✅ {description} - PASSED")
            else:
                print(f"❌ {description} - FAILED")
                print(f"Error output:\n{result.stderr}")

            print(f"Test output:\n{result.stdout}")

        except Exception as e:
            print(f"❌ {description} - ERROR: {str(e)}")
            suite_result = {
                "name": description,
                "file": test_file,
                "status": "error",
                "error": str(e)
            }
            self.test_suites.append(suite_result)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting comprehensive test suite for Social Security AI system")
        print(f"Start time: {self.test_results['start_time']}")

        # Define test suites to run
        test_suites = [
            ("tests/test_api_endpoints.py", "Core API Endpoints"),
            ("tests/test_services.py", "Service Layer Tests"),
            ("tests/test_integration.py", "Integration Tests"),
            ("tests/test_user_management.py", "User Management APIs"),
            ("tests/test_document_management.py", "Document Management APIs"),
            ("tests/test_ai_services.py", "AI Services (Analysis, OCR, Decision, Chat)")
        ]

        # Run each test suite
        for test_file, description in test_suites:
            if os.path.exists(os.path.join(project_root, test_file)):
                self.run_test_suite(test_file, description)
            else:
                print(f"⚠️ Test file not found: {test_file}")

        # Generate final report
        self.generate_report()

    def run_quick_tests(self):
        """Run quick smoke tests"""
        print("🔥 Running quick smoke tests")

        quick_tests = [
            ("tests/conftest.py", "Test Configuration"),
            ("tests/test_api_endpoints.py::TestHealthEndpoint", "Health Check API"),
            ("tests/test_user_management.py::TestUserManagementAPIs::test_get_user_profile_unauthorized", "Authentication Test")
        ]

        for test_target, description in quick_tests:
            if "::" in test_target:
                # Specific test method
                self.run_specific_test(test_target, description)
            else:
                # Check if file exists
                if os.path.exists(os.path.join(project_root, test_target)):
                    print(f"✅ {description} - File exists")
                else:
                    print(f"❌ {description} - File missing")

    def run_specific_test(self, test_target, description):
        """Run a specific test"""
        try:
            result = subprocess.run([
                "python", "-m", "pytest",
                test_target,
                "-v"
            ], capture_output=True, text=True, cwd=project_root)

            if result.returncode == 0:
                print(f"✅ {description} - PASSED")
            else:
                print(f"❌ {description} - FAILED")

        except Exception as e:
            print(f"❌ {description} - ERROR: {str(e)}")

    def check_dependencies(self):
        """Check if required dependencies are available"""
        print("🔍 Checking dependencies...")

        dependencies = [
            ("fastapi", "FastAPI framework"),
            ("pytest", "Testing framework"),
            ("sqlalchemy", "Database ORM"),
            ("pydantic", "Data validation"),
            ("httpx", "HTTP client for testing")
        ]

        for module, description in dependencies:
            try:
                __import__(module)
                print(f"✅ {description} - Available")
            except ImportError:
                print(f"❌ {description} - Not available")

    def check_services(self):
        """Check if external services are available"""
        print("🔍 Checking external services...")

        # Check if Ollama is running
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama - Running")
                models = response.json().get("models", [])
                print(f"   Available models: {[m['name'] for m in models]}")
            else:
                print("❌ Ollama - Not responding")
        except Exception as e:
            print(f"❌ Ollama - Not available: {str(e)}")

        # Check if PostgreSQL is available (via environment or docker)
        try:
            from sqlalchemy import create_engine
            # Try to connect with default test database URL
            engine = create_engine("postgresql://test:test@localhost:5432/test_db")
            connection = engine.connect()
            connection.close()
            print("✅ PostgreSQL - Available")
        except Exception as e:
            print(f"❌ PostgreSQL - Not available: {str(e)}")

        # Check if Redis is available
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            print("✅ Redis - Available")
        except Exception as e:
            print(f"❌ Redis - Not available: {str(e)}")

    def generate_report(self):
        """Generate final test report"""
        self.test_results["end_time"] = datetime.utcnow().isoformat()

        # Calculate summary
        passed_suites = len([s for s in self.test_suites if s.get("status") == "passed"])
        failed_suites = len([s for s in self.test_suites if s.get("status") == "failed"])
        error_suites = len([s for s in self.test_suites if s.get("status") == "error"])

        print(f"\n{'='*60}")
        print("📊 TEST SUITE SUMMARY")
        print(f"{'='*60}")
        print(f"Total test suites: {len(self.test_suites)}")
        print(f"Passed: {passed_suites}")
        print(f"Failed: {failed_suites}")
        print(f"Errors: {error_suites}")
        print(f"Start time: {self.test_results['start_time']}")
        print(f"End time: {self.test_results['end_time']}")

        # Save detailed report
        report_file = f"test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

        # Print individual suite results
        print(f"\n{'='*60}")
        print("📋 INDIVIDUAL SUITE RESULTS")
        print(f"{'='*60}")

        for suite in self.test_suites:
            status_icon = "✅" if suite.get("status") == "passed" else "❌"
            print(f"{status_icon} {suite['name']}")
            if suite.get("status") != "passed" and suite.get("stderr"):
                print(f"   Error: {suite['stderr'][:200]}...")

    def run_api_validation(self):
        """Run basic API validation tests"""
        print("🔍 Running API validation tests...")

        try:
            # Try to import the main app
            from app.main import app
            print("✅ FastAPI app imports successfully")

            # Check number of routes
            total_routes = len(app.routes)
            print(f"✅ Total API routes: {total_routes}")

            # Check if routers are included
            router_prefixes = []
            for route in app.routes:
                if hasattr(route, 'path'):
                    prefix = route.path.split('/')[1] if route.path.startswith('/') and len(route.path.split('/')) > 1 else ''
                    if prefix and prefix not in router_prefixes:
                        router_prefixes.append(prefix)

            print(f"✅ API endpoints available: {', '.join(router_prefixes)}")

        except Exception as e:
            print(f"❌ API validation failed: {str(e)}")


def main():
    """Main test runner function"""
    runner = TestRunner()

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            runner.check_dependencies()
            runner.check_services()
            runner.run_api_validation()
            runner.run_quick_tests()
        elif sys.argv[1] == "deps":
            runner.check_dependencies()
            runner.check_services()
        elif sys.argv[1] == "api":
            runner.run_api_validation()
        elif sys.argv[1] == "full":
            runner.check_dependencies()
            runner.check_services()
            runner.run_api_validation()
            runner.run_all_tests()
        else:
            print("Usage: python test_runner.py [quick|deps|api|full]")
            print("  quick - Run quick validation tests")
            print("  deps  - Check dependencies and services")
            print("  api   - Validate API structure")
            print("  full  - Run complete test suite")
    else:
        print("🚀 Social Security AI - Test Suite Runner")
        print("Choose test mode:")
        print("1. Quick validation (quick)")
        print("2. Check dependencies (deps)")
        print("3. API validation (api)")
        print("4. Full test suite (full)")

        choice = input("\nEnter choice (1-4) or command: ").strip()

        if choice in ["1", "quick"]:
            runner.check_dependencies()
            runner.check_services()
            runner.run_api_validation()
            runner.run_quick_tests()
        elif choice in ["2", "deps"]:
            runner.check_dependencies()
            runner.check_services()
        elif choice in ["3", "api"]:
            runner.run_api_validation()
        elif choice in ["4", "full"]:
            runner.check_dependencies()
            runner.check_services()
            runner.run_api_validation()
            runner.run_all_tests()
        else:
            print("Invalid choice. Running quick validation...")
            runner.run_quick_tests()


if __name__ == "__main__":
    main()