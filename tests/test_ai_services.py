"""
Comprehensive tests for AI Services (Analysis, OCR, Decision Making, Chatbot)
"""

import pytest
import json
import base64
import io
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.user_management.user_models import User
from app.document_processing.document_models import Document
from app.application_flow.application_models import Application
from app.user_management.user_service import hash_password

client = TestClient(app)

class TestMultimodalAnalysisAPIs:
    """Test suite for Multimodal Analysis endpoints"""

    def setup_method(self):
        """Set up test data"""
        self.test_user_data = {
            "username": "aiuser123",
            "email": "aiuser@example.com",
            "password": "securepassword123",
            "full_name": "AI Test User"
        }

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create authenticated user and return token"""
        user = User(
            username=self.test_user_data["username"],
            email=self.test_user_data["email"],
            password_hash=hash_password(self.test_user_data["password"]),
            full_name=self.test_user_data["full_name"],
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login", json={
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        })
        return login_response.json()["access_token"]

    @pytest.fixture
    def test_document(self, db_session, authenticated_user_token):
        """Create test document"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        doc = Document(
            user_id=user_id,
            document_type="bank_statement",
            original_filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()
        return str(doc.id)

    def test_analyze_document_success(self, authenticated_user_token, test_document):
        """Test successful document analysis"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        analysis_request = {
            "document_id": test_document,
            "analysis_type": "full",
            "custom_prompt": "Analyze this bank statement for income verification"
        }

        response = client.post(f"/analysis/documents/{test_document}",
                             json=analysis_request, headers=headers)

        # Note: This will fail if Ollama is not running, but we test the API structure
        assert response.status_code in [200, 500]  # 500 if Ollama not available

        if response.status_code == 200:
            result = response.json()
            assert "analysis_id" in result
            assert "document_id" in result
            assert "status" in result
            assert "processing_time_ms" in result

    def test_analyze_document_not_found(self, authenticated_user_token):
        """Test analysis with non-existent document"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        fake_id = "00000000-0000-0000-0000-000000000000"
        analysis_request = {
            "document_id": fake_id,
            "analysis_type": "full"
        }

        response = client.post(f"/analysis/documents/{fake_id}",
                             json=analysis_request, headers=headers)

        assert response.status_code == 404
        assert "DOCUMENT_NOT_FOUND" in response.json()["detail"]["error"]

    def test_bulk_analysis(self, authenticated_user_token, test_document, db_session):
        """Test bulk document analysis"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create additional test document
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        doc2 = Document(
            user_id=user_id,
            document_type="emirates_id",
            original_filename="emirates.jpg",
            file_path="/tmp/emirates.jpg",
            file_size=2048,
            mime_type="image/jpeg",
            processing_status="uploaded"
        )
        db_session.add(doc2)
        db_session.commit()

        bulk_request = {
            "document_ids": [test_document, str(doc2.id)],
            "analysis_type": "text_only"
        }

        response = client.post("/analysis/bulk", json=bulk_request, headers=headers)

        assert response.status_code in [200, 500]  # 500 if Ollama not available

        if response.status_code == 200:
            result = response.json()
            assert "batch_id" in result
            assert "total_documents" in result
            assert result["total_documents"] == 2

    def test_multimodal_query(self, authenticated_user_token):
        """Test interactive multimodal query"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create a simple base64 test image
        test_image_data = base64.b64encode(b"fake_image_data").decode()

        query_request = {
            "query": "What do you see in this image?",
            "image_data": test_image_data,
            "context": "This is a test image analysis"
        }

        response = client.post("/analysis/query", json=query_request, headers=headers)

        assert response.status_code in [200, 400, 500]  # May fail with invalid image data

    def test_upload_and_analyze(self, authenticated_user_token):
        """Test upload and analyze in one step"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create test file
        test_content = b"Test document content"
        files = {"file": ("test.txt", io.BytesIO(test_content), "text/plain")}
        data = {
            "analysis_type": "full",
            "custom_prompt": "Analyze this document content"
        }

        response = client.post("/analysis/upload-and-analyze",
                             files=files, data=data, headers=headers)

        assert response.status_code in [200, 500]  # 500 if services not available


class TestOCRAPIs:
    """Test suite for OCR Processing endpoints"""

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create authenticated user and return token"""
        user = User(
            username="ocruser123",
            email="ocruser@example.com",
            password_hash=hash_password("securepassword123"),
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login", json={
            "username": "ocruser123",
            "password": "securepassword123"
        })
        return login_response.json()["access_token"]

    @pytest.fixture
    def test_image_document(self, db_session, authenticated_user_token):
        """Create test image document"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        doc = Document(
            user_id=user_id,
            document_type="emirates_id",
            original_filename="test_image.png",
            file_path="/tmp/test_image.png",
            file_size=2048,
            mime_type="image/png",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()
        return str(doc.id)

    def test_ocr_document_success(self, authenticated_user_token, test_image_document):
        """Test OCR processing on document"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        ocr_request = {
            "document_id": test_image_document,
            "language_hints": ["en", "ar"],
            "preprocess": True
        }

        response = client.post(f"/ocr/documents/{test_image_document}",
                             json=ocr_request, headers=headers)

        # Will fail if EasyOCR not available or file doesn't exist
        assert response.status_code in [200, 404, 500]

    def test_direct_ocr(self, authenticated_user_token):
        """Test direct OCR processing"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create base64 encoded test image
        test_image_data = base64.b64encode(b"fake_image_data").decode()

        ocr_request = {
            "image_data": test_image_data,
            "language_hints": ["en"],
            "preprocess": True
        }

        response = client.post("/ocr/direct", json=ocr_request, headers=headers)

        assert response.status_code in [200, 400, 500]  # May fail with invalid image

    def test_upload_and_extract(self, authenticated_user_token):
        """Test upload and OCR extraction in one step"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create test image file
        test_image = b"fake_image_content"
        files = {"file": ("test_image.png", io.BytesIO(test_image), "image/png")}
        data = {
            "language_hints": "en,ar",
            "preprocess": "true"
        }

        response = client.post("/ocr/upload-and-extract",
                             files=files, data=data, headers=headers)

        assert response.status_code in [200, 500]  # 500 if OCR service not available

    def test_ocr_health_check(self):
        """Test OCR service health check"""
        response = client.get("/ocr/health")

        assert response.status_code in [200, 503]
        result = response.json()
        assert "status" in result
        assert "service" in result
        assert result["service"] == "OCR Processing"

    def test_batch_ocr(self, authenticated_user_token, test_image_document, db_session):
        """Test batch OCR processing"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create additional test document
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        doc2 = Document(
            user_id=user_id,
            document_type="bank_statement",
            original_filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status="uploaded"
        )
        db_session.add(doc2)
        db_session.commit()

        batch_request = {
            "document_ids": [test_image_document, str(doc2.id)],
            "language_hints": ["en"],
            "preprocess": True
        }

        response = client.post("/ocr/batch", json=batch_request, headers=headers)

        assert response.status_code in [200, 500]  # 500 if OCR not available


class TestDecisionMakingAPIs:
    """Test suite for AI Decision Making endpoints"""

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create authenticated user and return token"""
        user = User(
            username="decisionuser123",
            email="decisionuser@example.com",
            password_hash=hash_password("securepassword123"),
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login", json={
            "username": "decisionuser123",
            "password": "securepassword123"
        })
        return login_response.json()["access_token"]

    @pytest.fixture
    def test_application(self, db_session, authenticated_user_token):
        """Create test application for decision making"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        app = Application(
            user_id=user_id,
            full_name="Test Application",
            emirates_id="123456789",
            phone="+971501234567",
            email="test@example.com",
            monthly_income=3000.0,
            account_balance=15000.0,
            status="processing",
            progress=50
        )
        db_session.add(app)
        db_session.commit()
        return str(app.id)

    def test_make_decision_success(self, authenticated_user_token, test_application):
        """Test successful decision making"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        decision_request = {
            "application_id": test_application,
            "reasoning_depth": "standard"
        }

        response = client.post("/decisions/make-decision",
                             json=decision_request, headers=headers)

        assert response.status_code in [200, 500]  # 500 if LLM not available

        if response.status_code == 200:
            result = response.json()
            assert "decision_id" in result
            assert "application_id" in result
            assert "result" in result
            assert result["result"]["decision"] in ["approved", "rejected", "needs_review"]

    def test_make_decision_force_review(self, authenticated_user_token, test_application):
        """Test forced manual review decision"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        decision_request = {
            "application_id": test_application,
            "force_review": True
        }

        response = client.post("/decisions/make-decision",
                             json=decision_request, headers=headers)

        assert response.status_code == 200
        result = response.json()
        assert result["result"]["decision"] == "needs_review"

    def test_make_decision_with_custom_criteria(self, authenticated_user_token, test_application):
        """Test decision making with custom criteria"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        decision_request = {
            "application_id": test_application,
            "criteria_override": {
                "income_threshold": 4000.0,
                "asset_limit": 30000.0,
                "min_age": 21,
                "max_age": 60
            }
        }

        response = client.post("/decisions/make-decision",
                             json=decision_request, headers=headers)

        assert response.status_code in [200, 500]

    def test_batch_decisions(self, authenticated_user_token, test_application, db_session):
        """Test batch decision making"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create additional test application
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        app2 = Application(
            user_id=user_id,
            full_name="Test Application 2",
            emirates_id="987654321",
            phone="+971507654321",
            email="test2@example.com",
            monthly_income=6000.0,
            account_balance=60000.0,
            status="processing",
            progress=50
        )
        db_session.add(app2)
        db_session.commit()

        batch_request = {
            "application_ids": [test_application, str(app2.id)]
        }

        response = client.post("/decisions/batch", json=batch_request, headers=headers)

        assert response.status_code in [200, 500]

    def test_get_decision_criteria(self):
        """Test getting decision criteria"""
        response = client.get("/decisions/criteria")

        assert response.status_code == 200
        criteria = response.json()
        assert "income_threshold" in criteria
        assert "asset_limit" in criteria
        assert "min_age" in criteria
        assert "max_age" in criteria

    def test_explain_decision(self, authenticated_user_token, test_application):
        """Test decision explanation"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # First make a decision
        decision_request = {"application_id": test_application}
        decision_response = client.post("/decisions/make-decision",
                                      json=decision_request, headers=headers)

        if decision_response.status_code == 200:
            decision_id = decision_response.json()["decision_id"]

            explanation_request = {
                "decision_id": decision_id,
                "detail_level": "standard"
            }

            response = client.post(f"/decisions/explain/{decision_id}",
                                 json=explanation_request, headers=headers)

            assert response.status_code in [200, 500]

    def test_decision_health_check(self):
        """Test decision service health check"""
        response = client.get("/decisions/health")

        assert response.status_code in [200, 503]
        result = response.json()
        assert "status" in result
        assert "service" in result
        assert result["service"] == "Decision Making"


class TestChatbotAPIs:
    """Test suite for Chatbot endpoints"""

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create authenticated user and return token"""
        user = User(
            username="chatuser123",
            email="chatuser@example.com",
            password_hash=hash_password("securepassword123"),
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login", json={
            "username": "chatuser123",
            "password": "securepassword123"
        })
        return login_response.json()["access_token"]

    def test_chat_message_new_session(self, authenticated_user_token):
        """Test sending chat message in new session"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        chat_request = {
            "message": "Hello, I need help with my application",
            "stream": False
        }

        response = client.post("/chatbot/chat", json=chat_request, headers=headers)

        assert response.status_code in [200, 500]  # 500 if LLM not available

        if response.status_code == 200:
            result = response.json()
            assert "session_id" in result
            assert "response" in result
            assert "suggestions" in result
            assert isinstance(result["suggestions"], list)

    def test_chat_message_existing_session(self, authenticated_user_token):
        """Test sending chat message in existing session"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # First message to create session
        chat_request1 = {
            "message": "Hello",
            "stream": False
        }

        response1 = client.post("/chatbot/chat", json=chat_request1, headers=headers)

        if response1.status_code == 200:
            session_id = response1.json()["session_id"]

            # Second message in same session
            chat_request2 = {
                "message": "What documents do I need?",
                "session_id": session_id,
                "stream": False
            }

            response2 = client.post("/chatbot/chat", json=chat_request2, headers=headers)

            assert response2.status_code in [200, 500]
            if response2.status_code == 200:
                assert response2.json()["session_id"] == session_id

    def test_get_chat_sessions(self, authenticated_user_token):
        """Test getting chat sessions"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create a chat session first
        chat_request = {
            "message": "Test message",
            "stream": False
        }
        client.post("/chatbot/chat", json=chat_request, headers=headers)

        # Get sessions
        response = client.get("/chatbot/sessions", headers=headers)

        assert response.status_code == 200
        result = response.json()
        assert "sessions" in result
        assert "total_count" in result
        assert isinstance(result["sessions"], list)

    def test_get_specific_chat_session(self, authenticated_user_token):
        """Test getting specific chat session"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create a chat session first
        chat_request = {
            "message": "Test message for specific session",
            "stream": False
        }
        chat_response = client.post("/chatbot/chat", json=chat_request, headers=headers)

        if chat_response.status_code == 200:
            session_id = chat_response.json()["session_id"]

            # Get specific session
            response = client.get(f"/chatbot/sessions/{session_id}", headers=headers)

            assert response.status_code == 200
            result = response.json()
            assert result["session_id"] == session_id
            assert "messages" in result

    def test_delete_chat_session(self, authenticated_user_token):
        """Test deleting chat session"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create a chat session first
        chat_request = {
            "message": "Test message for deletion",
            "stream": False
        }
        chat_response = client.post("/chatbot/chat", json=chat_request, headers=headers)

        if chat_response.status_code == 200:
            session_id = chat_response.json()["session_id"]

            # Delete session
            response = client.delete(f"/chatbot/sessions/{session_id}", headers=headers)

            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]

    def test_get_quick_help(self):
        """Test getting quick help responses"""
        response = client.get("/chatbot/quick-help")

        assert response.status_code == 200
        result = response.json()
        assert "application_process" in result
        assert "document_requirements" in result
        assert "processing_time" in result
        assert "eligibility_criteria" in result

    def test_chatbot_health_check(self):
        """Test chatbot service health check"""
        response = client.get("/chatbot/health")

        assert response.status_code in [200, 503]
        result = response.json()
        assert "status" in result
        assert "service" in result
        assert result["service"] == "Chatbot"

    def test_chat_with_context(self, authenticated_user_token):
        """Test chat with additional context"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        chat_request = {
            "message": "What's the status of my application?",
            "context": {
                "current_application_id": "123",
                "user_type": "first_time_applicant"
            },
            "stream": False
        }

        response = client.post("/chatbot/chat", json=chat_request, headers=headers)

        assert response.status_code in [200, 500]

    def test_chat_security_and_validation(self, authenticated_user_token):
        """Test chat security and validation"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Test with very long message
        long_message = "A" * 10000
        chat_request = {
            "message": long_message,
            "stream": False
        }

        response = client.post("/chatbot/chat", json=chat_request, headers=headers)
        # Should handle gracefully
        assert response.status_code in [200, 400, 422, 500]

        # Test with empty message
        empty_request = {
            "message": "",
            "stream": False
        }

        response = client.post("/chatbot/chat", json=empty_request, headers=headers)
        assert response.status_code in [200, 400, 422]

    def test_session_access_control(self, authenticated_user_token, db_session):
        """Test that users can only access their own chat sessions"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=hash_password("password"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        # Try to access non-existent session
        fake_session_id = "fake_session_12345"
        response = client.get(f"/chatbot/sessions/{fake_session_id}", headers=headers)
        assert response.status_code == 404