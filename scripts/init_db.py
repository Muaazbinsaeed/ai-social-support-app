#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and sets up the database schema
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import init_db, check_db_connection, engine
from app.shared.logging_config import setup_logging, get_logger

# Import all models to ensure they're registered with SQLAlchemy
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.document_processing.document_models import Document, DocumentProcessingLog
from app.decision_making.decision_models import Decision, DecisionAuditLog

# Setup logging
setup_logging()
logger = get_logger(__name__)


def main():
    """Initialize the database"""
    try:
        logger.info("Starting database initialization...")

        # Check database connection first
        if not check_db_connection():
            logger.error("Cannot connect to database. Please check your database configuration.")
            sys.exit(1)

        # Initialize database (create all tables)
        init_db()

        logger.info("Database initialization completed successfully!")
        logger.info("Created tables:")
        logger.info("  - users (User authentication and profiles)")
        logger.info("  - applications (Application data and state)")
        logger.info("  - workflow_states (Detailed workflow tracking)")
        logger.info("  - documents (Document storage and processing)")
        logger.info("  - document_processing_logs (Processing step logs)")
        logger.info("  - decisions (AI decision results)")
        logger.info("  - decision_audit_logs (Decision audit trail)")

    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()