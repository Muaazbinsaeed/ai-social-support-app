#!/usr/bin/env python3
"""
Add updated_at column to applications table
"""

import os
import sys
from sqlalchemy import text

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.shared.database import engine

def add_updated_at_column():
    """Add the missing updated_at column to applications table"""
    try:
        print("🔄 Adding updated_at column to applications table...")

        with engine.connect() as conn:
            # Add column with IF NOT EXISTS check
            sql = "ALTER TABLE applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"
            print(f"Executing: {sql}")
            conn.execute(text(sql))
            conn.commit()

        print("✅ Updated_at column added successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        return False

if __name__ == "__main__":
    success = add_updated_at_column()
    if success:
        print("\n🎊 Updated_at column is ready!")
    sys.exit(0 if success else 1)