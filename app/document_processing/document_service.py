"""
Document processing business logic
"""

import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import json

from app.document_processing.document_models import Document, DocumentProcessingLog
from app.document_processing.document_schemas import (
    DocumentUpload, DocumentAnalysisResult, DocumentProcessingStatus
)
from app.document_processing.ocr_service import OCRService
from app.shared.llm_client import OllamaClient
from app.shared.file_utils import FileManager
from app.shared.exceptions import (
    DocumentProcessingError, DocumentNotFoundError, ValidationError
)
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for document processing operations"""

    def __init__(self):
        self.ocr_service = OCRService()
        self.llm_client = OllamaClient()

    def create_document_record(self, db: Session, application_id: str, user_id: str,
                             document_upload: DocumentUpload, file_path: str) -> Document:
        """Create a document record in the database"""
        try:
            document = Document(
                application_id=application_id,
                user_id=user_id,
                document_type=document_upload.document_type,
                original_filename=document_upload.original_filename,
                file_path=file_path,
                file_size=document_upload.file_size,
                mime_type=document_upload.mime_type,
                processing_status="uploaded"
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            logger.info(
                "Document record created",
                document_id=str(document.id),
                application_id=application_id,
                document_type=document_upload.document_type
            )

            return document

        except Exception as e:
            db.rollback()
            logger.error("Failed to create document record", error=str(e))
            raise DocumentProcessingError(f"Failed to create document record: {str(e)}", "DOCUMENT_CREATE_ERROR")

    def get_document_by_id(self, db: Session, document_id: str) -> Document:
        """Get document by ID"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise DocumentNotFoundError(f"Document with ID {document_id} not found", "DOCUMENT_NOT_FOUND")
        return document

    def get_documents_by_application(self, db: Session, application_id: str) -> List[Document]:
        """Get all documents for an application"""
        return db.query(Document).filter(Document.application_id == application_id).all()

    def update_processing_status(self, db: Session, document_id: str, status: str,
                               error_message: Optional[str] = None) -> Document:
        """Update document processing status"""
        try:
            document = self.get_document_by_id(db, document_id)
            document.processing_status = status

            if error_message:
                document.error_message = error_message

            if status in ["analyzed", "failed"]:
                document.processed_at = db.execute("SELECT NOW()").scalar()

            db.commit()
            db.refresh(document)

            logger.info(
                "Document processing status updated",
                document_id=document_id,
                status=status,
                error=error_message
            )

            return document

        except Exception as e:
            db.rollback()
            logger.error("Failed to update document status", error=str(e), document_id=document_id)
            raise

    def log_processing_step(self, db: Session, document_id: str, processing_step: str,
                          step_status: str, step_result: Optional[Dict[str, Any]] = None,
                          confidence_score: Optional[Decimal] = None,
                          processing_time_ms: Optional[int] = None,
                          error_message: Optional[str] = None) -> DocumentProcessingLog:
        """Log a processing step"""
        try:
            log_entry = DocumentProcessingLog(
                document_id=document_id,
                processing_step=processing_step,
                step_status=step_status,
                step_result=step_result,
                confidence_score=confidence_score,
                processing_time_ms=processing_time_ms,
                error_message=error_message
            )

            if step_status == "started":
                log_entry.started_at = db.execute("SELECT NOW()").scalar()
            elif step_status in ["completed", "failed"]:
                log_entry.completed_at = db.execute("SELECT NOW()").scalar()

            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)

            return log_entry

        except Exception as e:
            db.rollback()
            logger.error("Failed to log processing step", error=str(e))
            raise

    def process_document_ocr(self, db: Session, document_id: str) -> bool:
        """Process document OCR extraction"""
        try:
            document = self.get_document_by_id(db, document_id)

            # Log start of OCR processing
            self.log_processing_step(db, document_id, "ocr", "started")

            # Update status
            self.update_processing_status(db, document_id, "processing")

            start_time = time.time()

            # Perform OCR
            ocr_result = self.ocr_service.extract_text(document.file_path)

            processing_time = int((time.time() - start_time) * 1000)

            # Validate OCR quality
            if not self.ocr_service.validate_text_quality(ocr_result, document.document_type):
                error_msg = "OCR quality insufficient for processing"
                self.log_processing_step(
                    db, document_id, "ocr", "failed",
                    error_message=error_msg,
                    processing_time_ms=processing_time
                )
                self.update_processing_status(db, document_id, "failed", error_msg)
                return False

            # Save OCR results
            document.extracted_text = ocr_result.extracted_text
            document.ocr_confidence = Decimal(str(ocr_result.confidence))
            document.ocr_processing_time_ms = processing_time

            # Log successful OCR
            self.log_processing_step(
                db, document_id, "ocr", "completed",
                step_result={"text_length": len(ocr_result.extracted_text)},
                confidence_score=Decimal(str(ocr_result.confidence)),
                processing_time_ms=processing_time
            )

            # Update status
            self.update_processing_status(db, document_id, "ocr_completed")

            logger.info(
                "OCR processing completed successfully",
                document_id=document_id,
                confidence=ocr_result.confidence,
                text_length=len(ocr_result.extracted_text)
            )

            return True

        except Exception as e:
            logger.error("OCR processing failed", error=str(e), document_id=document_id)
            self.log_processing_step(
                db, document_id, "ocr", "failed",
                error_message=str(e)
            )
            self.update_processing_status(db, document_id, "failed", str(e))
            return False

    def process_document_analysis(self, db: Session, document_id: str) -> bool:
        """Process document with AI analysis"""
        try:
            document = self.get_document_by_id(db, document_id)

            if not document.extracted_text:
                raise DocumentProcessingError("No OCR text available for analysis", "NO_OCR_TEXT")

            # Log start of analysis
            self.log_processing_step(db, document_id, "multimodal_analysis", "started")

            start_time = time.time()

            # Perform AI analysis
            analysis_result = self.llm_client.analyze_document_multimodal(
                document.extracted_text,
                document.document_type
            )

            processing_time = int((time.time() - start_time) * 1000)

            # Save analysis results
            document.structured_data = analysis_result
            document.analysis_processing_time_ms = processing_time

            # Log successful analysis
            confidence = analysis_result.get("confidence", 0.5)
            self.log_processing_step(
                db, document_id, "multimodal_analysis", "completed",
                step_result=analysis_result,
                confidence_score=Decimal(str(confidence)),
                processing_time_ms=processing_time
            )

            # Update status
            self.update_processing_status(db, document_id, "analyzed")

            logger.info(
                "Document analysis completed successfully",
                document_id=document_id,
                confidence=confidence,
                document_type=document.document_type
            )

            return True

        except Exception as e:
            logger.error("Document analysis failed", error=str(e), document_id=document_id)
            self.log_processing_step(
                db, document_id, "multimodal_analysis", "failed",
                error_message=str(e)
            )
            self.update_processing_status(db, document_id, "failed", str(e))
            return False

    def get_processing_status(self, db: Session, document_id: str) -> DocumentProcessingStatus:
        """Get detailed processing status for a document"""
        try:
            document = self.get_document_by_id(db, document_id)

            # Get processing logs
            logs = db.query(DocumentProcessingLog).filter(
                DocumentProcessingLog.document_id == document_id
            ).order_by(DocumentProcessingLog.created_at).all()

            # Determine current step and progress
            steps_completed = [log.processing_step for log in logs if log.step_status == "completed"]
            current_step = None
            progress_percentage = 0

            if document.processing_status == "uploaded":
                progress_percentage = 10
            elif document.processing_status == "processing":
                current_step = "ocr"
                progress_percentage = 30
            elif document.processing_status == "ocr_completed":
                current_step = "multimodal_analysis"
                progress_percentage = 60
            elif document.processing_status == "analyzed":
                progress_percentage = 100
            elif document.processing_status == "failed":
                progress_percentage = 0

            # Estimate completion time (simplified)
            estimated_completion_time = None
            if progress_percentage < 100 and progress_percentage > 0:
                remaining_steps = 2 - len(steps_completed)
                estimated_completion_time = remaining_steps * 30  # 30 seconds per step estimate

            return DocumentProcessingStatus(
                document_id=document_id,
                processing_status=document.processing_status,
                current_step=current_step,
                progress_percentage=progress_percentage,
                steps_completed=steps_completed,
                estimated_completion_time=estimated_completion_time,
                error_message=document.error_message,
                can_retry=document.processing_status == "failed"
            )

        except Exception as e:
            logger.error("Failed to get processing status", error=str(e), document_id=document_id)
            raise DocumentProcessingError(f"Failed to get processing status: {str(e)}", "STATUS_ERROR")

    def retry_document_processing(self, db: Session, document_id: str,
                                retry_step: Optional[str] = None) -> bool:
        """Retry failed document processing"""
        try:
            document = self.get_document_by_id(db, document_id)

            if document.processing_status not in ["failed", "analyzed"]:
                raise ValidationError("Document is not in a state that allows retry", "INVALID_RETRY_STATE")

            logger.info(
                "Retrying document processing",
                document_id=document_id,
                retry_step=retry_step
            )

            # Increment retry count
            document.retry_count += 1
            document.error_message = None

            # Determine what to retry
            if retry_step == "ocr" or not document.extracted_text:
                # Retry OCR
                return self.process_document_ocr(db, document_id)
            else:
                # Retry analysis
                return self.process_document_analysis(db, document_id)

        except Exception as e:
            logger.error("Document retry failed", error=str(e), document_id=document_id)
            self.update_processing_status(db, document_id, "failed", str(e))
            return False

    def get_extraction_summary(self, db: Session, application_id: str) -> Dict[str, Any]:
        """Get summary of extracted data from all documents"""
        try:
            documents = self.get_documents_by_application(db, application_id)

            summary = {
                "total_documents": len(documents),
                "processed_documents": 0,
                "failed_documents": 0,
                "extracted_data": {}
            }

            for doc in documents:
                if doc.processing_status == "analyzed" and doc.structured_data:
                    summary["processed_documents"] += 1
                    summary["extracted_data"][doc.document_type] = doc.structured_data
                elif doc.processing_status == "failed":
                    summary["failed_documents"] += 1

            return summary

        except Exception as e:
            logger.error("Failed to get extraction summary", error=str(e), application_id=application_id)
            return {"error": str(e)}