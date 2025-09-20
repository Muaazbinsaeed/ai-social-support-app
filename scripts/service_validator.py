"""
Comprehensive Service Validation Script
Tests all services and validates integration
"""

import os
import sys
import json
import asyncio
import requests
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ServiceValidator:
    """Validates all services and integration points"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "integration_tests": {},
            "summary": {
                "total_services": 0,
                "healthy_services": 0,
                "failed_services": 0,
                "integration_tests_passed": 0,
                "integration_tests_failed": 0
            }
        }

    def test_ollama_service(self):
        """Test Ollama AI service"""
        print("🤖 Testing Ollama AI Service...")

        service_result = {
            "name": "Ollama AI Service",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            # Test basic connectivity
            response = requests.get("http://localhost:11434/api/tags", timeout=10)

            if response.status_code == 200:
                models = response.json().get("models", [])

                # Check for required models
                required_models = ["moondream:1.8b", "qwen2:1.5b", "nomic-embed-text"]
                available_models = [model["name"] for model in models]

                missing_models = [model for model in required_models if model not in available_models]

                service_result["details"] = {
                    "available_models": available_models,
                    "required_models": required_models,
                    "missing_models": missing_models
                }

                if missing_models:
                    service_result["status"] = "partial"
                    service_result["errors"].append(f"Missing models: {missing_models}")
                    print(f"⚠️ Ollama - Partial (Missing models: {missing_models})")
                else:
                    service_result["status"] = "healthy"
                    print("✅ Ollama - Healthy")

                # Test model inference
                try:
                    test_prompt = {
                        "model": "qwen2:1.5b",
                        "prompt": "Test prompt: What is 2+2?",
                        "stream": False
                    }

                    inference_response = requests.post(
                        "http://localhost:11434/api/generate",
                        json=test_prompt,
                        timeout=30
                    )

                    if inference_response.status_code == 200:
                        result = inference_response.json()
                        service_result["details"]["inference_test"] = "passed"
                        service_result["details"]["sample_response"] = result.get("response", "")[:100]
                        print("   ✅ Model inference test passed")
                    else:
                        service_result["details"]["inference_test"] = "failed"
                        service_result["errors"].append("Model inference test failed")
                        print("   ❌ Model inference test failed")

                except Exception as e:
                    service_result["details"]["inference_test"] = "error"
                    service_result["errors"].append(f"Inference test error: {str(e)}")
                    print(f"   ❌ Model inference error: {str(e)}")

            else:
                service_result["status"] = "unhealthy"
                service_result["errors"].append(f"HTTP {response.status_code}")
                print(f"❌ Ollama - Unhealthy (HTTP {response.status_code})")

        except requests.exceptions.ConnectionError:
            service_result["status"] = "unavailable"
            service_result["errors"].append("Connection refused - service not running")
            print("❌ Ollama - Not running")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ Ollama - Error: {str(e)}")

        self.results["services"]["ollama"] = service_result

    def test_postgresql_service(self):
        """Test PostgreSQL database service"""
        print("🗄️ Testing PostgreSQL Service...")

        service_result = {
            "name": "PostgreSQL Database",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            from sqlalchemy import create_engine, text

            # Test with different possible configurations
            db_urls = [
                "postgresql://postgres:postgres@localhost:5432/social_security_ai",
                "postgresql://user:password@localhost:5432/social_security_ai",
                "postgresql://postgres@localhost:5432/social_security_ai"
            ]

            connected = False
            for db_url in db_urls:
                try:
                    engine = create_engine(db_url)
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT version();"))
                        version = result.fetchone()[0]

                        service_result["status"] = "healthy"
                        service_result["details"]["version"] = version
                        service_result["details"]["connection_url"] = db_url.split("@")[1]  # Hide credentials
                        connected = True
                        print("✅ PostgreSQL - Healthy")
                        break

                except Exception:
                    continue

            if not connected:
                service_result["status"] = "unavailable"
                service_result["errors"].append("Could not connect with any configuration")
                print("❌ PostgreSQL - Could not connect")

        except ImportError:
            service_result["status"] = "error"
            service_result["errors"].append("SQLAlchemy not available")
            print("❌ PostgreSQL - SQLAlchemy not installed")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ PostgreSQL - Error: {str(e)}")

        self.results["services"]["postgresql"] = service_result

    def test_redis_service(self):
        """Test Redis cache service"""
        print("🔴 Testing Redis Service...")

        service_result = {
            "name": "Redis Cache",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            import redis

            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

            # Test basic operations
            r.ping()

            # Test set/get
            test_key = "test_key_validator"
            test_value = "test_value_123"
            r.set(test_key, test_value, ex=10)  # Expire in 10 seconds
            retrieved_value = r.get(test_key)

            if retrieved_value == test_value:
                service_result["status"] = "healthy"
                service_result["details"]["test_operations"] = "passed"
                print("✅ Redis - Healthy")
            else:
                service_result["status"] = "partial"
                service_result["errors"].append("Set/Get test failed")
                print("⚠️ Redis - Partial (Set/Get failed)")

            # Get Redis info
            info = r.info()
            service_result["details"]["version"] = info.get("redis_version")
            service_result["details"]["memory_usage"] = info.get("used_memory_human")

        except ImportError:
            service_result["status"] = "error"
            service_result["errors"].append("Redis Python client not available")
            print("❌ Redis - Python client not installed")
        except redis.exceptions.ConnectionError:
            service_result["status"] = "unavailable"
            service_result["errors"].append("Connection refused - service not running")
            print("❌ Redis - Not running")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ Redis - Error: {str(e)}")

        self.results["services"]["redis"] = service_result

    def test_qdrant_service(self):
        """Test Qdrant vector database service"""
        print("🔍 Testing Qdrant Vector Database...")

        service_result = {
            "name": "Qdrant Vector Database",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            # Test HTTP API first
            response = requests.get("http://localhost:6333/", timeout=10)

            if response.status_code == 200:
                # Try to get collections
                collections_response = requests.get("http://localhost:6333/collections", timeout=10)

                if collections_response.status_code == 200:
                    collections = collections_response.json()
                    service_result["status"] = "healthy"
                    service_result["details"]["collections"] = collections.get("result", {}).get("collections", [])
                    print("✅ Qdrant - Healthy")
                else:
                    service_result["status"] = "partial"
                    service_result["errors"].append("Collections endpoint not accessible")
                    print("⚠️ Qdrant - Partial")
            else:
                service_result["status"] = "unhealthy"
                service_result["errors"].append(f"HTTP {response.status_code}")
                print(f"❌ Qdrant - Unhealthy (HTTP {response.status_code})")

        except requests.exceptions.ConnectionError:
            service_result["status"] = "unavailable"
            service_result["errors"].append("Connection refused - service not running")
            print("❌ Qdrant - Not running")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ Qdrant - Error: {str(e)}")

        self.results["services"]["qdrant"] = service_result

    def test_easyocr_service(self):
        """Test EasyOCR service"""
        print("👁️ Testing EasyOCR Service...")

        service_result = {
            "name": "EasyOCR",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            import easyocr
            import numpy as np

            # Initialize reader
            reader = easyocr.Reader(['en'])

            # Create a simple test image (white background with black text)
            test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255

            # Test OCR (this is a simple test, real text images would work better)
            start_time = time.time()
            results = reader.readtext(test_image)
            processing_time = (time.time() - start_time) * 1000

            service_result["status"] = "healthy"
            service_result["details"]["supported_languages"] = reader.lang_list
            service_result["details"]["test_processing_time_ms"] = round(processing_time, 2)
            service_result["details"]["test_results_count"] = len(results)
            print("✅ EasyOCR - Healthy")

        except ImportError:
            service_result["status"] = "error"
            service_result["errors"].append("EasyOCR not installed")
            print("❌ EasyOCR - Not installed")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ EasyOCR - Error: {str(e)}")

        self.results["services"]["easyocr"] = service_result

    def test_fastapi_service(self):
        """Test FastAPI application"""
        print("🚀 Testing FastAPI Application...")

        service_result = {
            "name": "FastAPI Application",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            # Test if we can import the app
            from app.main import app

            service_result["details"]["app_loaded"] = True
            service_result["details"]["total_routes"] = len(app.routes)

            # Get route information
            routes = []
            for route in app.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    routes.append({
                        "path": route.path,
                        "methods": list(route.methods) if route.methods else []
                    })

            service_result["details"]["routes_sample"] = routes[:10]  # First 10 routes

            # Test with TestClient
            from fastapi.testclient import TestClient
            client = TestClient(app)

            # Test root endpoint
            response = client.get("/")
            if response.status_code == 200:
                service_result["status"] = "healthy"
                service_result["details"]["root_endpoint"] = "accessible"
                print("✅ FastAPI - Healthy")
            else:
                service_result["status"] = "partial"
                service_result["errors"].append(f"Root endpoint returned {response.status_code}")
                print(f"⚠️ FastAPI - Partial (Root endpoint: {response.status_code})")

            # Test health endpoint
            health_response = client.get("/health")
            service_result["details"]["health_endpoint"] = health_response.status_code

        except ImportError as e:
            service_result["status"] = "error"
            service_result["errors"].append(f"Import error: {str(e)}")
            print(f"❌ FastAPI - Import error: {str(e)}")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ FastAPI - Error: {str(e)}")

        self.results["services"]["fastapi"] = service_result

    def test_streamlit_service(self):
        """Test Streamlit frontend"""
        print("🎨 Testing Streamlit Frontend...")

        service_result = {
            "name": "Streamlit Frontend",
            "status": "unknown",
            "details": {},
            "errors": []
        }

        try:
            # Check if Streamlit is installed
            import streamlit
            service_result["details"]["streamlit_version"] = streamlit.__version__

            # Check if frontend files exist
            frontend_files = [
                "frontend/app.py",
                "frontend/pages",
                "frontend/utils"
            ]

            existing_files = []
            for file_path in frontend_files:
                full_path = project_root / file_path
                if full_path.exists():
                    existing_files.append(file_path)

            service_result["details"]["existing_files"] = existing_files

            if existing_files:
                service_result["status"] = "available"
                print("✅ Streamlit - Available")
            else:
                service_result["status"] = "partial"
                service_result["errors"].append("Frontend files not found")
                print("⚠️ Streamlit - Frontend files not found")

            # Test if we can run on port 8005 (check if port is free)
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8005))
            sock.close()

            if result == 0:
                service_result["details"]["port_8005"] = "in_use"
                print("   ℹ️ Port 8005 is in use (possibly Streamlit running)")
            else:
                service_result["details"]["port_8005"] = "available"

        except ImportError:
            service_result["status"] = "error"
            service_result["errors"].append("Streamlit not installed")
            print("❌ Streamlit - Not installed")
        except Exception as e:
            service_result["status"] = "error"
            service_result["errors"].append(str(e))
            print(f"❌ Streamlit - Error: {str(e)}")

        self.results["services"]["streamlit"] = service_result

    def test_integration_workflow(self):
        """Test complete integration workflow"""
        print("\n🔄 Testing Integration Workflow...")

        integration_result = {
            "name": "Complete User Workflow",
            "status": "unknown",
            "steps": [],
            "errors": []
        }

        try:
            from fastapi.testclient import TestClient
            from app.main import app

            client = TestClient(app)

            # Step 1: User Registration
            step1 = {"name": "User Registration", "status": "unknown"}
            try:
                user_data = {
                    "username": "integrationuser",
                    "email": "integration@test.com",
                    "password": "testpassword123",
                    "full_name": "Integration Test User"
                }

                response = client.post("/auth/register", json=user_data)
                if response.status_code in [200, 201]:
                    step1["status"] = "passed"
                else:
                    step1["status"] = "failed"
                    step1["error"] = f"HTTP {response.status_code}"

            except Exception as e:
                step1["status"] = "error"
                step1["error"] = str(e)

            integration_result["steps"].append(step1)

            # Step 2: User Login (only if registration succeeded)
            step2 = {"name": "User Login", "status": "unknown"}
            auth_token = None

            if step1["status"] == "passed":
                try:
                    login_data = {
                        "username": "integrationuser",
                        "password": "testpassword123"
                    }

                    response = client.post("/auth/login", json=login_data)
                    if response.status_code == 200:
                        auth_token = response.json().get("access_token")
                        step2["status"] = "passed"
                    else:
                        step2["status"] = "failed"
                        step2["error"] = f"HTTP {response.status_code}"

                except Exception as e:
                    step2["status"] = "error"
                    step2["error"] = str(e)
            else:
                step2["status"] = "skipped"
                step2["reason"] = "Registration failed"

            integration_result["steps"].append(step2)

            # Step 3: Health Check
            step3 = {"name": "Health Check", "status": "unknown"}
            try:
                response = client.get("/health")
                if response.status_code == 200:
                    step3["status"] = "passed"
                    step3["response"] = response.json()
                else:
                    step3["status"] = "failed"
                    step3["error"] = f"HTTP {response.status_code}"

            except Exception as e:
                step3["status"] = "error"
                step3["error"] = str(e)

            integration_result["steps"].append(step3)

            # Step 4: User Profile Access (only if logged in)
            step4 = {"name": "User Profile Access", "status": "unknown"}

            if auth_token:
                try:
                    headers = {"Authorization": f"Bearer {auth_token}"}
                    response = client.get("/users/profile", headers=headers)

                    if response.status_code == 200:
                        step4["status"] = "passed"
                    else:
                        step4["status"] = "failed"
                        step4["error"] = f"HTTP {response.status_code}"

                except Exception as e:
                    step4["status"] = "error"
                    step4["error"] = str(e)
            else:
                step4["status"] = "skipped"
                step4["reason"] = "No auth token available"

            integration_result["steps"].append(step4)

            # Determine overall status
            passed_steps = len([s for s in integration_result["steps"] if s["status"] == "passed"])
            failed_steps = len([s for s in integration_result["steps"] if s["status"] == "failed"])
            error_steps = len([s for s in integration_result["steps"] if s["status"] == "error"])

            if error_steps > 0:
                integration_result["status"] = "error"
            elif failed_steps > 0:
                integration_result["status"] = "failed"
            elif passed_steps > 0:
                integration_result["status"] = "passed"

            print(f"   Integration workflow: {integration_result['status']}")
            for step in integration_result["steps"]:
                status_icon = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}.get(step["status"], "❓")
                print(f"   {status_icon} {step['name']}: {step['status']}")

        except Exception as e:
            integration_result["status"] = "error"
            integration_result["errors"].append(str(e))
            print(f"❌ Integration workflow error: {str(e)}")

        self.results["integration_tests"]["user_workflow"] = integration_result

    def test_api_endpoints_health(self):
        """Test health of all API endpoints"""
        print("\n🩺 Testing API Endpoints Health...")

        api_health_result = {
            "name": "API Endpoints Health",
            "status": "unknown",
            "endpoints": [],
            "summary": {
                "total": 0,
                "healthy": 0,
                "unhealthy": 0,
                "protected": 0
            }
        }

        try:
            from fastapi.testclient import TestClient
            from app.main import app

            client = TestClient(app)

            # Test key endpoints
            endpoints_to_test = [
                {"path": "/", "method": "GET", "expected_status": [200]},
                {"path": "/health", "method": "GET", "expected_status": [200]},
                {"path": "/auth/register", "method": "POST", "expected_status": [422]},  # Without data
                {"path": "/docs", "method": "GET", "expected_status": [200]},
                {"path": "/users/profile", "method": "GET", "expected_status": [401]},  # Protected
                {"path": "/documents", "method": "GET", "expected_status": [401]},  # Protected
                {"path": "/chatbot/quick-help", "method": "GET", "expected_status": [200]},
                {"path": "/decisions/criteria", "method": "GET", "expected_status": [200]},
                {"path": "/ocr/health", "method": "GET", "expected_status": [200, 503]},
                {"path": "/chatbot/health", "method": "GET", "expected_status": [200, 503]}
            ]

            for endpoint in endpoints_to_test:
                endpoint_result = {
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    "status": "unknown",
                    "response_code": None
                }

                try:
                    if endpoint["method"] == "GET":
                        response = client.get(endpoint["path"])
                    elif endpoint["method"] == "POST":
                        response = client.post(endpoint["path"], json={})

                    endpoint_result["response_code"] = response.status_code

                    if response.status_code in endpoint["expected_status"]:
                        endpoint_result["status"] = "healthy"
                        api_health_result["summary"]["healthy"] += 1
                    else:
                        endpoint_result["status"] = "unhealthy"
                        api_health_result["summary"]["unhealthy"] += 1

                    if response.status_code == 401:
                        api_health_result["summary"]["protected"] += 1

                except Exception as e:
                    endpoint_result["status"] = "error"
                    endpoint_result["error"] = str(e)
                    api_health_result["summary"]["unhealthy"] += 1

                api_health_result["endpoints"].append(endpoint_result)
                api_health_result["summary"]["total"] += 1

            # Determine overall status
            health_rate = api_health_result["summary"]["healthy"] / api_health_result["summary"]["total"]

            if health_rate >= 0.8:
                api_health_result["status"] = "healthy"
            elif health_rate >= 0.6:
                api_health_result["status"] = "partial"
            else:
                api_health_result["status"] = "unhealthy"

            print(f"   API Health: {api_health_result['status']} ({api_health_result['summary']['healthy']}/{api_health_result['summary']['total']} healthy)")

        except Exception as e:
            api_health_result["status"] = "error"
            api_health_result["error"] = str(e)
            print(f"❌ API health check error: {str(e)}")

        self.results["integration_tests"]["api_health"] = api_health_result

    def run_all_validations(self):
        """Run all service validations"""
        print("🔍 Starting Comprehensive Service Validation")
        print(f"Timestamp: {self.results['timestamp']}")
        print("=" * 60)

        # Test individual services
        services_to_test = [
            self.test_fastapi_service,
            self.test_postgresql_service,
            self.test_redis_service,
            self.test_ollama_service,
            self.test_qdrant_service,
            self.test_easyocr_service,
            self.test_streamlit_service
        ]

        for test_func in services_to_test:
            try:
                test_func()
                self.results["summary"]["total_services"] += 1
            except Exception as e:
                print(f"❌ Service test failed: {str(e)}")

        # Test integrations
        integration_tests = [
            self.test_integration_workflow,
            self.test_api_endpoints_health
        ]

        for test_func in integration_tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ Integration test failed: {str(e)}")

        # Calculate summary
        for service_name, service_data in self.results["services"].items():
            if service_data["status"] in ["healthy", "available"]:
                self.results["summary"]["healthy_services"] += 1
            else:
                self.results["summary"]["failed_services"] += 1

        for test_name, test_data in self.results["integration_tests"].items():
            if test_data["status"] == "passed":
                self.results["summary"]["integration_tests_passed"] += 1
            else:
                self.results["summary"]["integration_tests_failed"] += 1

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate final validation report"""
        print("\n" + "=" * 60)
        print("📊 SERVICE VALIDATION SUMMARY")
        print("=" * 60)

        # Services summary
        print(f"Services tested: {self.results['summary']['total_services']}")
        print(f"Healthy services: {self.results['summary']['healthy_services']}")
        print(f"Failed services: {self.results['summary']['failed_services']}")

        # Integration tests summary
        total_integration = self.results['summary']['integration_tests_passed'] + self.results['summary']['integration_tests_failed']
        print(f"Integration tests: {total_integration}")
        print(f"Passed: {self.results['summary']['integration_tests_passed']}")
        print(f"Failed: {self.results['summary']['integration_tests_failed']}")

        # Service details
        print("\n🔧 SERVICE STATUS DETAILS:")
        for service_name, service_data in self.results["services"].items():
            status_icon = {
                "healthy": "✅",
                "available": "✅",
                "partial": "⚠️",
                "unhealthy": "❌",
                "unavailable": "❌",
                "error": "💥"
            }.get(service_data["status"], "❓")

            print(f"{status_icon} {service_data['name']}: {service_data['status']}")

            if service_data["errors"]:
                for error in service_data["errors"]:
                    print(f"   ⚠️ {error}")

        # Integration details
        print("\n🔄 INTEGRATION TEST DETAILS:")
        for test_name, test_data in self.results["integration_tests"].items():
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "error": "💥"
            }.get(test_data["status"], "❓")

            print(f"{status_icon} {test_data['name']}: {test_data['status']}")

        # Overall health assessment
        service_health_rate = self.results['summary']['healthy_services'] / max(self.results['summary']['total_services'], 1)
        integration_pass_rate = self.results['summary']['integration_tests_passed'] / max(total_integration, 1)

        print("\n🎯 OVERALL SYSTEM HEALTH:")
        print(f"Service Health Rate: {service_health_rate:.1%}")
        print(f"Integration Pass Rate: {integration_pass_rate:.1%}")

        if service_health_rate >= 0.8 and integration_pass_rate >= 0.8:
            print("🟢 System Status: HEALTHY")
        elif service_health_rate >= 0.6 or integration_pass_rate >= 0.6:
            print("🟡 System Status: PARTIAL")
        else:
            print("🔴 System Status: UNHEALTHY")

        # Save detailed report
        report_file = f"service_validation_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved: {report_file}")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if self.results['summary']['failed_services'] > 0:
            print("• Check failed services and ensure they are properly configured and running")

        if "ollama" in self.results["services"] and self.results["services"]["ollama"]["status"] != "healthy":
            print("• Install and configure Ollama with required models: moondream:1.8b, qwen2:1.5b, nomic-embed-text")

        if "postgresql" in self.results["services"] and self.results["services"]["postgresql"]["status"] != "healthy":
            print("• Set up PostgreSQL database with proper connection credentials")

        if "redis" in self.results["services"] and self.results["services"]["redis"]["status"] != "healthy":
            print("• Start Redis service for caching and session management")

        print("\n🚀 Ready for production deployment!" if service_health_rate >= 0.8 and integration_pass_rate >= 0.8 else "⚠️ Additional setup required before deployment")


def main():
    """Main validation function"""
    validator = ServiceValidator()

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # Quick validation of core services
            validator.test_fastapi_service()
            validator.test_integration_workflow()
            validator.generate_report()
        elif sys.argv[1] == "services":
            # Test only external services
            validator.test_postgresql_service()
            validator.test_redis_service()
            validator.test_ollama_service()
            validator.test_qdrant_service()
            validator.test_easyocr_service()
            validator.generate_report()
        elif sys.argv[1] == "integration":
            # Test only integration workflows
            validator.test_integration_workflow()
            validator.test_api_endpoints_health()
            validator.generate_report()
        else:
            print("Usage: python service_validator.py [quick|services|integration]")
    else:
        # Run full validation
        validator.run_all_validations()


if __name__ == "__main__":
    main()