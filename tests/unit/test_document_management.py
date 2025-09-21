"""
Comprehensive tests for Document Management APIs
"""

import pytest
import json
import io
import os
import tempfile
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.user_management.user_models import User
from app.document_processing.document_models import Document, DocumentProcessingLog
from app.application_flow.application_models import Application
from app.user_management.user_service import hash_password

client = TestClient(app)

class TestDocumentManagementAPIs:
    """Test suite for Document Management endpoints"""

    def setup_method(self):
        """Set up test data before each test"""
        self.test_user_data = {
            "username": "docuser123",
            "email": "docuser@example.com",
            "password": "securepassword123",
            "full_name": "Document Test User"
        }

    @pytest.fixture
    def authenticated_user_token(self, db_session):
        """Create an authenticated user and return access token"""
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

        assert login_response.status_code == 200
        return login_response.json()["access_token"]

    @pytest.fixture
    def test_application(self, db_session, authenticated_user_token):
        """Create a test application for document association"""
        # Get user from token
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        application = Application(
            user_id=user_id,
            full_name="Test Application",
            emirates_id="123456789",
            phone="+971501234567",
            email="test@example.com",
            status="draft",
            progress=0
        )
        db_session.add(application)
        db_session.commit()
        return str(application.id)

    def create_test_file(self, filename="test.txt", content="Test file content", content_type="text/plain"):
        """Create a test file for upload"""
        file_obj = io.BytesIO(content.encode() if isinstance(content, str) else content)
        return (filename, file_obj, content_type)

    def create_test_image(self):
        """Create a test image file for upload"""
        # Create a simple PNG image
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x14IDATx\x9cc\xf8\x0f\x00\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x18\x8d\xb4\x1d\x00\x00\x00\x00IEND\xaeB`\x82'
        return ("test_image.png", io.BytesIO(png_data), "image/png")

    def test_upload_document_success(self, authenticated_user_token, test_application):
        """Test successful document upload"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        filename, file_obj, content_type = self.create_test_file()

        files = {"file": (filename, file_obj, content_type)}
        data = {
            "document_type": "bank_statement",
            "application_id": test_application
        }

        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["document_type"] == "bank_statement"
        assert result["application_id"] == test_application
        assert result["original_filename"] == filename
        assert result["processing_status"] == "uploaded"
        assert result["file_size"] > 0

    def test_upload_document_without_application(self, authenticated_user_token):
        """Test document upload without application association"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        filename, file_obj, content_type = self.create_test_file()

        files = {"file": (filename, file_obj, content_type)}
        data = {"document_type": "emirates_id"}

        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        assert response.status_code == 201
        result = response.json()
        assert result["application_id"] is None
        assert result["document_type"] == "emirates_id"

    def test_upload_document_invalid_file_type(self, authenticated_user_token):
        """Test upload with invalid file type"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create file with invalid extension
        filename, file_obj, content_type = self.create_test_file("test.exe", "executable content")

        files = {"file": (filename, file_obj, content_type)}
        data = {"document_type": "bank_statement"}

        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        assert response.status_code == 400
        assert "INVALID_FILE" in response.json()["detail"]["error"]

    def test_upload_document_nonexistent_application(self, authenticated_user_token):
        """Test upload with non-existent application ID"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        filename, file_obj, content_type = self.create_test_file()

        files = {"file": (filename, file_obj, content_type)}
        data = {
            "document_type": "bank_statement",
            "application_id": "00000000-0000-0000-0000-000000000000"
        }

        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        assert response.status_code == 404
        assert "APPLICATION_NOT_FOUND" in response.json()["detail"]["error"]

    def test_upload_image_document(self, authenticated_user_token):
        """Test successful image document upload"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        filename, file_obj, content_type = self.create_test_image()

        files = {"file": (filename, file_obj, content_type)}
        data = {"document_type": "emirates_id"}

        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        assert response.status_code == 201
        result = response.json()
        assert result["mime_type"] == "image/png"
        assert result["document_type"] == "emirates_id"

    def test_list_documents_success(self, authenticated_user_token, db_session):
        """Test successful document listing"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test documents
        for i in range(5):
            doc = Document(
                user_id=user_id,
                document_type=f"test_type_{i}",
                original_filename=f"test_{i}.txt",
                file_path=f"/tmp/test_{i}.txt",
                file_size=100 + i,
                mime_type="text/plain",
                processing_status="uploaded"
            )
            db_session.add(doc)
        db_session.commit()

        response = client.get("/document-management/", headers=headers)

        assert response.status_code == 200
        result = response.json()
        assert "documents" in result
        assert "total_count" in result
        assert len(result["documents"]) == 5
        assert result["total_count"] == 5

    def test_list_documents_with_filters(self, authenticated_user_token, db_session):
        """Test document listing with filters"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test documents with different types and statuses
        doc_configs = [
            ("bank_statement", "uploaded"),
            ("bank_statement", "processing"),
            ("emirates_id", "uploaded"),
            ("emirates_id", "completed")
        ]

        for doc_type, status in doc_configs:
            doc = Document(
                user_id=user_id,
                document_type=doc_type,
                original_filename=f"{doc_type}.txt",
                file_path=f"/tmp/{doc_type}.txt",
                file_size=100,
                mime_type="text/plain",
                processing_status=status
            )
            db_session.add(doc)
        db_session.commit()

        # Test filter by document type
        response = client.get("/document-management/?document_type=bank_statement", headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 2
        for doc in result["documents"]:
            assert doc["document_type"] == "bank_statement"

        # Test filter by status
        response = client.get("/document-management/?status_filter=uploaded", headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 2
        for doc in result["documents"]:
            assert doc["processing_status"] == "uploaded"

    def test_list_documents_pagination(self, authenticated_user_token, db_session):
        """Test document listing pagination"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create 15 test documents
        for i in range(15):
            doc = Document(
                user_id=user_id,
                document_type="test_type",
                original_filename=f"test_{i}.txt",
                file_path=f"/tmp/test_{i}.txt",
                file_size=100,
                mime_type="text/plain",
                processing_status="uploaded"
            )
            db_session.add(doc)
        db_session.commit()

        # Test first page
        response = client.get("/document-management/?page=1&page_size=5", headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 5
        assert result["page"] == 1
        assert result["page_size"] == 5
        assert result["total_count"] == 15

        # Test second page
        response = client.get("/document-management/?page=2&page_size=5", headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 5
        assert result["page"] == 2

    def test_get_document_success(self, authenticated_user_token, db_session):
        """Test successful document retrieval"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="test_document",
            original_filename="test.txt",
            file_path="/tmp/test.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded",
            extracted_text="Sample extracted text"
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get(f"/document-management/{doc.id}", headers=headers)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == str(doc.id)
        assert result["document_type"] == "test_document"
        assert result["extracted_text"] == "Sample extracted text"

    def test_get_document_not_found(self, authenticated_user_token):
        """Test document retrieval with non-existent ID"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/document-management/{fake_id}", headers=headers)

        assert response.status_code == 404
        assert "DOCUMENT_NOT_FOUND" in response.json()["detail"]["error"]

    def test_update_document_success(self, authenticated_user_token, db_session):
        """Test successful document update"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="old_type",
            original_filename="test.txt",
            file_path="/tmp/test.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        update_data = {
            "document_type": "new_type",
            "structured_data": {"key": "value", "number": 123}
        }

        response = client.put(f"/document-management/{doc.id}",
                            json=update_data, headers=headers)

        assert response.status_code == 200
        result = response.json()
        assert result["document_type"] == "new_type"
        assert result["structured_data"] == {"key": "value", "number": 123}

    def test_delete_document_success(self, authenticated_user_token, db_session):
        """Test successful document deletion"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="test_type",
            original_filename="test.txt",
            file_path=tmp_path,
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        response = client.delete(f"/document-management/{doc.id}", headers=headers)

        assert response.status_code == 200
        assert "Document deleted successfully" in response.json()["message"]

        # Verify document is deleted from database
        deleted_doc = db_session.query(Document).filter(Document.id == doc.id).first()
        assert deleted_doc is None

        # Clean up temporary file if it still exists
        try:
            os.unlink(tmp_path)
        except:
            pass

    def test_download_document_success(self, authenticated_user_token, db_session):
        """Test successful document download"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create temporary file with content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(b"test file content for download")
            tmp_path = tmp_file.name

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="test_type",
            original_filename="download_test.txt",
            file_path=tmp_path,
            file_size=26,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get(f"/document-management/{doc.id}/download", headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert b"test file content for download" in response.content

        # Clean up
        os.unlink(tmp_path)

    def test_download_document_file_not_found(self, authenticated_user_token, db_session):
        """Test document download when file doesn't exist on disk"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test document with non-existent file path
        doc = Document(
            user_id=user_id,
            document_type="test_type",
            original_filename="missing.txt",
            file_path="/non/existent/path/missing.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get(f"/document-management/{doc.id}/download", headers=headers)

        assert response.status_code == 404
        assert "FILE_NOT_FOUND" in response.json()["detail"]["error"]

    def test_get_processing_logs(self, authenticated_user_token, db_session):
        """Test getting document processing logs"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="test_type",
            original_filename="test.txt",
            file_path="/tmp/test.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        # Create processing logs
        log1 = DocumentProcessingLog(
            document_id=doc.id,
            processing_step="ocr",
            step_status="completed",
            step_result={"text": "extracted text"},
            confidence_score=0.95,
            processing_time_ms=1500
        )
        log2 = DocumentProcessingLog(
            document_id=doc.id,
            processing_step="analysis",
            step_status="started",
            processing_time_ms=0
        )
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        response = client.get(f"/document-management/{doc.id}/processing-logs", headers=headers)

        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2
        assert logs[0]["processing_step"] == "ocr"
        assert logs[0]["step_status"] == "completed"
        assert logs[0]["confidence_score"] == 0.95
        assert logs[1]["processing_step"] == "analysis"

    def test_get_supported_types(self):
        """Test getting supported document types"""
        response = client.get("/document-management/types/supported")

        assert response.status_code == 200
        result = response.json()
        assert "document_types" in result
        assert "supported_formats" in result
        assert "processing_capabilities" in result

        assert "bank_statement" in result["document_types"]
        assert "emirates_id" in result["document_types"]
        assert ".pdf" in result["supported_formats"]["documents"]
        assert ".png" in result["supported_formats"]["images"]

    def test_document_access_control(self, authenticated_user_token, db_session):
        """Test that users can only access their own documents"""
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

        # Create document for other user
        other_doc = Document(
            user_id=other_user.id,
            document_type="private_doc",
            original_filename="private.txt",
            file_path="/tmp/private.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(other_doc)
        db_session.commit()

        # Try to access other user's document
        response = client.get(f"/document-management/{other_doc.id}", headers=headers)
        assert response.status_code == 404

        # Try to update other user's document
        response = client.put(f"/document-management/{other_doc.id}",
                            json={"document_type": "hacked"}, headers=headers)
        assert response.status_code == 404

        # Try to delete other user's document
        response = client.delete(f"/document-management/{other_doc.id}", headers=headers)
        assert response.status_code == 404

    def test_large_file_handling(self, authenticated_user_token):
        """Test handling of large files"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Create a large file (simulate size check)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB, over the limit
        filename, file_obj, content_type = ("large_file.txt", io.BytesIO(large_content), "text/plain")

        files = {"file": (filename, file_obj, content_type)}
        data = {"document_type": "bank_statement"}

        # Note: This test assumes the validation catches the size
        # In practice, FastAPI might handle this differently
        response = client.post("/document-management/upload",
                             files=files, data=data, headers=headers)

        # The exact status code may vary based on implementation
        assert response.status_code in [400, 413, 422]

    def test_concurrent_document_operations(self, authenticated_user_token, db_session):
        """Test concurrent document operations"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Get user ID
        profile_response = client.get("/users/profile", headers=headers)
        user_id = profile_response.json()["id"]

        # Create test document
        doc = Document(
            user_id=user_id,
            document_type="concurrent_test",
            original_filename="test.txt",
            file_path="/tmp/test.txt",
            file_size=100,
            mime_type="text/plain",
            processing_status="uploaded"
        )
        db_session.add(doc)
        db_session.commit()

        # Simulate concurrent updates
        update1 = {"document_type": "type1"}
        update2 = {"document_type": "type2"}

        response1 = client.put(f"/document-management/{doc.id}",
                              json=update1, headers=headers)
        response2 = client.put(f"/document-management/{doc.id}",
                              json=update2, headers=headers)

        # Both should succeed (last one wins)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response2.json()["document_type"] == "type2"

    def test_malformed_document_requests(self, authenticated_user_token):
        """Test handling of malformed document requests"""
        headers = {"Authorization": f"Bearer {authenticated_user_token}"}

        # Test upload without file
        response = client.post("/document-management/upload",
                             data={"document_type": "test"}, headers=headers)
        assert response.status_code == 422

        # Test upload without document_type
        filename, file_obj, content_type = self.create_test_file()
        files = {"file": (filename, file_obj, content_type)}
        response = client.post("/document-management/upload",
                             files=files, headers=headers)
        assert response.status_code == 422

        # Test update with invalid JSON
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.put(f"/document-management/{fake_id}",
                            data="invalid json",
                            headers={**headers, "Content-Type": "application/json"})
        assert response.status_code in [400, 422]