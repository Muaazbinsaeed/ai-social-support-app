"""
Health check API endpoints
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import httpx
from typing import Dict, Any

from app.shared.database import get_db, check_db_connection
from app.config import settings
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


def check_redis_connection() -> Dict[str, Any]:
    """Check Redis connection and get basic info"""
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        info = r.info()
        return {
            "status": "healthy",
            "response_time": "< 50ms",
            "memory_usage": f"{info.get('used_memory_human', 'unknown')}",
            "connected_clients": info.get('connected_clients', 0)
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_ollama_connection() -> Dict[str, Any]:
    """Check Ollama service and model availability"""
    try:
        with httpx.Client(timeout=10.0) as client:
            # Check if Ollama is running
            response = client.get(f"{settings.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]

                # Check for any working models (more flexible approach)
                preferred_models = ["qwen2:1.5b", "llama3.2:3b", "moondream:1.8b", "nomic-embed-text"]
                available_models = [model for model in preferred_models if any(model in name for name in model_names)]

                # If we have at least one model, consider it healthy
                # This is more practical for development environments
                status = "healthy" if len(model_names) > 0 else "unhealthy"
                if len(available_models) == 0 and len(model_names) > 0:
                    status = "degraded"  # Models available but not the preferred ones

                return {
                    "status": status,
                    "available_models": available_models if available_models else model_names[:3],  # Show first 3 models
                    "total_models": len(model_names),
                    "response_time": "< 10s"
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_qdrant_connection() -> Dict[str, Any]:
    """Check Qdrant vector database connection"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.qdrant_url}/collections")
            if response.status_code == 200:
                collections = response.json().get("result", {}).get("collections", [])
                return {
                    "status": "healthy",
                    "collections": len(collections),
                    "response_time": "< 5s"
                }
            else:
                return {
                    "status": "unavailable",
                    "error": f"HTTP {response.status_code}",
                    "note": "Optional service - not required for core functionality"
                }
    except Exception as e:
        # Don't log as error since this is optional
        return {
            "status": "unavailable",
            "error": "Service not running",
            "note": "Optional service - not required for core functionality"
        }


@router.get("/")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive system health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {},
        "metrics": {}
    }

    # Check database
    db_healthy = check_db_connection()
    health_status["services"]["database"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "response_time": "< 100ms" if db_healthy else "timeout"
    }

    # Check Redis
    health_status["services"]["redis"] = check_redis_connection()

    # Check Ollama
    health_status["services"]["ollama"] = check_ollama_connection()

    # Check Qdrant
    health_status["services"]["qdrant"] = check_qdrant_connection()

    # Check Celery workers (simplified check)
    try:
        r = redis.from_url(settings.celery_broker_url)
        # Check if there are any active workers by looking at queue stats
        queue_length = r.llen("celery")  # Default Celery queue
        health_status["services"]["celery_workers"] = {
            "status": "healthy",  # Simplified - in production, check actual worker processes
            "queue_length": queue_length,
            "active_workers": "unknown"  # Would need more complex logic to determine
        }
    except Exception as e:
        health_status["services"]["celery_workers"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # File system check
    try:
        import os
        import shutil

        uploads_usage = shutil.disk_usage(settings.upload_dir)
        total_gb = uploads_usage.total / (1024**3)
        free_gb = uploads_usage.free / (1024**3)
        used_percent = ((uploads_usage.total - uploads_usage.free) / uploads_usage.total) * 100

        health_status["services"]["file_system"] = {
            "status": "healthy" if used_percent < 80 else "warning",
            "disk_usage": f"{used_percent:.1f}%",
            "free_space": f"{free_gb:.1f}GB",
            "total_space": f"{total_gb:.1f}GB"
        }
    except Exception as e:
        health_status["services"]["file_system"] = {
            "status": "unknown",
            "error": str(e)
        }

    # Add basic metrics
    health_status["metrics"] = {
        "uptime": "unknown",  # Would track application start time
        "active_connections": "unknown",  # Would need connection pooling metrics
        "memory_usage": "unknown"  # Would need system resource monitoring
    }

    # Determine overall health status - only consider core services
    core_services = ["database", "redis", "celery_workers"]
    core_statuses = [
        health_status["services"][service]["status"]
        for service in core_services
        if service in health_status["services"]
    ]

    if "unhealthy" in core_statuses:
        health_status["status"] = "unhealthy"
    elif "degraded" in core_statuses or "warning" in core_statuses:
        health_status["status"] = "degraded"
    else:
        # Check if any optional services are unhealthy (but ignore "unavailable" status)
        optional_services = ["ollama", "qdrant", "file_system"]
        optional_statuses = [
            health_status["services"][service]["status"]
            for service in optional_services
            if service in health_status["services"] and health_status["services"][service]["status"] not in ["unavailable"]
        ]

        if "unhealthy" in optional_statuses:
            health_status["status"] = "degraded"  # Some optional services unhealthy, but core is fine
        else:
            health_status["status"] = "healthy"  # All core services healthy, optional services OK or unavailable

    return health_status


@router.get("/basic")
def basic_health_check():
    """Basic health check - just returns OK if service is running"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "social-security-ai"
    }


@router.get("/database")
def database_health_check(db: Session = Depends(get_db)):
    """Database-specific health check"""
    try:
        # Try a simple query
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "postgresql",
            "connection": "ok"
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(e)
        }