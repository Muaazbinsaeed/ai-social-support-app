"""
PyTest configuration and fixtures
"""

import pytest
import asyncio
from typing import Generator, Dict, Any
import tempfile
import os
from pathlib import Path

# FastAPI and database imports
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Application imports
from app.main import app
from app.shared.database import get_db, Base
from app.config import settings
from app.user_management.user_service import UserService
from app.user_management.auth_schemas import UserCreate

# Test database URL (using SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"

# SQLite UUID support
from sqlalchemy import TypeDecorator, String
import uuid

class GUID(TypeDecorator):
    """Platform-independent GUID type that stores UUIDs as strings in SQLite."""
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(String(36))
        else:
            # For PostgreSQL, use the native UUID type
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'sqlite':
            return str(value)
        else:
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite specific
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create a test client with database dependency override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_user(db_session: Session, test_user_data: Dict[str, Any]):
    """Create a test user"""
    user_create = UserCreate(**test_user_data)
    user = UserService.create_user(db_session, user_create)
    return user


@pytest.fixture
def authenticated_client(client: TestClient, test_user_data: Dict[str, Any]) -> TestClient:
    """Create an authenticated test client"""
    # Login to get token
    login_response = client.post(
        "/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )

    assert login_response.status_code == 200
    token_data = login_response.json()
    token = token_data["access_token"]

    # Set authorization header for future requests
    client.headers.update({"Authorization": f"Bearer {token}"})

    return client


@pytest.fixture
def test_application_data() -> Dict[str, Any]:
    """Test application data"""
    return {
        "full_name": "Ahmed Test User",
        "emirates_id": "784-1985-9876543-2",
        "phone": "+971501234567",
        "email": "ahmed@test.com"
    }


@pytest.fixture
def test_upload_files() -> Dict[str, bytes]:
    """Test upload files"""
    # Create mock PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF"

    # Create mock image content (minimal JPG header)
    jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\x00\xff\xd9"

    return {
        "bank_statement": pdf_content,
        "emirates_id": jpg_content
    }


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        upload_path = Path(temp_dir) / "uploads"
        upload_path.mkdir(exist_ok=True)
        yield upload_path


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama response for testing"""
    return {
        "model": "qwen2:1.5b",
        "response": '{"decision": "approved", "confidence": 0.85, "benefit_amount": 2500, "reasoning": "Test approval"}',
        "done": True
    }


@pytest.fixture
def mock_ocr_result():
    """Mock OCR result for testing"""
    return {
        "confidence": 0.9,
        "extracted_text": """
        EMIRATES NBD BANK
        Account Statement
        Account Holder: Ahmed Test User
        Account Number: 1234567890
        Monthly Income: 3500
        Account Balance: 15000
        """,
        "processing_time_ms": 1500
    }


@pytest.fixture
def mock_document_analysis():
    """Mock document analysis result"""
    return {
        "monthly_income": 3500.0,
        "account_balance": 15000.0,
        "account_holder": "Ahmed Test User",
        "bank_name": "Emirates NBD",
        "confidence": 0.9
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["OLLAMA_URL"] = "http://localhost:11434"

    yield

    # Cleanup
    if os.path.exists("test.db"):
        os.remove("test.db")


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Custom test markers
pytestmark = [
    pytest.mark.asyncio,
]