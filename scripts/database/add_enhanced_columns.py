#!/usr/bin/env python3
"""
Add enhanced status tracking columns to documents table
"""

import os
import sys
from sqlalchemy import text

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.shared.database import engine

def add_enhanced_columns():
    """Add the missing enhanced status tracking columns"""
    try:
        print("🔄 Adding enhanced status tracking columns...")

        with engine.connect() as conn:
            # Add columns one by one with IF NOT EXISTS check
            columns_to_add = [
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_status VARCHAR(20) DEFAULT 'pending';",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS multimodal_status VARCHAR(20) DEFAULT 'pending';",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_progress INTEGER DEFAULT 0;",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS multimodal_progress INTEGER DEFAULT 0;",
                "CREATE INDEX IF NOT EXISTS idx_documents_ocr_status ON documents(ocr_status);",
                "CREATE INDEX IF NOT EXISTS idx_documents_multimodal_status ON documents(multimodal_status);"
            ]

            for sql in columns_to_add:
                print(f"Executing: {sql}")
                conn.execute(text(sql))
                conn.commit()

        print("✅ Enhanced status tracking columns added successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to add columns: {e}")
        return False

if __name__ == "__main__":
    success = add_enhanced_columns()
    if success:
        print("\n🎊 Enhanced status tracking columns are ready!")
    sys.exit(0 if success else 1)