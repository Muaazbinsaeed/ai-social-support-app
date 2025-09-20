"""
Complete Document Management CRUD API endpoints
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.shared.database import get_db
from app.dependencies import get_current_active_user, get_current_admin_user
from app.user_management.user_models import User
from app.document_processing.document_models import Document, DocumentProcessingLog
from app.application_flow.application_models import Application
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/document-management", tags=["document-management"])

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.txt', '.doc', '.docx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Pydantic models
class DocumentResponse(BaseModel):
    id: str
    application_id: Optional[str] = None
    user_id: str
    document_type: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    processing_status: str
    ocr_confidence: Optional[float] = None
    extracted_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    uploaded_at: str
    processed_at: Optional[str] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int
    page: int
    page_size: int

class DocumentUploadRequest(BaseModel):
    document_type: str
    application_id: Optional[str] = None

class DocumentUpdateRequest(BaseModel):
    document_type: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class ProcessingLogResponse(BaseModel):
    id: str
    document_id: str
    processing_step: str
    step_status: str
    step_result: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return False, f"File size {file.size} exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"

    return True, "Valid file"


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED,
            summary="Upload document",
            description="Upload a single document with metadata")
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    document_type: str = Form(..., description="Type of document (bank_statement, emirates_id, etc.)"),
    application_id: Optional[str] = Form(None, description="Associated application ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a single document"""
    try:
        # Validate file
        is_valid, message = validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_FILE",
                    "message": message,
                    "filename": file.filename
                }
            )

        # Validate application_id if provided
        if application_id:
            application = db.query(Application).filter(
                Application.id == application_id,
                Application.user_id == current_user.id
            ).first()
            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "APPLICATION_NOT_FOUND",
                        "message": "Application not found or not accessible"
                    }
                )

        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique document ID and file path
        document_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix if file.filename else ""
        safe_filename = f"{document_id}_{file.filename}" if file.filename else f"{document_id}{file_extension}"
        file_path = upload_dir / safe_filename

        # Read and save file
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Create document record
        document = Document(
            id=document_id,
            application_id=application_id,
            user_id=current_user.id,
            document_type=document_type,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(file_content),
            mime_type=file.content_type,
            processing_status="uploaded"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info("Document uploaded successfully",
                   document_id=document_id,
                   user_id=str(current_user.id),
                   document_type=document_type,
                   file_size=len(file_content))

        return DocumentResponse(
            id=str(document.id),
            application_id=str(document.application_id) if document.application_id else None,
            user_id=str(document.user_id),
            document_type=document.document_type,
            original_filename=document.original_filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            processing_status=document.processing_status,
            ocr_confidence=float(document.ocr_confidence) if document.ocr_confidence else None,
            extracted_text=document.extracted_text,
            structured_data=document.structured_data,
            error_message=document.error_message,
            uploaded_at=document.uploaded_at.isoformat() + "Z" if document.uploaded_at else None,
            processed_at=document.processed_at.isoformat() + "Z" if document.processed_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UPLOAD_FAILED",
                "message": "Failed to upload document"
            }
        )


@router.get("/", response_model=DocumentListResponse,
           summary="List documents",
           description="Get paginated list of user's documents")
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status_filter: Optional[str] = Query(None, description="Filter by processing status"),
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's documents with filtering and pagination"""
    try:
        # Build query
        query = db.query(Document).filter(Document.user_id == current_user.id)

        # Apply filters
        if document_type:
            query = query.filter(Document.document_type == document_type)

        if status_filter:
            query = query.filter(Document.processing_status == status_filter)

        if application_id:
            query = query.filter(Document.application_id == application_id)

        # Get total count
        total_count = query.count()

        # Apply pagination
        documents = query.order_by(desc(Document.uploaded_at)).offset((page - 1) * page_size).limit(page_size).all()

        # Build response
        document_responses = []
        for doc in documents:
            doc_response = DocumentResponse(
                id=str(doc.id),
                application_id=str(doc.application_id) if doc.application_id else None,
                user_id=str(doc.user_id),
                document_type=doc.document_type,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                processing_status=doc.processing_status,
                ocr_confidence=float(doc.ocr_confidence) if doc.ocr_confidence else None,
                extracted_text=doc.extracted_text,
                structured_data=doc.structured_data,
                error_message=doc.error_message,
                uploaded_at=doc.uploaded_at.isoformat() + "Z" if doc.uploaded_at else None,
                processed_at=doc.processed_at.isoformat() + "Z" if doc.processed_at else None
            )
            document_responses.append(doc_response)

        logger.info("Documents list retrieved",
                   user_id=str(current_user.id),
                   total_count=total_count,
                   page=page)

        return DocumentListResponse(
            documents=document_responses,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list documents",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOCUMENTS_LIST_FAILED",
                "message": "Failed to retrieve documents list"
            }
        )


@router.get("/{document_id}", response_model=DocumentResponse,
           summary="Get document details",
           description="Retrieve detailed information about a specific document")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document details"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        logger.info("Document details retrieved",
                   document_id=document_id,
                   user_id=str(current_user.id))

        return DocumentResponse(
            id=str(document.id),
            application_id=str(document.application_id) if document.application_id else None,
            user_id=str(document.user_id),
            document_type=document.document_type,
            original_filename=document.original_filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            processing_status=document.processing_status,
            ocr_confidence=float(document.ocr_confidence) if document.ocr_confidence else None,
            extracted_text=document.extracted_text,
            structured_data=document.structured_data,
            error_message=document.error_message,
            uploaded_at=document.uploaded_at.isoformat() + "Z" if document.uploaded_at else None,
            processed_at=document.processed_at.isoformat() + "Z" if document.processed_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document details",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOCUMENT_FETCH_FAILED",
                "message": "Failed to retrieve document details"
            }
        )


@router.put("/{document_id}", response_model=DocumentResponse,
           summary="Update document",
           description="Update document metadata and structured data")
async def update_document(
    document_id: str,
    update_data: DocumentUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update document metadata"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(document, field, value)

        db.commit()
        db.refresh(document)

        logger.info("Document updated",
                   document_id=document_id,
                   user_id=str(current_user.id),
                   updated_fields=list(update_dict.keys()))

        return DocumentResponse(
            id=str(document.id),
            application_id=str(document.application_id) if document.application_id else None,
            user_id=str(document.user_id),
            document_type=document.document_type,
            original_filename=document.original_filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            processing_status=document.processing_status,
            ocr_confidence=float(document.ocr_confidence) if document.ocr_confidence else None,
            extracted_text=document.extracted_text,
            structured_data=document.structured_data,
            error_message=document.error_message,
            uploaded_at=document.uploaded_at.isoformat() + "Z" if document.uploaded_at else None,
            processed_at=document.processed_at.isoformat() + "Z" if document.processed_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update document",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOCUMENT_UPDATE_FAILED",
                "message": "Failed to update document"
            }
        )


@router.delete("/{document_id}",
              summary="Delete document",
              description="Delete a document and its associated file")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete document"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        # Delete file from disk
        try:
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file from disk: {str(e)}")

        # Delete processing logs
        db.query(DocumentProcessingLog).filter(
            DocumentProcessingLog.document_id == document.id
        ).delete()

        # Delete document record
        db.delete(document)
        db.commit()

        logger.info("Document deleted",
                   document_id=document_id,
                   user_id=str(current_user.id))

        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "deleted_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOCUMENT_DELETE_FAILED",
                "message": "Failed to delete document"
            }
        )


@router.get("/{document_id}/download",
           summary="Download document file",
           description="Download the original document file")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download document file"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        if not document.file_path or not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "FILE_NOT_FOUND",
                    "message": "Document file not found on disk"
                }
            )

        logger.info("Document downloaded",
                   document_id=document_id,
                   user_id=str(current_user.id))

        return FileResponse(
            path=document.file_path,
            filename=document.original_filename or f"document_{document_id}",
            media_type=document.mime_type or "application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download document",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOWNLOAD_FAILED",
                "message": "Failed to download document"
            }
        )


@router.get("/{document_id}/processing-logs", response_model=List[ProcessingLogResponse],
           summary="Get document processing logs",
           description="Retrieve processing history for a document")
async def get_processing_logs(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document processing logs"""
    try:
        # Verify document access
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        # Get processing logs
        logs = db.query(DocumentProcessingLog).filter(
            DocumentProcessingLog.document_id == document_id
        ).order_by(DocumentProcessingLog.created_at).all()

        log_responses = []
        for log in logs:
            log_response = ProcessingLogResponse(
                id=str(log.id),
                document_id=str(log.document_id),
                processing_step=log.processing_step,
                step_status=log.step_status,
                step_result=log.step_result,
                confidence_score=float(log.confidence_score) if log.confidence_score else None,
                processing_time_ms=log.processing_time_ms,
                error_message=log.error_message,
                created_at=log.created_at.isoformat() + "Z" if log.created_at else None
            )
            log_responses.append(log_response)

        logger.info("Processing logs retrieved",
                   document_id=document_id,
                   user_id=str(current_user.id),
                   log_count=len(log_responses))

        return log_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get processing logs",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "LOGS_FETCH_FAILED",
                "message": "Failed to retrieve processing logs"
            }
        )


@router.get("/types/supported",
           summary="Get supported document types",
           description="Get list of supported document types and file formats")
async def get_supported_types():
    """Get supported document types and file formats"""
    return {
        "document_types": [
            "bank_statement",
            "emirates_id",
            "salary_certificate",
            "passport",
            "visa",
            "employment_contract",
            "medical_report",
            "utility_bill",
            "other"
        ],
        "supported_formats": {
            "images": [".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
            "documents": [".pdf", ".txt", ".doc", ".docx"],
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "max_file_size_bytes": MAX_FILE_SIZE
        },
        "processing_capabilities": [
            "OCR text extraction",
            "Multimodal AI analysis",
            "Structured data extraction",
            "Document classification",
            "Quality validation"
        ]
    }