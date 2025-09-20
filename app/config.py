"""
Configuration management for Social Security AI System
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation"""
    model_config = {"extra": "allow", "env_file": ".env", "case_sensitive": False}

    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Security
    jwt_secret_key: str = "development-jwt-secret-key-32-chars-minimum-length"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # Database
    database_url: str = "postgresql://admin:postgres123@postgres:5432/social_security_ai"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # AI Configuration
    ollama_url: str = "http://ollama:11434"
    ollama_request_timeout: int = 300
    ollama_max_retries: int = 3

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"

    # File Upload
    max_file_size: int = 52428800  # 50MB
    allowed_extensions: str = "pdf,jpg,jpeg,png"
    upload_dir: str = "./uploads"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_worker_concurrency: int = 2
    celery_task_time_limit: int = 600
    celery_task_soft_time_limit: int = 300

    # Monitoring
    enable_metrics: bool = True
    health_check_interval: int = 30

    # Business Rules
    income_threshold_aed: int = 4000
    balance_threshold_aed: int = 1500
    confidence_threshold: float = 0.7
    auto_approval_threshold: float = 0.8

    # Test Users
    test_user1_username: str = "user1"
    test_user1_password: str = "password123"
    test_user2_username: str = "user2"
    test_user2_password: str = "password123"

    @field_validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters long')
        return v

    @field_validator('allowed_extensions')
    def validate_extensions(cls, v):
        return [ext.strip().lower() for ext in v.split(',')]



# Global settings instance
settings = Settings()


# AI Model Configuration
AI_MODELS = {
    "multimodal_analysis": {
        "name": "moondream:1.8b",
        "purpose": "Document understanding and structured data extraction",
        "timeout": 300
    },
    "decision_making": {
        "name": "qwen2:1.5b",
        "purpose": "Eligibility reasoning and decision making",
        "timeout": 60
    },
    "embeddings": {
        "name": "nomic-embed-text",
        "purpose": "Document vectorization and similarity search",
        "timeout": 30
    }
}


# Application State Configuration
APPLICATION_STATES = {
    "DRAFT": "draft",
    "FORM_SUBMITTED": "form_submitted",
    "DOCUMENTS_UPLOADED": "documents_uploaded",
    "SCANNING_DOCUMENTS": "scanning_documents",
    "OCR_COMPLETED": "ocr_completed",
    "ANALYZING_INCOME": "analyzing_income",
    "ANALYZING_IDENTITY": "analyzing_identity",
    "ANALYSIS_COMPLETED": "analysis_completed",
    "MAKING_DECISION": "making_decision",
    "DECISION_COMPLETED": "decision_completed",
    "APPROVED": "approved",
    "REJECTED": "rejected",
    "NEEDS_REVIEW": "needs_review",
    "PARTIAL_SUCCESS": "partial_success",
    "MANUAL_REVIEW_REQUIRED": "manual_review_required"
}


# State transition messages for user feedback
STATE_MESSAGES = {
    "form_submitted": "📝 Application form received and validated",
    "documents_uploaded": "📤 Documents received, starting analysis...",
    "scanning_documents": "🔍 Scanning documents for text extraction...",
    "ocr_completed": "✅ Text extraction completed successfully",
    "analyzing_income": "💰 Analyzing bank statement for income verification",
    "analyzing_identity": "🆔 Verifying Emirates ID details...",
    "analysis_completed": "✅ Document analysis completed",
    "making_decision": "⚖️ Evaluating eligibility criteria...",
    "decision_completed": "✅ Decision processing completed",
    "needs_review": "👀 Partial data processed, manual review required",
    "approved": "🎉 APPROVED: Eligible for benefits",
    "rejected": "❌ Application does not meet eligibility criteria",
    "partial_success": "⚠️ Processing completed with partial data"
}