"""
API client for communicating with FastAPI backend
"""

import httpx
import streamlit as st
from typing import Dict, Any, Optional, List
import json
import os

# Get API base URL from environment or default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    """Client for making API requests to the FastAPI backend"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.timeout = 30.0

    def _get_headers(self) -> Dict[str, str]:
        """Get headers including authentication token if available"""
        headers = {"Content-Type": "application/json"}

        # Get token from session state if available
        if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        return headers

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response and extract data"""
        try:
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                return response.json()
            elif response.status_code == 422:
                error_data = response.json()
                return {"error": "Validation Error", "details": error_data.get("detail", [])}
            elif response.status_code == 401:
                # Clear token if unauthorized
                if hasattr(st.session_state, 'access_token'):
                    st.session_state.access_token = None
                    st.session_state.user_info = None
                return {"error": "Authentication required", "status_code": 401}
            else:
                try:
                    error_data = response.json()
                    return {"error": error_data.get("message", "Unknown error"), "status_code": response.status_code}
                except:
                    return {"error": f"HTTP {response.status_code}", "status_code": response.status_code}
        except Exception as e:
            return {"error": f"Response parsing error: {str(e)}"}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login user and get access token"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/auth/login",
                    json={"username": username, "password": password}
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def register(self, username: str, email: str, password: str, full_name: str = None) -> Dict[str, Any]:
        """Register new user"""
        try:
            user_data = {
                "username": username,
                "email": email,
                "password": password
            }
            if full_name:
                user_data["full_name"] = full_name

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/auth/register",
                    json=user_data
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_current_user(self) -> Dict[str, Any]:
        """Get current user information"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/auth/me",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def create_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new application"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/workflow/start-application",
                    json=application_data,
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def upload_documents(self, application_id: str, files: Dict[str, bytes]) -> Dict[str, Any]:
        """Upload documents for an application"""
        try:
            files_data = {}
            for doc_type, file_content in files.items():
                files_data[doc_type] = file_content

            headers = {}
            if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
                headers["Authorization"] = f"Bearer {st.session_state.access_token}"

            with httpx.Client(timeout=60.0) as client:  # Longer timeout for file uploads
                response = client.post(
                    f"{self.base_url}/workflow/upload-documents/{application_id}",
                    files=files_data,
                    headers=headers
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Upload error: {str(e)}"}

    def get_application_status(self, application_id: str) -> Dict[str, Any]:
        """Get application processing status"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/workflow/status/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_application_results(self, application_id: str) -> Dict[str, Any]:
        """Get application decision results"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/applications/{application_id}/results",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def start_processing(self, application_id: str) -> Dict[str, Any]:
        """Start application processing"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/workflow/process/{application_id}",
                    json={},
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/health")
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_user_applications(self) -> Dict[str, Any]:
        """Get current user's applications"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/applications/my-applications",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}


# Global API client instance
api_client = APIClient()