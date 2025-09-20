#!/usr/bin/env python3
"""
Comprehensive test runner for Social Security AI System
Consolidates all testing functionality into a single script
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRunner:
    """Comprehensive test runner for the Social Security AI system"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {}
        self.overall_success = True

    def check_docker_services(self) -> bool:
        """Check if Docker services are running"""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode != 0:
                print("❌ Docker Compose not running")
                return False

            output_lines = result.stdout.strip().split('\n')
            # Skip header line and count running services
            service_lines = [line for line in output_lines[1:] if 'Up' in line]

            print(f"✅ Docker services running: {len(service_lines)} services detected")
            return len(service_lines) >= 5  # Minimum required services

        except Exception as e:
            print(f"❌ Failed to check Docker services: {e}")
            return False

    def run_health_check(self) -> bool:
        """Run system health check"""
        try:
            print("\n🏥 Running system health check...")
            result = subprocess.run(
                [sys.executable, "scripts/health_check.py"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            print(result.stdout)
            if result.stderr:
                print(f"Health check stderr: {result.stderr}")

            success = result.returncode == 0
            self.test_results['health_check'] = {
                'success': success,
                'output': result.stdout,
                'duration': 'N/A'
            }

            return success

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            self.test_results['health_check'] = {'success': False, 'error': str(e)}
            return False

    def run_pytest_tests(self) -> bool:
        """Run pytest test suite"""
        try:
            print("\n🧪 Running pytest test suite...")
            start_time = time.time()

            # Run comprehensive tests
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "tests/test_comprehensive.py",
                "-v",
                "--tb=short",
                "--disable-warnings"
            ], capture_output=True, text=True, cwd=self.project_root)

            duration = time.time() - start_time

            print(result.stdout)
            if result.stderr:
                print(f"Pytest stderr: {result.stderr}")

            success = result.returncode == 0
            self.test_results['pytest'] = {
                'success': success,
                'output': result.stdout,
                'duration': f"{duration:.2f}s",
                'return_code': result.returncode
            }

            return success

        except Exception as e:
            print(f"❌ Pytest execution failed: {e}")
            self.test_results['pytest'] = {'success': False, 'error': str(e)}
            return False

    def run_api_tests(self) -> bool:
        """Run API endpoint tests"""
        try:
            print("\n🔗 Running API endpoint tests...")
            import requests
            import time

            base_url = "http://localhost:8000"
            api_tests = []

            # Test API endpoints
            endpoints = [
                ("GET", "/", "Root API endpoint"),
                ("GET", "/health/basic", "Basic health check"),
                ("GET", "/docs", "API documentation"),
                ("GET", "/openapi.json", "OpenAPI schema")
            ]

            for method, endpoint, description in endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    duration = time.time() - start_time

                    success = response.status_code in [200, 201]
                    api_tests.append({
                        'endpoint': endpoint,
                        'method': method,
                        'description': description,
                        'status_code': response.status_code,
                        'success': success,
                        'duration': f"{duration*1000:.0f}ms"
                    })

                    print(f"  {'✅' if success else '❌'} {method} {endpoint} - {response.status_code}")

                except Exception as e:
                    print(f"  ❌ {method} {endpoint} - Error: {e}")
                    api_tests.append({
                        'endpoint': endpoint,
                        'method': method,
                        'description': description,
                        'success': False,
                        'error': str(e)
                    })

            # Test authentication flow
            try:
                print("\n🔐 Testing authentication flow...")

                # Register user
                register_data = {
                    "username": f"testuser_{int(time.time())}",
                    "email": f"test_{int(time.time())}@example.com",
                    "password": "testpass123",
                    "full_name": "Test User"
                }

                register_response = requests.post(
                    f"{base_url}/auth/register",
                    json=register_data,
                    timeout=10
                )

                register_success = register_response.status_code == 201
                print(f"  {'✅' if register_success else '❌'} User registration - {register_response.status_code}")

                if register_success:
                    # Login
                    login_data = {
                        "username": register_data["username"],
                        "password": register_data["password"]
                    }

                    login_response = requests.post(
                        f"{base_url}/auth/login",
                        json=login_data,
                        timeout=10
                    )

                    login_success = login_response.status_code == 200
                    print(f"  {'✅' if login_success else '❌'} User login - {login_response.status_code}")

                    if login_success:
                        token = login_response.json().get("access_token")
                        headers = {"Authorization": f"Bearer {token}"}

                        # Test protected endpoint
                        me_response = requests.get(
                            f"{base_url}/auth/me",
                            headers=headers,
                            timeout=10
                        )

                        me_success = me_response.status_code == 200
                        print(f"  {'✅' if me_success else '❌'} Protected endpoint - {me_response.status_code}")

                        api_tests.extend([
                            {'endpoint': '/auth/register', 'success': register_success},
                            {'endpoint': '/auth/login', 'success': login_success},
                            {'endpoint': '/auth/me', 'success': me_success}
                        ])

            except Exception as e:
                print(f"  ❌ Authentication test failed: {e}")
                api_tests.append({'endpoint': 'auth_flow', 'success': False, 'error': str(e)})

            overall_api_success = all(test.get('success', False) for test in api_tests)
            self.test_results['api_tests'] = {
                'success': overall_api_success,
                'tests': api_tests,
                'total_tests': len(api_tests),
                'passed_tests': sum(1 for test in api_tests if test.get('success', False))
            }

            return overall_api_success

        except Exception as e:
            print(f"❌ API tests failed: {e}")
            self.test_results['api_tests'] = {'success': False, 'error': str(e)}
            return False

    def run_performance_tests(self) -> bool:
        """Run basic performance tests"""
        try:
            print("\n⚡ Running performance tests...")
            import requests
            import time
            import threading

            base_url = "http://localhost:8000"

            # Response time test
            print("  Testing API response times...")
            response_times = []

            for i in range(5):
                start_time = time.time()
                response = requests.get(f"{base_url}/health/basic", timeout=10)
                duration = time.time() - start_time
                response_times.append(duration * 1000)  # Convert to ms

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            print(f"  Average response time: {avg_response_time:.0f}ms")
            print(f"  Max response time: {max_response_time:.0f}ms")

            # Concurrent requests test
            print("  Testing concurrent requests...")
            concurrent_results = []

            def make_request():
                try:
                    response = requests.get(f"{base_url}/health/basic", timeout=10)
                    concurrent_results.append(response.status_code == 200)
                except:
                    concurrent_results.append(False)

            threads = []
            for i in range(10):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            concurrent_success_rate = sum(concurrent_results) / len(concurrent_results) * 100
            print(f"  Concurrent request success rate: {concurrent_success_rate:.1f}%")

            performance_success = (
                avg_response_time < 1000 and  # Less than 1 second
                concurrent_success_rate >= 90  # At least 90% success
            )

            self.test_results['performance'] = {
                'success': performance_success,
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max_response_time,
                'concurrent_success_rate': concurrent_success_rate
            }

            return performance_success

        except Exception as e:
            print(f"❌ Performance tests failed: {e}")
            self.test_results['performance'] = {'success': False, 'error': str(e)}
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        try:
            print("\n🔄 Running integration tests...")

            # Test database connection
            from app.shared.database import check_db_connection
            db_success = check_db_connection()
            print(f"  {'✅' if db_success else '❌'} Database connection")

            # Test Redis connection
            import redis
            from app.config import settings
            try:
                r = redis.from_url(settings.redis_url)
                r.ping()
                redis_success = True
                print("  ✅ Redis connection")
            except:
                redis_success = False
                print("  ❌ Redis connection")

            # Test AI models
            try:
                import httpx
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{settings.ollama_url}/api/tags")
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        ai_success = len(models) >= 2
                        print(f"  {'✅' if ai_success else '❌'} AI models ({len(models)} available)")
                    else:
                        ai_success = False
                        print("  ❌ AI models")
            except:
                ai_success = False
                print("  ❌ AI models")

            integration_success = db_success and redis_success and ai_success
            self.test_results['integration'] = {
                'success': integration_success,
                'database': db_success,
                'redis': redis_success,
                'ai_models': ai_success
            }

            return integration_success

        except Exception as e:
            print(f"❌ Integration tests failed: {e}")
            self.test_results['integration'] = {'success': False, 'error': str(e)}
            return False

    def generate_test_report(self):
        """Generate comprehensive test report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("\n" + "="*80)
        print("SOCIAL SECURITY AI - COMPREHENSIVE TEST REPORT")
        print("="*80)
        print(f"Timestamp: {timestamp}")
        print(f"Overall Status: {'🟢 PASSED' if self.overall_success else '🔴 FAILED'}")
        print("-"*80)

        # Test summary
        total_test_categories = len(self.test_results)
        passed_categories = sum(1 for result in self.test_results.values() if result.get('success', False))

        print(f"Test Categories: {passed_categories}/{total_test_categories} passed")
        print()

        # Detailed results
        for category, results in self.test_results.items():
            success = results.get('success', False)
            status_icon = "🟢" if success else "🔴"

            print(f"{status_icon} {category.upper().replace('_', ' ')}: {'PASSED' if success else 'FAILED'}")

            if 'error' in results:
                print(f"   ❌ Error: {results['error']}")

            if 'duration' in results:
                print(f"   ⏱️  Duration: {results['duration']}")

            if category == 'api_tests' and 'tests' in results:
                print(f"   📊 API Tests: {results['passed_tests']}/{results['total_tests']} passed")

            if category == 'performance' and 'avg_response_time_ms' in results:
                print(f"   ⚡ Avg Response: {results['avg_response_time_ms']:.0f}ms")
                print(f"   🔄 Concurrent Success: {results['concurrent_success_rate']:.1f}%")

            print()

        print("-"*80)

        if self.overall_success:
            print("✅ ALL TESTS PASSED! System is ready for production.")
            print("\n🚀 Quick Access:")
            print("   📊 Dashboard: http://localhost:8005")
            print("   🔗 API Docs: http://localhost:8000/docs")
            print("   🏥 Health: http://localhost:8000/health")
        else:
            print("⚠️  SOME TESTS FAILED! Please review the issues above.")
            print("\n🔧 Troubleshooting:")
            print("   1. Check Docker services: docker compose ps")
            print("   2. Check logs: docker compose logs")
            print("   3. Restart system: docker compose restart")

        print("="*80)

    def run_all_tests(self):
        """Run all test categories"""
        print("🚀 Starting comprehensive test suite for Social Security AI System...")

        # Check prerequisites
        if not self.check_docker_services():
            print("❌ Docker services not ready. Please start the system first.")
            print("   Run: docker compose up -d")
            return False

        # Run test categories
        test_categories = [
            ("Health Check", self.run_health_check),
            ("Integration Tests", self.run_integration_tests),
            ("API Tests", self.run_api_tests),
            ("Performance Tests", self.run_performance_tests),
            ("Pytest Suite", self.run_pytest_tests)
        ]

        for category_name, test_function in test_categories:
            print(f"\n{'='*20} {category_name} {'='*20}")
            success = test_function()
            if not success:
                self.overall_success = False

        # Generate final report
        self.generate_test_report()

        return self.overall_success


def main():
    """Main test execution function"""
    runner = TestRunner()

    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

        if test_type == "health":
            success = runner.run_health_check()
        elif test_type == "api":
            success = runner.run_api_tests()
        elif test_type == "performance":
            success = runner.run_performance_tests()
        elif test_type == "integration":
            success = runner.run_integration_tests()
        elif test_type == "pytest":
            success = runner.run_pytest_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available types: health, api, performance, integration, pytest, all")
            sys.exit(1)

        sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()