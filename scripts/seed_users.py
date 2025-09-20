#!/usr/bin/env python3
"""
Seed script for creating test user accounts
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import SessionLocal
from app.user_management.user_service import UserService
from app.user_management.auth_schemas import UserCreate
from app.shared.logging_config import setup_logging, get_logger
from app.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_test_users():
    """Create test user accounts"""
    db = SessionLocal()

    test_users = [
        {
            "username": settings.test_user1_username,
            "email": "user1@test.com",
            "password": settings.test_user1_password,
            "full_name": "Ahmed Test User"
        },
        {
            "username": settings.test_user2_username,
            "email": "user2@test.com",
            "password": settings.test_user2_password,
            "full_name": "Fatima Test User"
        },
        {
            "username": "admin",
            "email": "admin@test.com",
            "password": "admin123",
            "full_name": "System Administrator"
        },
        {
            "username": "demo",
            "email": "demo@test.com",
            "password": "demo123",
            "full_name": "Demo User"
        }
    ]

    try:
        for user_data in test_users:
            try:
                user_create = UserCreate(**user_data)
                user = UserService.create_user(db, user_create)
                logger.info(f"Created test user: {user.username} (ID: {user.id})")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Test user {user_data['username']} already exists, skipping...")
                else:
                    logger.error(f"Failed to create user {user_data['username']}: {str(e)}")

        logger.info("Test user creation completed!")

        print("\n" + "="*60)
        print("TEST USER ACCOUNTS CREATED")
        print("="*60)
        print("Username: user1     | Password: password123")
        print("Username: user2     | Password: password123")
        print("Username: admin     | Password: admin123")
        print("Username: demo      | Password: demo123")
        print("="*60)
        print("Use these credentials to log into the system")
        print("Dashboard: http://localhost:8005")
        print("API Docs:  http://localhost:8000/docs")
        print("="*60)

    except Exception as e:
        logger.error(f"Failed to create test users: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_test_users()