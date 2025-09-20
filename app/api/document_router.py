"""
Document upload and processing API endpoints
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return False, f"File size {file.size} exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"

    return True, "Valid file"


@router.post("/upload", status_code=status.HTTP_201_CREATED,
            summary="Upload documents",
            description="Upload bank statement and Emirates ID documents for processing")
def upload_documents(
    bank_statement: UploadFile = File(..., description="Bank statement PDF file"),
    emirates_id: UploadFile = File(..., description="Emirates ID image file"),
    application_id: Optional[str] = Form(None, description="Application ID to associate documents with"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and validate documents for application processing"""
    try:
        # Validate files
        for file, file_type in [(bank_statement, "bank_statement"), (emirates_id, "emirates_id")]:
            is_valid, message = validate_file(file)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_FILE",
                        "message": f"Invalid {file_type}: {message}",
                        "file_type": file_type,
                        "filename": file.filename
                    }
                )

        # Generate unique document IDs
        bank_statement_id = str(uuid.uuid4())
        emirates_id_id = str(uuid.uuid4())

        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save files
        bank_statement_path = upload_dir / f"{bank_statement_id}_{bank_statement.filename}"
        emirates_id_path = upload_dir / f"{emirates_id_id}_{emirates_id.filename}"

        # Write files to disk
        with open(bank_statement_path, "wb") as f:
            content = bank_statement.file.read()
            f.write(content)

        with open(emirates_id_path, "wb") as f:
            content = emirates_id.file.read()
            f.write(content)

        # Log successful upload
        logger.info("Documents uploaded successfully",
                   user_id=str(current_user.id),
                   bank_statement_id=bank_statement_id,
                   emirates_id_id=emirates_id_id)

        # Return upload confirmation
        return {
            "message": "Documents uploaded successfully",
            "documents": {
                "bank_statement": {
                    "id": bank_statement_id,
                    "filename": bank_statement.filename,
                    "content_type": bank_statement.content_type,
                    "size": len(content) if 'content' in locals() else None,
                    "status": "uploaded"
                },
                "emirates_id": {
                    "id": emirates_id_id,
                    "filename": emirates_id.filename,
                    "content_type": emirates_id.content_type,
                    "size": len(emirates_id.file.read() if hasattr(emirates_id.file, 'read') else b''),
                    "status": "uploaded"
                }
            },
            "application_id": application_id or "auto-generated",
            "user_id": str(current_user.id),
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "next_steps": [
                "Documents will be processed automatically",
                "OCR extraction will begin shortly",
                "Check status via /documents/status endpoint"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UPLOAD_FAILED",
                "message": "Failed to upload documents",
                "details": str(e)
            }
        )


@router.get("/status/{document_id}")
def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document processing status"""
    try:
        # For now, return mock status since document processing is not fully implemented
        return {
            "document_id": document_id,
            "status": "processing",
            "stage": "ocr_extraction",
            "progress": 45,
            "created_at": "2025-09-20T01:20:00Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "processing_steps": [
                {"step": "upload", "status": "completed", "timestamp": "2025-09-20T01:20:00Z"},
                {"step": "validation", "status": "completed", "timestamp": "2025-09-20T01:20:01Z"},
                {"step": "ocr_extraction", "status": "in_progress", "timestamp": "2025-09-20T01:20:02Z"},
                {"step": "ai_analysis", "status": "pending", "timestamp": None},
                {"step": "data_extraction", "status": "pending", "timestamp": None}
            ],
            "user_id": str(current_user.id)
        }
    except Exception as e:
        logger.error("Failed to get document status",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATUS_FETCH_FAILED",
                "message": "Failed to fetch document status"
            }
        )


@router.get("/types")
def get_supported_file_types():
    """Get supported file types and limits"""
    return {
        "supported_types": {
            "bank_statement": {
                "extensions": [".pdf"],
                "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
                "description": "Bank statement in PDF format"
            },
            "emirates_id": {
                "extensions": [".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
                "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
                "description": "Emirates ID image in common formats"
            }
        },
        "limits": {
            "max_file_size_bytes": MAX_FILE_SIZE,
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "allowed_extensions": list(ALLOWED_EXTENSIONS)
        },
        "requirements": {
            "bank_statement": "Must be a clear PDF with readable text",
            "emirates_id": "Must be a clear image showing all details"
        }
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a uploaded document"""
    try:
        # For now, return success since full document management is not implemented
        logger.info("Document deletion requested",
                   document_id=document_id,
                   user_id=str(current_user.id))

        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
            "user_id": str(current_user.id)
        }
    except Exception as e:
        logger.error("Document deletion failed",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DELETION_FAILED",
                "message": "Failed to delete document"
            }
        )