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
            elif response.status_code == 202:
                return response.json()
            elif response.status_code == 405:
                return {"error": "Method not allowed - check API endpoint", "status_code": 405}
            elif response.status_code == 307:
                # Handle redirects - follow redirect automatically
                redirect_url = response.headers.get('location')
                return {"error": f"Redirect to {redirect_url}. Please update the API endpoint.", "status_code": 307}
            elif response.status_code == 422:
                error_data = response.json()
                return {"error": "Validation Error", "details": error_data.get("detail", [])}
            elif response.status_code == 401:
                # Clear token if unauthorized
                if hasattr(st.session_state, 'access_token'):
                    st.session_state.access_token = None
                    st.session_state.user_info = None
                return {"error": "Authentication required", "status_code": 401}
            elif response.status_code == 404:
                # Handle not found responses
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", {})
                    return {
                        "error": detail.get("message", "Not found"),
                        "status_code": 404,
                        "details": detail
                    }
                except:
                    return {"error": "Not found", "status_code": 404}
            elif response.status_code == 409:
                # Handle conflict responses (like existing application)
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", {})
                    return {
                        "error": detail.get("message", "Conflict error"),
                        "status_code": 409,
                        "details": detail
                    }
                except:
                    return {"error": "Conflict error", "status_code": 409}
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
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
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

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
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
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/auth/me",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def logout(self) -> Dict[str, Any]:
        """Logout current user"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/auth/logout",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def create_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new application"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/workflow/start-application",
                    json=application_data,
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def upload_document(self, file_content: bytes, file_name: str, document_type: str, application_id: str = None) -> Dict[str, Any]:
        """Upload a single document"""
        try:
            headers = {}
            if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
                headers["Authorization"] = f"Bearer {st.session_state.access_token}"

            # Prepare form data
            files = {"file": (file_name, file_content)}
            data = {"document_type": document_type}
            if application_id:
                data["application_id"] = application_id

            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/documents/upload",
                    files=files,
                    data=data,
                    headers=headers
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Upload error: {str(e)}"}

    def upload_documents(self, application_id: str, files: Dict[str, tuple]) -> Dict[str, Any]:
        """Upload multiple documents for an application
        
        Args:
            application_id: The application ID
            files: Dict with doc_type as key and (filename, data, content_type) tuple as value
        """
        try:
            headers = {}
            if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
                headers["Authorization"] = f"Bearer {st.session_state.access_token}"

            # Prepare files according to backend expectations
            upload_files = {}
            data = {}

            if application_id:
                data["application_id"] = application_id

            for doc_type, file_info in files.items():
                # Extract filename, data, and content_type from tuple
                filename, file_data, content_type = file_info
                upload_files[doc_type] = (filename, file_data, content_type)

            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/documents/upload",
                    files=upload_files,
                    data=data,
                    headers=headers
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Upload error: {str(e)}"}

    def get_application_status(self, application_id: str) -> Dict[str, Any]:
        """Get application processing status"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
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
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
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
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
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
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(f"{self.base_url}/health/")
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_user_applications(self) -> Dict[str, Any]:
        """Get current user's applications"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/applications/",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_user_applications_simple(self) -> Dict[str, Any]:
        """Get simple list of current user's application IDs"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/applications/simple-list",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def cancel_application(self, application_id: str) -> Dict[str, Any]:
        """Cancel an active application"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.delete(
                    f"{self.base_url}/workflow/cancel-application/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def update_application_form(self, application_id: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update application form data"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.put(
                    f"{self.base_url}/workflow/update-form/{application_id}",
                    json=form_data,
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def reset_application_status(self, application_id: str) -> Dict[str, Any]:
        """Reset application status to editable state"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.put(
                    f"{self.base_url}/workflow/reset-status/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}
    
    def get_documents_status(self, application_id: str) -> Dict[str, Any]:
        """Get document status for an application"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/documents/application/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}
    
    def download_document(self, document_id: str) -> Dict[str, Any]:
        """Download a specific document"""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/documents/download/{document_id}",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return {
                        "data": response.content,
                        "content_type": response.headers.get("content-type", "application/octet-stream")
                    }
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Download error: {str(e)}"}
    
    def process_application(self, application_id: str) -> Dict[str, Any]:
        """Start processing an application"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/workflow/process/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Processing error: {str(e)}"}
    
    def get_processing_status(self, application_id: str) -> Dict[str, Any]:
        """Get detailed processing status with OCR results"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/workflow/processing-status/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Status fetch error: {str(e)}"}

    def get_application_history(self) -> Dict[str, Any]:
        """Get application history for current user"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/applications/history",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def discard_current_application(self) -> Dict[str, Any]:
        """Discard current active application"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.delete(
                    f"{self.base_url}/workflow/discard-application",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    # OCR and Document Processing Methods

    def ocr_document(self, document_id: str) -> Dict[str, Any]:
        """Process a document with OCR"""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:  # Longer timeout for OCR
                response = client.post(
                    f"{self.base_url}/ocr/documents/{document_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"OCR processing error: {str(e)}"}

    def direct_ocr(self, file_content: bytes, file_name: str, document_type: str) -> Dict[str, Any]:
        """Perform direct OCR on a file without saving to database"""
        try:
            import base64

            # Determine file type based on filename extension
            file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''

            if file_extension == 'pdf':
                # Use upload-and-extract endpoint for PDFs
                return self.upload_and_extract(file_content, file_name, document_type)
            else:
                # Use direct endpoint for images
                # Encode file content as base64
                image_data_b64 = base64.b64encode(file_content).decode('utf-8')

                # Prepare JSON payload
                payload = {
                    "image_data": image_data_b64,
                    "language_hints": ["en", "ar"],
                    "preprocess": True
                }

                with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                    response = client.post(
                        f"{self.base_url}/ocr/direct",
                        json=payload,
                        headers=self._get_headers()
                    )
                    result = self._handle_response(response)

                    # Extract the result from the nested structure
                    if 'error' not in result and 'result' in result:
                        # Flatten the response to match expected format
                        ocr_result = result['result']
                        return {
                            'extracted_text': ocr_result.get('extracted_text', ''),
                            'confidence_average': ocr_result.get('confidence_average', 0),
                            'text_regions': ocr_result.get('text_regions', []),
                            'language_detected': ocr_result.get('language_detected', []),
                            'processing_time_ms': result.get('processing_time_ms', 0),
                            'ocr_id': result.get('ocr_id', ''),
                            'timestamp': result.get('timestamp', '')
                        }

                    return result
        except Exception as e:
            return {"error": f"Direct OCR error: {str(e)}"}

    def upload_and_extract(self, file_content: bytes, file_name: str, document_type: str) -> Dict[str, Any]:
        """Upload a file and immediately extract text"""
        try:
            files = {"file": (file_name, file_content)}
            data = {"language_hints": "en,ar", "preprocess": "true"}

            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/ocr/upload-and-extract",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
                )
                result = self._handle_response(response)

                # Extract the result from the nested structure
                if 'error' not in result and 'result' in result:
                    # Flatten the response to match expected format
                    ocr_result = result['result']
                    return {
                        'extracted_text': ocr_result.get('extracted_text', ''),
                        'confidence_average': ocr_result.get('confidence_average', 0),
                        'text_regions': ocr_result.get('text_regions', []),
                        'language_detected': ocr_result.get('language_detected', []),
                        'processing_time_ms': result.get('processing_time_ms', 0),
                        'ocr_id': result.get('ocr_id', ''),
                        'timestamp': result.get('timestamp', '')
                    }

                return result
        except Exception as e:
            return {"error": f"Upload and extract error: {str(e)}"}

    def get_ocr_health(self) -> Dict[str, Any]:
        """Check OCR service health"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(f"{self.base_url}/ocr/health")
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"OCR health check error: {str(e)}"}

    # Analysis endpoints for multimodal processing

    def analyze_document(self, document_id: str) -> Dict[str, Any]:
        """Analyze a document with AI"""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.post(
                    f"{self.base_url}/analysis/documents/{document_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Document analysis error: {str(e)}"}

    def get_analysis_status(self, document_id: str) -> Dict[str, Any]:
        """Get analysis status for a document"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/analysis/documents/{document_id}/status",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Analysis status error: {str(e)}"}

    def get_enhanced_processing_status(self, application_id: str) -> Dict[str, Any]:
        """Get enhanced processing status with detailed OCR and analysis info"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    f"{self.base_url}/workflow/status-enhanced/{application_id}",
                    headers=self._get_headers()
                )
                return self._handle_response(response)
        except Exception as e:
            return {"error": f"Enhanced status error: {str(e)}"}


# Global API client instance
api_client = APIClient()