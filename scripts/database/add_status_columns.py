#!/usr/bin/env python3
"""
Add new status tracking columns to existing database
"""

import os
import sys
from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = "postgresql://admin:postgres123@localhost:5432/social_security_ai"

def add_status_columns():
    """Add new status tracking columns to documents table"""
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Add new columns if they don't exist
            try:
                conn.execute(text("""
                    ALTER TABLE documents
                    ADD COLUMN IF NOT EXISTS ocr_status VARCHAR(20) DEFAULT 'pending',
                    ADD COLUMN IF NOT EXISTS multimodal_status VARCHAR(20) DEFAULT 'pending',
                    ADD COLUMN IF NOT EXISTS ocr_progress INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS multimodal_progress INTEGER DEFAULT 0;
                """))
                conn.commit()
                print("✅ Successfully added new status columns to documents table")

                # Verify columns exist
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'documents'
                    AND column_name IN ('ocr_status', 'multimodal_status', 'ocr_progress', 'multimodal_progress');
                """))

                columns = [row[0] for row in result]
                print(f"✅ Verified columns exist: {columns}")

                return True

            except Exception as e:
                print(f"❌ Failed to add columns: {e}")
                return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = add_status_columns()
    sys.exit(0 if success else 1)