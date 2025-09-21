"""
Test configuration for running API tests without full app dependencies
"""

import pytest
import os
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock problematic imports
with patch.dict('sys.modules', {
    'easyocr': Mock(),
    'streamlit': Mock(),
    'plotly': Mock(),
    'celery': Mock(),
    'transformers': Mock(),
    'torch': Mock(),
    'langgraph': Mock(),
    'langchain': Mock(),
}):
    from app.main import app
    from app.shared.database import get_db, Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_module1.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

# Test client
test_client = TestClient(app)

@pytest.fixture(scope="session")
def client():
    """Test client fixture"""
    return test_client

@pytest.fixture(scope="module")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def clean_database():
    """Clean database between tests"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)