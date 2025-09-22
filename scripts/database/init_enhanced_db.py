#!/usr/bin/env python3
"""
Initialize database with enhanced status tracking
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.shared.database import engine, Base
from app.document_processing.document_models import Document
from app.application_flow.application_models import Application, WorkflowState
from app.user_management.user_models import User

def init_enhanced_database():
    """Initialize database with new enhanced status fields"""
    try:
        print("🔄 Initializing database with enhanced status tracking...")

        # Create all tables (this will add new columns if model is updated)
        Base.metadata.create_all(bind=engine)

        print("✅ Database initialized successfully with enhanced status tracking")
        print("✅ New columns added: ocr_status, multimodal_status, ocr_progress, multimodal_progress")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_enhanced_database()
    if success:
        print("\n🎊 Enhanced status tracking is ready!")
        print("You can now test the new endpoints:")
        print("- GET /workflow/status-enhanced/{app_id}")
        print("- GET /workflow/processing-details/{app_id}")
        print("- GET /workflow/progress/{app_id}")
    sys.exit(0 if success else 1)