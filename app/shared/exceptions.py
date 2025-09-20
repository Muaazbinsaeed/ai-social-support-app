"""
Custom exception classes for the application
"""

from typing import Optional, Dict, Any


class ApplicationException(Exception):
    """Base exception class for application-specific errors"""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(ApplicationException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(ApplicationException):
    """Raised when user doesn't have permission for an action"""
    pass


class ValidationError(ApplicationException):
    """Raised when input validation fails"""
    pass


class DocumentProcessingError(ApplicationException):
    """Raised when document processing fails"""
    pass


class AIServiceError(ApplicationException):
    """Raised when AI service calls fail"""
    pass


class WorkflowError(ApplicationException):
    """Raised when workflow transitions are invalid"""
    pass


class DatabaseError(ApplicationException):
    """Raised when database operations fail"""
    pass


class FileStorageError(ApplicationException):
    """Raised when file storage operations fail"""
    pass


class ConfigurationError(ApplicationException):
    """Raised when configuration is invalid"""
    pass


class ExternalServiceError(ApplicationException):
    """Raised when external services are unavailable"""
    pass


# Specific business logic exceptions
class ApplicationNotFoundError(ApplicationException):
    """Raised when application is not found"""
    pass


class DocumentNotFoundError(ApplicationException):
    """Raised when document is not found"""
    pass


class InvalidStateTransitionError(WorkflowError):
    """Raised when trying to transition to an invalid state"""
    pass


class ProcessingTimeoutError(ApplicationException):
    """Raised when processing takes too long"""
    pass


class InsufficientDataError(ApplicationException):
    """Raised when not enough data is available for processing"""
    pass


class UserNotFoundError(ApplicationException):
    """Raised when user is not found"""
    pass


class DuplicateUserError(ApplicationException):
    """Raised when trying to create a user that already exists"""
    pass