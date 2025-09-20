#!/usr/bin/env python3
"""
Reset system for development - clears all data and reinitializes
"""

import sys
import os
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import SessionLocal, engine, Base
from app.shared.logging_config import setup_logging, get_logger
from app.config import settings

# Import all models to ensure they're registered
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.document_processing.document_models import Document, DocumentProcessingLog
from app.decision_making.decision_models import Decision, DecisionAuditLog

# Setup logging
setup_logging()
logger = get_logger(__name__)


def confirm_reset():
    """Confirm with user before proceeding with reset"""
    print("\n⚠️  WARNING: SYSTEM RESET")
    print("="*50)
    print("This will permanently delete:")
    print("  • All user accounts")
    print("  • All applications")
    print("  • All uploaded documents")
    print("  • All processing logs")
    print("  • All decisions and audit trails")
    print("="*50)

    response = input("\nAre you sure you want to continue? (type 'RESET' to confirm): ")

    if response != 'RESET':
        print("❌ Reset cancelled.")
        sys.exit(0)

    print("✅ Reset confirmed. Proceeding...")


def drop_all_tables():
    """Drop all database tables"""
    try:
        logger.info("Dropping all database tables...")

        # Drop all tables
        Base.metadata.drop_all(bind=engine)

        logger.info("All database tables dropped successfully")
        print("🗑️  Database tables dropped")

    except Exception as e:
        logger.error(f"Failed to drop database tables: {str(e)}")
        raise


def recreate_all_tables():
    """Recreate all database tables"""
    try:
        logger.info("Recreating all database tables...")

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.info("All database tables recreated successfully")
        print("🏗️  Database tables recreated")

    except Exception as e:
        logger.error(f"Failed to recreate database tables: {str(e)}")
        raise


def clear_uploaded_files():
    """Clear all uploaded files"""
    try:
        logger.info("Clearing uploaded files...")

        upload_dir = Path(settings.upload_dir)

        if upload_dir.exists():
            # Remove all files and subdirectories but keep the main directory
            for item in upload_dir.iterdir():
                if item.is_file():
                    item.unlink()
                    logger.info(f"Deleted file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Deleted directory: {item}")

        # Recreate .gitkeep file
        gitkeep_file = upload_dir / ".gitkeep"
        gitkeep_file.write_text("# Keep this directory for document uploads")

        logger.info("Uploaded files cleared successfully")
        print("📁 Uploaded files cleared")

    except Exception as e:
        logger.error(f"Failed to clear uploaded files: {str(e)}")
        raise


def clear_log_files():
    """Clear log files"""
    try:
        logger.info("Clearing log files...")

        log_dir = Path("./logs")

        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                log_file.unlink()
                logger.info(f"Deleted log file: {log_file}")

        # Recreate .gitkeep file
        gitkeep_file = log_dir / ".gitkeep"
        gitkeep_file.write_text("# Keep this directory for application logs")

        logger.info("Log files cleared successfully")
        print("📄 Log files cleared")

    except Exception as e:
        logger.error(f"Failed to clear log files: {str(e)}")
        raise


def recreate_test_users():
    """Recreate test user accounts"""
    try:
        logger.info("Recreating test user accounts...")

        from app.user_management.user_service import UserService
        from app.user_management.auth_schemas import UserCreate

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

        created_users = []
        for user_data in test_users:
            try:
                user_create = UserCreate(**user_data)
                user = UserService.create_user(db, user_create)
                created_users.append(user.username)
                logger.info(f"Created test user: {user.username}")
            except Exception as e:
                logger.error(f"Failed to create user {user_data['username']}: {str(e)}")

        db.close()

        logger.info(f"Test users recreated: {created_users}")
        print(f"👥 Test users recreated: {', '.join(created_users)}")

    except Exception as e:
        logger.error(f"Failed to recreate test users: {str(e)}")
        raise


def clear_redis_data():
    """Clear Redis data"""
    try:
        logger.info("Clearing Redis data...")

        import redis

        # Clear main Redis database
        r = redis.from_url(settings.redis_url)
        r.flushdb()

        # Clear Celery broker database
        broker_r = redis.from_url(settings.celery_broker_url)
        broker_r.flushdb()

        # Clear Celery result backend database
        result_r = redis.from_url(settings.celery_result_backend)
        result_r.flushdb()

        logger.info("Redis data cleared successfully")
        print("🔴 Redis data cleared")

    except Exception as e:
        logger.warning(f"Failed to clear Redis data (may be offline): {str(e)}")
        print("⚠️  Redis data clearing skipped (service may be offline)")


def reset_qdrant_data():
    """Reset Qdrant vector database"""
    try:
        logger.info("Resetting Qdrant data...")

        import httpx

        with httpx.Client(timeout=10.0) as client:
            # Get all collections
            response = client.get(f"{settings.qdrant_url}/collections")

            if response.status_code == 200:
                collections = response.json().get("result", {}).get("collections", [])

                # Delete each collection
                for collection in collections:
                    collection_name = collection.get("name")
                    if collection_name:
                        delete_response = client.delete(f"{settings.qdrant_url}/collections/{collection_name}")
                        if delete_response.status_code == 200:
                            logger.info(f"Deleted Qdrant collection: {collection_name}")

        logger.info("Qdrant data reset successfully")
        print("🔵 Qdrant data reset")

    except Exception as e:
        logger.warning(f"Failed to reset Qdrant data (may be offline): {str(e)}")
        print("⚠️  Qdrant data reset skipped (service may be offline)")


def main():
    """Main reset function"""
    try:
        print("🔄 Social Security AI System Reset")

        # Confirm with user
        confirm_reset()

        print("\n🚀 Starting system reset...")

        # Step 1: Clear external services
        print("\n1️⃣  Clearing external services...")
        clear_redis_data()
        reset_qdrant_data()

        # Step 2: Clear files
        print("\n2️⃣  Clearing files...")
        clear_uploaded_files()
        clear_log_files()

        # Step 3: Reset database
        print("\n3️⃣  Resetting database...")
        drop_all_tables()
        recreate_all_tables()

        # Step 4: Recreate test users
        print("\n4️⃣  Recreating test users...")
        recreate_test_users()

        # Step 5: Success message
        print("\n✅ System reset completed successfully!")

        print("\n" + "="*60)
        print("SYSTEM RESET COMPLETED")
        print("="*60)
        print("🎉 Your Social Security AI system has been reset to a clean state.")
        print("\n📋 What was reset:")
        print("   ✅ Database tables (dropped and recreated)")
        print("   ✅ Test user accounts (recreated)")
        print("   ✅ Uploaded documents (cleared)")
        print("   ✅ Log files (cleared)")
        print("   ✅ Redis cache and queues (cleared)")
        print("   ✅ Qdrant vector database (reset)")

        print("\n🚀 Next steps:")
        print("   1. Start the system: docker-compose up -d")
        print("   2. Wait for all services to be ready (~2 minutes)")
        print("   3. Run health check: python scripts/health_check.py")
        print("   4. Generate test data: python scripts/generate_test_data.py")
        print("   5. Access dashboard: http://localhost:8005")

        print("\n🔑 Test credentials:")
        print("   • Username: user1 | Password: password123")
        print("   • Username: user2 | Password: password123")
        print("   • Username: admin | Password: admin123")
        print("="*60)

    except Exception as e:
        logger.error(f"System reset failed: {str(e)}")
        print(f"\n❌ System reset failed: {str(e)}")
        print("\n🔧 Manual cleanup may be required:")
        print("   1. Stop all services: docker-compose down")
        print("   2. Remove volumes: docker-compose down -v")
        print("   3. Restart: docker-compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    main()