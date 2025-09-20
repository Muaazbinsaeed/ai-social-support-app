#!/usr/bin/env python3
"""
Final Comprehensive Test Results Generator
Combines all test results and generates comprehensive report
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any


class FinalTestReporter:
    """Generate comprehensive test report"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.all_results = {
            "basic_api_tests": [],
            "edge_case_tests": [],
            "service_layer_tests": [],
            "performance_tests": [],
            "security_tests": []
        }

    def run_quick_verification_suite(self):
        """Run quick verification of all major functionalities"""
        print("🚀 Running Final Comprehensive Test Verification")
        print("=" * 60)

        # API Endpoint Tests
        self.test_all_endpoints()

        # Authentication Flow Tests
        self.test_authentication_flow()

        # Security Tests
        self.test_security_features()

        # Performance Tests
        self.test_performance_benchmarks()

        # Service Integration Tests
        self.test_service_integrations()

        # Generate final report
        self.generate_comprehensive_report()

    def test_all_endpoints(self):
        """Test all API endpoints"""
        endpoints = [
            ("/", "GET", "Root endpoint"),
            ("/health/basic", "GET", "Basic health check"),
            ("/health/", "GET", "Comprehensive health check"),
            ("/health/database", "GET", "Database health check"),
            ("/docs", "GET", "API documentation"),
            ("/openapi.json", "GET", "OpenAPI schema")
        ]

        passed = 0
        total = len(endpoints)

        for endpoint, method, description in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    passed += 1
                    print(f"✅ {description}: {response.status_code}")
                else:
                    print(f"❌ {description}: {response.status_code}")
            except Exception as e:
                print(f"❌ {description}: Error - {str(e)}")

        self.all_results["basic_api_tests"].append({
            "category": "API Endpoints",
            "passed": passed,
            "total": total,
            "success_rate": (passed/total)*100 if total > 0 else 0
        })

    def test_authentication_flow(self):
        """Test complete authentication flow"""
        print("\n🔐 Testing Authentication Flow...")

        auth_tests = []

        # Test user registration
        try:
            user_data = {
                "username": f"final_test_{int(time.time())}",
                "email": f"final_test_{int(time.time())}@example.com",
                "password": "FinalTest123!",
                "full_name": "Final Test User"
            }

            reg_response = self.session.post(
                f"{self.base_url}/auth/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )

            if reg_response.status_code == 201:
                auth_tests.append(("User Registration", True))
                print("✅ User Registration: Success")

                # Test login
                login_response = self.session.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "username": user_data["username"],
                        "password": user_data["password"]
                    },
                    headers={"Content-Type": "application/json"}
                )

                if login_response.status_code == 200:
                    auth_tests.append(("User Login", True))
                    print("✅ User Login: Success")

                    token_data = login_response.json()
                    token = token_data["access_token"]

                    # Test protected endpoint access
                    me_response = self.session.get(
                        f"{self.base_url}/auth/me",
                        headers={"Authorization": f"Bearer {token}"}
                    )

                    if me_response.status_code == 200:
                        auth_tests.append(("Protected Endpoint Access", True))
                        print("✅ Protected Endpoint Access: Success")
                    else:
                        auth_tests.append(("Protected Endpoint Access", False))
                        print("❌ Protected Endpoint Access: Failed")

                    # Test token refresh
                    refresh_response = self.session.post(
                        f"{self.base_url}/auth/refresh",
                        headers={"Authorization": f"Bearer {token}"}
                    )

                    if refresh_response.status_code == 200:
                        auth_tests.append(("Token Refresh", True))
                        print("✅ Token Refresh: Success")
                    else:
                        auth_tests.append(("Token Refresh", False))
                        print("❌ Token Refresh: Failed")

                else:
                    auth_tests.append(("User Login", False))
                    print("❌ User Login: Failed")
            else:
                auth_tests.append(("User Registration", False))
                print("❌ User Registration: Failed")

        except Exception as e:
            print(f"❌ Authentication Flow: Error - {str(e)}")

        passed_auth = sum(1 for _, success in auth_tests if success)
        total_auth = len(auth_tests)

        self.all_results["basic_api_tests"].append({
            "category": "Authentication Flow",
            "passed": passed_auth,
            "total": total_auth,
            "success_rate": (passed_auth/total_auth)*100 if total_auth > 0 else 0,
            "tests": auth_tests
        })

    def test_security_features(self):
        """Test security features"""
        print("\n🛡️ Testing Security Features...")

        security_tests = []

        # Test unauthorized access
        try:
            unauth_response = self.session.get(f"{self.base_url}/auth/me")
            if unauth_response.status_code in [401, 403]:
                security_tests.append(("Unauthorized Access Blocked", True))
                print("✅ Unauthorized Access Blocked: Success")
            else:
                security_tests.append(("Unauthorized Access Blocked", False))
                print("❌ Unauthorized Access Blocked: Failed")
        except:
            security_tests.append(("Unauthorized Access Blocked", False))

        # Test content type validation
        try:
            invalid_content_response = self.session.post(
                f"{self.base_url}/auth/login",
                data="invalid data",
                headers={"Content-Type": "text/plain"}
            )
            if invalid_content_response.status_code == 415:
                security_tests.append(("Content Type Validation", True))
                print("✅ Content Type Validation: Success")
            else:
                security_tests.append(("Content Type Validation", False))
                print("❌ Content Type Validation: Failed")
        except:
            security_tests.append(("Content Type Validation", False))

        # Test input validation
        try:
            invalid_input_response = self.session.post(
                f"{self.base_url}/auth/register",
                json={"username": "a", "email": "invalid", "password": "123"},
                headers={"Content-Type": "application/json"}
            )
            if invalid_input_response.status_code == 422:
                security_tests.append(("Input Validation", True))
                print("✅ Input Validation: Success")
            else:
                security_tests.append(("Input Validation", False))
                print("❌ Input Validation: Failed")
        except:
            security_tests.append(("Input Validation", False))

        passed_security = sum(1 for _, success in security_tests if success)
        total_security = len(security_tests)

        self.all_results["security_tests"].append({
            "category": "Security Features",
            "passed": passed_security,
            "total": total_security,
            "success_rate": (passed_security/total_security)*100 if total_security > 0 else 0,
            "tests": security_tests
        })

    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n⚡ Testing Performance Benchmarks...")

        performance_tests = []

        # Test API response time
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health/basic")
            response_time = time.time() - start_time

            if response.status_code == 200 and response_time < 1.0:
                performance_tests.append(("API Response Time < 1s", True))
                print(f"✅ API Response Time: {response_time*1000:.1f}ms")
            else:
                performance_tests.append(("API Response Time < 1s", False))
                print(f"❌ API Response Time: {response_time*1000:.1f}ms")
        except:
            performance_tests.append(("API Response Time < 1s", False))

        # Test concurrent requests
        try:
            import threading
            results = []

            def make_request():
                try:
                    resp = requests.get(f"{self.base_url}/health/basic", timeout=5)
                    results.append(resp.status_code == 200)
                except:
                    results.append(False)

            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join(timeout=10)

            concurrent_success = sum(results) / len(results) if results else 0
            if concurrent_success >= 0.8:  # 80% success rate
                performance_tests.append(("Concurrent Requests", True))
                print(f"✅ Concurrent Requests: {concurrent_success*100:.1f}% success")
            else:
                performance_tests.append(("Concurrent Requests", False))
                print(f"❌ Concurrent Requests: {concurrent_success*100:.1f}% success")

        except:
            performance_tests.append(("Concurrent Requests", False))

        passed_perf = sum(1 for _, success in performance_tests if success)
        total_perf = len(performance_tests)

        self.all_results["performance_tests"].append({
            "category": "Performance Benchmarks",
            "passed": passed_perf,
            "total": total_perf,
            "success_rate": (passed_perf/total_perf)*100 if total_perf > 0 else 0,
            "tests": performance_tests
        })

    def test_service_integrations(self):
        """Test service integrations"""
        print("\n🔗 Testing Service Integrations...")

        integration_tests = []

        try:
            health_response = self.session.get(f"{self.base_url}/health/")

            if health_response.status_code == 200:
                health_data = health_response.json()
                services = health_data.get("services", {})

                service_checks = [
                    ("database", "Database"),
                    ("redis", "Redis Cache"),
                    ("ollama", "AI Models"),
                    ("qdrant", "Vector Database"),
                    ("celery_workers", "Background Workers")
                ]

                for service_key, service_name in service_checks:
                    if service_key in services:
                        service_status = services[service_key].get("status", "unknown")
                        if service_status in ["healthy", "degraded"]:
                            integration_tests.append((service_name, True))
                            print(f"✅ {service_name}: {service_status}")
                        else:
                            integration_tests.append((service_name, False))
                            print(f"❌ {service_name}: {service_status}")
                    else:
                        integration_tests.append((service_name, False))
                        print(f"❌ {service_name}: Not found")

            else:
                print(f"❌ Health check failed: {health_response.status_code}")

        except Exception as e:
            print(f"❌ Service Integration Test Error: {str(e)}")

        passed_integration = sum(1 for _, success in integration_tests if success)
        total_integration = len(integration_tests)

        self.all_results["service_layer_tests"].append({
            "category": "Service Integrations",
            "passed": passed_integration,
            "total": total_integration,
            "success_rate": (passed_integration/total_integration)*100 if total_integration > 0 else 0,
            "tests": integration_tests
        })

    def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 60)

        total_tests = 0
        total_passed = 0

        # Calculate overall statistics
        for category_results in self.all_results.values():
            for result in category_results:
                total_tests += result["total"]
                total_passed += result["passed"]

        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        print(f"\n🎯 OVERALL TEST RESULTS:")
        print(f"📈 Success Rate: {overall_success_rate:.1f}% ({total_passed}/{total_tests})")
        print(f"✅ Passed: {total_passed}")
        print(f"❌ Failed: {total_tests - total_passed}")

        print(f"\n📋 CATEGORY BREAKDOWN:")
        for category_name, category_results in self.all_results.items():
            if category_results:
                for result in category_results:
                    print(f"   {result['category']}: {result['success_rate']:.1f}% ({result['passed']}/{result['total']})")

        # Overall system status
        print(f"\n🎯 SYSTEM STATUS:")
        if overall_success_rate >= 95:
            status = "🟢 EXCELLENT"
        elif overall_success_rate >= 85:
            status = "🟡 GOOD"
        elif overall_success_rate >= 70:
            status = "🟠 FAIR"
        else:
            status = "🔴 POOR"

        print(f"   {status} ({overall_success_rate:.1f}%)")

        # Save detailed results
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_success_rate": overall_success_rate,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_tests - total_passed,
            "category_results": self.all_results,
            "system_status": status,
            "recommendations": self.generate_recommendations(overall_success_rate)
        }

        with open("final_comprehensive_test_results.json", "w") as f:
            json.dump(final_report, f, indent=2, default=str)

        print(f"\n📄 Final report saved to: final_comprehensive_test_results.json")

        return final_report

    def generate_recommendations(self, success_rate: float) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        if success_rate >= 95:
            recommendations.append("System is production-ready with excellent performance")
            recommendations.append("Continue monitoring and maintain current quality standards")
        elif success_rate >= 85:
            recommendations.append("System is largely functional with minor issues to address")
            recommendations.append("Review failed tests and implement fixes for edge cases")
        elif success_rate >= 70:
            recommendations.append("System has significant issues that should be addressed")
            recommendations.append("Focus on fixing failed critical functionality")
        else:
            recommendations.append("System requires major fixes before production deployment")
            recommendations.append("Review all failed tests and implement comprehensive fixes")

        recommendations.append("Continue comprehensive testing for new features")
        recommendations.append("Implement automated testing in CI/CD pipeline")

        return recommendations


def main():
    """Main function"""
    reporter = FinalTestReporter()

    # Check if API is accessible
    try:
        response = requests.get("http://localhost:8000/health/basic", timeout=5)
        if response.status_code != 200:
            print("❌ API is not accessible.")
            return None
    except:
        print("❌ Cannot connect to API.")
        return None

    # Run comprehensive tests
    return reporter.run_quick_verification_suite()


if __name__ == "__main__":
    main()