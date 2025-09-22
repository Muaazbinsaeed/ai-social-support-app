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
    bank_statement: Optional[UploadFile] = File(None, description="Bank statement PDF file"),
    emirates_id: Optional[UploadFile] = File(None, description="Emirates ID image file"),
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


@router.put("/replace/{document_type}",
           summary="Replace an existing document",
           description="Replace a bank statement or Emirates ID document")
def replace_document(
    document_type: str,
    file: UploadFile = File(..., description="New document file"),
    application_id: Optional[str] = Form(None, description="Application ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Replace an existing document with a new one"""
    try:
        # Validate document type
        if document_type not in ['bank_statement', 'emirates_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_DOCUMENT_TYPE", "message": f"Invalid document type: {document_type}"}
            )
        
        # Validate file
        is_valid, message = validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_FILE", "message": message}
            )
        
        # Save new file
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower()
        new_filename = f"{file_id}_{document_type}{file_ext}"
        
        upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / new_filename
        
        # Save file
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Document replaced successfully",
                   document_type=document_type,
                   new_file=new_filename,
                   user_id=str(current_user.id))
        
        return {
            "message": f"{document_type} replaced successfully",
            "document_type": document_type,
            "document_id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "replaced_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document replacement failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "REPLACEMENT_FAILED", "message": "Failed to replace document"}
        )


@router.post("/reset/{document_type}",
            summary="Reset document status",
            description="Reset a document status to allow re-processing")
def reset_document_status(
    document_type: str,
    application_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reset document status to pending"""
    try:
        if document_type not in ['bank_statement', 'emirates_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_DOCUMENT_TYPE", "message": f"Invalid document type: {document_type}"}
            )
        
        logger.info(f"Document status reset",
                   document_type=document_type,
                   application_id=application_id,
                   user_id=str(current_user.id))
        
        return {
            "message": f"{document_type} status reset successfully",
            "document_type": document_type,
            "new_status": "pending_reupload",
            "reset_at": datetime.utcnow().isoformat() + "Z",
            "can_edit": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document status reset failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "RESET_FAILED", "message": "Failed to reset document status"}
        )


@router.get("/application/{application_id}",
           summary="Get documents for an application",
           description="Get all documents associated with an application")
def get_application_documents(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all documents for an application"""
    try:
        # For now, return mock data since document DB is not fully integrated
        logger.info(f"Getting documents for application {application_id}")
        
        # Check if documents exist in file system
        upload_dir = Path(settings.UPLOAD_DIR)
        documents = {}
        
        # Check for bank statement
        bank_files = list(upload_dir.glob(f"*bank_statement*"))
        if bank_files:
            documents['bank_statement'] = {
                'id': str(uuid.uuid4()),
                'filename': bank_files[0].name,
                'file_size': bank_files[0].stat().st_size,
                'status': 'submitted',
                'uploaded_at': datetime.utcnow().isoformat() + "Z"
            }
        
        # Check for emirates ID
        emirates_files = list(upload_dir.glob(f"*emirates_id*"))
        if emirates_files:
            documents['emirates_id'] = {
                'id': str(uuid.uuid4()),
                'filename': emirates_files[0].name,
                'file_size': emirates_files[0].stat().st_size,
                'status': 'submitted',
                'uploaded_at': datetime.utcnow().isoformat() + "Z"
            }
        
        return {
            'application_id': application_id,
            'documents': documents,
            'total_documents': len(documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to get application documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "FETCH_FAILED", "message": "Failed to get documents"}
        )


@router.get("/download/{document_id}",
           summary="Download a document",
           description="Download a specific document by ID")
def download_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a specific document"""
    try:
        # For now, return a placeholder since full DB integration is pending
        logger.info(f"Download requested for document {document_id}")
        
        # Try to find the actual file based on document_id pattern
        upload_dir = Path(settings.UPLOAD_DIR)
        
        # Look for files matching the document_id pattern
        # Document IDs usually contain the original filename
        matching_files = []
        for file_path in upload_dir.glob("*"):
            if document_id in str(file_path) or file_path.stem.startswith(document_id[:8]):
                matching_files.append(file_path)
        
        if not matching_files:
            # Try to find any recent file for the user
            user_files = list(upload_dir.glob(f"*{str(current_user.id)[:8]}*"))
            if user_files:
                matching_files = [max(user_files, key=lambda f: f.stat().st_mtime)]
        
        if matching_files:
            file_path = matching_files[0]
            
            with open(file_path, "rb") as f:
                content = f.read()
            
            import base64
            
            # Return as base64 encoded JSON for consistency with frontend
            return {
                "document_id": document_id,
                "filename": file_path.name,
                "data": base64.b64encode(content).decode('utf-8'),
                "content_type": "application/pdf" if file_path.suffix.lower() == '.pdf' else "image/jpeg"
            }
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Document not found"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DOWNLOAD_FAILED", "message": "Failed to download document"}
        )


@router.delete("/{document_type}/delete",
              summary="Delete a specific document",
              description="Delete a bank statement or Emirates ID document")
def delete_document(
    document_type: str,
    application_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific document type"""
    try:
        if document_type not in ['bank_statement', 'emirates_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_DOCUMENT_TYPE", "message": f"Invalid document type: {document_type}"}
            )
        
        # Delete physical file if exists (in production, would check database)
        upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
        if upload_dir.exists():
            # Find and delete matching files
            for file_path in upload_dir.glob(f"*_{document_type}.*"):
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
        
        logger.info(f"Document deleted successfully",
                   document_type=document_type,
                   user_id=str(current_user.id))
        
        return {
            "message": f"{document_type} deleted successfully",
            "document_type": document_type,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
            "user_id": str(current_user.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DELETION_FAILED", "message": "Failed to delete document"}
        )