#!/usr/bin/env python3
"""
API Coverage Report Generator
Generates comprehensive coverage report for all API endpoints
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import aiohttp


class APICoverageAnalyzer:
    """Analyzes and reports on API coverage"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = None
        self.coverage_data = {
            "timestamp": datetime.now().isoformat(),
            "total_endpoints": 0,
            "tested_endpoints": 0,
            "coverage_percentage": 0,
            "modules": {},
            "endpoints": {}
        }

    async def setup(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cleanup(self):
        """Cleanup session"""
        if self.session:
            await self.session.close()

    async def get_openapi_spec(self):
        """Get OpenAPI specification from server"""
        try:
            async with self.session.get(f"{self.base_url}/openapi.json") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Failed to get OpenAPI spec: {e}")
        return None

    def analyze_endpoints(self, openapi_spec: Dict[str, Any]):
        """Analyze all endpoints from OpenAPI spec"""
        if not openapi_spec or "paths" not in openapi_spec:
            return

        endpoints = {}
        modules = {}

        for path, methods in openapi_spec["paths"].items():
            for method, spec in methods.items():
                endpoint_key = f"{method.upper()} {path}"

                # Determine module based on path
                module = self._determine_module(path)

                # Extract endpoint information
                endpoint_info = {
                    "method": method.upper(),
                    "path": path,
                    "module": module,
                    "summary": spec.get("summary", ""),
                    "description": spec.get("description", ""),
                    "tags": spec.get("tags", []),
                    "parameters": len(spec.get("parameters", [])),
                    "requires_auth": self._requires_auth(spec),
                    "request_body": bool(spec.get("requestBody")),
                    "responses": list(spec.get("responses", {}).keys())
                }

                endpoints[endpoint_key] = endpoint_info

                # Group by module
                if module not in modules:
                    modules[module] = {
                        "name": module,
                        "endpoints": [],
                        "total": 0,
                        "tested": 0,
                        "coverage": 0
                    }

                modules[module]["endpoints"].append(endpoint_key)
                modules[module]["total"] += 1

        self.coverage_data["endpoints"] = endpoints
        self.coverage_data["modules"] = modules
        self.coverage_data["total_endpoints"] = len(endpoints)

    def _determine_module(self, path: str) -> str:
        """Determine module based on path"""
        if path == "/":
            return "Root"
        elif path.startswith("/health"):
            return "Health"
        elif path.startswith("/auth"):
            return "Authentication"
        elif path.startswith("/documents") and not path.startswith("/document-management"):
            return "Document Upload"
        elif path.startswith("/document-management"):
            return "Document Management"
        elif path.startswith("/workflow"):
            return "Workflow"
        elif path.startswith("/applications"):
            return "Applications"
        elif path.startswith("/analysis"):
            return "AI Analysis"
        elif path.startswith("/ocr"):
            return "OCR Processing"
        elif path.startswith("/decisions"):
            return "Decision Making"
        elif path.startswith("/chatbot"):
            return "Chatbot"
        elif path.startswith("/users"):
            return "User Management"
        else:
            return "Other"

    def _requires_auth(self, spec: Dict[str, Any]) -> bool:
        """Check if endpoint requires authentication"""
        security = spec.get("security", [])
        return bool(security)

    async def test_endpoint_availability(self, endpoint: Dict[str, Any]) -> bool:
        """Test if endpoint is available"""
        try:
            method = endpoint["method"]
            path = endpoint["path"]
            url = f"{self.base_url}{path}"

            # For parametrized paths, use dummy values
            if "{" in path:
                path = path.replace("{application_id}", "dummy-id")
                path = path.replace("{document_id}", "dummy-id")
                path = path.replace("{user_id}", "dummy-id")
                path = path.replace("{session_id}", "dummy-id")
                path = path.replace("{decision_id}", "dummy-id")
                url = f"{self.base_url}{path}"

            async with self.session.request(method, url) as response:
                # Accept any response that's not a connection error
                return True
        except Exception:
            return False

    async def generate_coverage_report(self):
        """Generate comprehensive coverage report"""
        await self.setup()

        try:
            # Get OpenAPI specification
            openapi_spec = await self.get_openapi_spec()
            if not openapi_spec:
                print("❌ Failed to get API specification")
                return None

            # Analyze endpoints
            self.analyze_endpoints(openapi_spec)

            # Test endpoint availability
            print("🔍 Testing endpoint availability...")
            for endpoint_key, endpoint_info in self.coverage_data["endpoints"].items():
                is_available = await self.test_endpoint_availability(endpoint_info)
                endpoint_info["available"] = is_available

                if is_available:
                    self.coverage_data["tested_endpoints"] += 1
                    module = endpoint_info["module"]
                    self.coverage_data["modules"][module]["tested"] += 1

            # Calculate coverage percentages
            total = self.coverage_data["total_endpoints"]
            tested = self.coverage_data["tested_endpoints"]
            self.coverage_data["coverage_percentage"] = (tested / total * 100) if total > 0 else 0

            for module_name, module_data in self.coverage_data["modules"].items():
                module_total = module_data["total"]
                module_tested = module_data["tested"]
                module_data["coverage"] = (module_tested / module_total * 100) if module_total > 0 else 0

        finally:
            await self.cleanup()

        return self.coverage_data

    def print_coverage_report(self, coverage_data: Dict[str, Any]):
        """Print formatted coverage report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE API COVERAGE REPORT")
        print("=" * 80)

        # Overall statistics
        total = coverage_data["total_endpoints"]
        tested = coverage_data["tested_endpoints"]
        coverage = coverage_data["coverage_percentage"]

        print(f"📈 Overall Coverage: {tested}/{total} endpoints ({coverage:.1f}%)")
        print(f"🕒 Generated: {coverage_data['timestamp']}")

        # Module breakdown
        print(f"\n📋 Coverage by Module:")
        print("-" * 80)
        print(f"{'Module':<20} {'Total':<8} {'Available':<10} {'Coverage':<10} {'Status'}")
        print("-" * 80)

        for module_name, module_data in coverage_data["modules"].items():
            total_endpoints = module_data["total"]
            tested_endpoints = module_data["tested"]
            module_coverage = module_data["coverage"]

            status = "🟢 Excellent" if module_coverage >= 90 else \
                    "🟡 Good" if module_coverage >= 75 else \
                    "🟠 Needs Work" if module_coverage >= 50 else \
                    "🔴 Critical"

            print(f"{module_name:<20} {total_endpoints:<8} {tested_endpoints:<10} {module_coverage:>6.1f}%    {status}")

        # Detailed endpoint listing
        print(f"\n📝 Detailed Endpoint Analysis:")
        print("-" * 80)

        for module_name, module_data in coverage_data["modules"].items():
            print(f"\n🔷 {module_name} Module ({module_data['tested']}/{module_data['total']} endpoints)")

            for endpoint_key in module_data["endpoints"]:
                endpoint = coverage_data["endpoints"][endpoint_key]
                status = "✅" if endpoint.get("available", False) else "❌"
                auth = "🔒" if endpoint["requires_auth"] else "🔓"
                print(f"   {status} {auth} {endpoint_key}")
                if endpoint.get("summary"):
                    print(f"      └─ {endpoint['summary']}")

        # Summary and recommendations
        print(f"\n💡 Summary:")
        if coverage >= 95:
            print("🎉 EXCELLENT: All endpoints are available and working!")
        elif coverage >= 85:
            print("✅ VERY GOOD: Most endpoints working, minor issues to address")
        elif coverage >= 75:
            print("⚠️ GOOD: System is functional but needs some attention")
        elif coverage >= 60:
            print("🟠 MODERATE: Several endpoints need fixes")
        else:
            print("🔴 CRITICAL: Many endpoints are failing")

        # API Statistics
        print(f"\n📊 API Statistics:")
        auth_required = sum(1 for ep in coverage_data["endpoints"].values() if ep["requires_auth"])
        public_endpoints = total - auth_required
        post_endpoints = sum(1 for ep in coverage_data["endpoints"].values() if ep["method"] == "POST")
        get_endpoints = sum(1 for ep in coverage_data["endpoints"].values() if ep["method"] == "GET")

        print(f"   • Total Endpoints: {total}")
        print(f"   • Public Endpoints: {public_endpoints}")
        print(f"   • Protected Endpoints: {auth_required}")
        print(f"   • GET Endpoints: {get_endpoints}")
        print(f"   • POST Endpoints: {post_endpoints}")

    def save_report(self, coverage_data: Dict[str, Any], filename: str = None):
        """Save coverage report to JSON file"""
        if not filename:
            timestamp = int(time.time())
            filename = f"api_coverage_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(coverage_data, f, indent=2, default=str)

        print(f"📄 Detailed report saved to: {filename}")
        return filename


async def main():
    """Main entry point"""
    analyzer = APICoverageAnalyzer()

    print("🚀 Generating API Coverage Report...")
    coverage_data = await analyzer.generate_coverage_report()

    if coverage_data:
        analyzer.print_coverage_report(coverage_data)
        analyzer.save_report(coverage_data)
    else:
        print("❌ Failed to generate coverage report")


if __name__ == "__main__":
    asyncio.run(main())