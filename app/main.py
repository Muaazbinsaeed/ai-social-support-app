"""
Main FastAPI application
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import time
import uuid
from contextlib import asynccontextmanager

from app.config import settings
from app.shared.logging_config import setup_logging, get_logger
from app.shared.exceptions import ApplicationException
from app.api.auth_router import router as auth_router
from app.api.health_router import router as health_router
from app.api.document_router import router as document_router
from app.api.workflow_router import router as workflow_router
from app.api.application_router import router as application_router
from app.api.analysis_router import router as analysis_router
from app.api.ocr_router import router as ocr_router
from app.api.decision_router import router as decision_router
from app.api.chatbot_router import router as chatbot_router
from app.api.user_router import router as user_router
from app.api.document_management_router import router as document_management_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Social Security AI application", environment=settings.environment)

    # Initialize database on startup
    try:
        from app.shared.database import init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Social Security AI application")


# Create FastAPI application
app = FastAPI(
    title="Social Security AI Workflow Automation System",
    description="AI-powered government social security application processing system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8005", "http://127.0.0.1:8005"],  # Streamlit frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Content type validation middleware
@app.middleware("http")
async def content_type_validation_middleware(request: Request, call_next):
    """Validate content types for POST/PUT requests"""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "").lower()

        # Check if it's a JSON endpoint (most of our API endpoints)
        if request.url.path.startswith("/auth/") or request.url.path.startswith("/api/"):
            if content_type and not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": "UNSUPPORTED_MEDIA_TYPE",
                        "message": f"Content-Type '{content_type}' is not supported. Please use 'application/json'",
                        "supported_types": ["application/json"],
                        "request_id": str(uuid.uuid4())
                    }
                )

    response = await call_next(request)
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Add to logger context
    logger_with_id = logger.bind(request_id=request_id)
    request.state.logger = logger_with_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Log request completion
    logger_with_id.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int(process_time * 1000)
    )

    response.headers["X-Request-ID"] = request_id
    return response


# Global exception handlers
@app.exception_handler(ApplicationException)
async def application_exception_handler(request: Request, exc: ApplicationException):
    """Handle custom application exceptions"""
    request_logger = getattr(request.state, 'logger', logger)
    request_logger.error(
        "Application exception occurred",
        error_type=exc.__class__.__name__,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details
    )

    status_code = status.HTTP_400_BAD_REQUEST
    if "Authentication" in exc.__class__.__name__:
        status_code = status.HTTP_401_UNAUTHORIZED
    elif "Authorization" in exc.__class__.__name__:
        status_code = status.HTTP_403_FORBIDDEN
    elif "NotFound" in exc.__class__.__name__:
        status_code = status.HTTP_404_NOT_FOUND
    elif "Duplicate" in exc.__class__.__name__ or "Conflict" in exc.__class__.__name__:
        status_code = status.HTTP_409_CONFLICT

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    request_logger = getattr(request.state, 'logger', logger)

    # Convert errors to JSON-serializable format
    def serialize_error(error):
        """Convert error objects to JSON-serializable format"""
        serialized = {}
        for key, value in error.items():
            if key == 'ctx' and value:
                # Handle context objects
                serialized[key] = {k: str(v) for k, v in value.items()}
            elif isinstance(value, (str, int, float, bool, type(None))):
                serialized[key] = value
            elif isinstance(value, (list, tuple)):
                serialized[key] = list(value)
            else:
                serialized[key] = str(value)
        return serialized

    serialized_errors = [serialize_error(error) for error in exc.errors()]

    request_logger.warning("Validation error occurred", errors=serialized_errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": serialized_errors,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_logger = getattr(request.state, 'logger', logger)

    # Safe error message handling - convert any non-serializable types
    error_message = str(exc)
    error_type = exc.__class__.__name__

    request_logger.error(
        "Unexpected exception occurred",
        error_type=error_type,
        error_message=error_message,
        path=str(request.url.path),
        method=str(request.method)
    )

    # Determine appropriate error message based on exception type
    if "JSON" in error_message or "decode" in error_message.lower():
        user_message = "Invalid request format. Please ensure you're sending valid JSON with Content-Type: application/json"
        error_code = "INVALID_REQUEST_FORMAT"
    elif "content-type" in error_message.lower() or "media type" in error_message.lower():
        user_message = "Unsupported content type. Please use Content-Type: application/json"
        error_code = "UNSUPPORTED_CONTENT_TYPE"
    else:
        user_message = "An unexpected error occurred"
        error_code = "INTERNAL_ERROR"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": error_code,
            "message": user_message,
            "request_id": getattr(request.state, 'request_id', None),
            "error_type": error_type
        }
    )


# Include routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(document_router)
app.include_router(workflow_router)
app.include_router(application_router)
app.include_router(analysis_router)
app.include_router(ocr_router)
app.include_router(decision_router)
app.include_router(chatbot_router)
app.include_router(user_router)
app.include_router(document_management_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Social Security AI Workflow Automation System",
        "version": "1.0.0",
        "description": "AI-powered government social security application processing",
        "features": [
            "2-minute application processing",
            "99% automation rate",
            "Real-time status tracking",
            "Graceful failure handling",
            "Local AI processing"
        ],
        "endpoints": {
            "documentation": "/docs",
            "health_check": "/health",
            "authentication": "/auth",
            "documents": "/documents",
            "workflow": "/workflow",
            "applications": "/applications",
            "analysis": "/analysis",
            "ocr": "/ocr",
            "decisions": "/decisions",
            "chatbot": "/chatbot",
            "users": "/users",
            "document_management": "/document-management"
        }
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Social Security AI API",
        version="1.0.0",
        description="Comprehensive API for AI-powered social security application processing",
        routes=app.routes,
    )

    # Add custom schema information
    openapi_schema["info"]["x-logo"] = {
        "url": "https://via.placeholder.com/200x50/0066cc/ffffff?text=Social+Security+AI"
    }

    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.socialsecurity.gov.ae", "description": "Production server (example)"}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )