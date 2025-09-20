"""
Structured logging configuration
"""

import structlog
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from app.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application
    """

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_timestamp,
            add_request_id,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_timestamp(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamp to log entries"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_request_id(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add request ID if available in context"""
    # This will be populated by FastAPI middleware
    request_id = getattr(logger, 'request_id', None)
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    """
    return structlog.get_logger(name)


# Log levels and their purposes
LOG_LEVELS = {
    "DEBUG": "Detailed information for debugging",
    "INFO": "General information about application flow",
    "WARNING": "Something unexpected but application continues",
    "ERROR": "Error occurred but application continues",
    "CRITICAL": "Serious error, application may be unable to continue"
}


# Logging examples for different scenarios
def log_user_action(logger: structlog.BoundLogger, user_id: str, action: str, **kwargs) -> None:
    """Log user actions with context"""
    logger.info(
        "User action performed",
        user_id=user_id,
        action=action,
        **kwargs
    )


def log_processing_step(logger: structlog.BoundLogger, application_id: str, step: str,
                       duration_ms: int = None, **kwargs) -> None:
    """Log processing steps with timing"""
    log_data = {
        "application_id": application_id,
        "processing_step": step,
        **kwargs
    }
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    logger.info("Processing step completed", **log_data)


def log_error_with_context(logger: structlog.BoundLogger, error: Exception,
                          context: Dict[str, Any] = None) -> None:
    """Log errors with full context"""
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if context:
        log_data.update(context)

    logger.error("Error occurred", **log_data)