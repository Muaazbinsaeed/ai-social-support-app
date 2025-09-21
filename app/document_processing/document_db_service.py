"""
Document database service for managing document storage
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import json
from pathlib import Path

from app.document_processing.document_storage import Document, DocumentType, DocumentStatus
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class DocumentDBService:
    """Service for managing documents in database"""
    
    @staticmethod
    def create_document(
        db: Session,
        user_id: uuid.UUID,
        document_type: DocumentType,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        application_id: Optional[uuid.UUID] = None
    ) -> Document:
        """Create a new document record"""
        try:
            document = Document(
                user_id=user_id,
                application_id=application_id,
                document_type=document_type,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                status=DocumentStatus.UPLOADED,
                uploaded_at=datetime.utcnow()
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document created: {document.id} - {document_type}")
            return document
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create document: {str(e)}")
            raise
    
    @staticmethod
    def get_user_documents(
        db: Session,
        user_id: uuid.UUID,
        application_id: Optional[uuid.UUID] = None
    ) -> List[Document]:
        """Get all documents for a user"""
        query = db.query(Document).filter(Document.user_id == user_id)
        
        if application_id:
            query = query.filter(Document.application_id == application_id)
        
        return query.all()
    
    @staticmethod
    def get_document_by_type(
        db: Session,
        user_id: uuid.UUID,
        document_type: DocumentType,
        application_id: Optional[uuid.UUID] = None
    ) -> Optional[Document]:
        """Get a specific document type for a user"""
        query = db.query(Document).filter(
            Document.user_id == user_id,
            Document.document_type == document_type
        )
        
        if application_id:
            query = query.filter(Document.application_id == application_id)
        
        # Get the most recent document of this type
        return query.order_by(Document.uploaded_at.desc()).first()
    
    @staticmethod
    def update_document_status(
        db: Session,
        document_id: uuid.UUID,
        status: DocumentStatus
    ) -> Optional[Document]:
        """Update document status"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if not document:
                return None
            
            document.status = status
            
            # Update timestamps based on status
            if status == DocumentStatus.SUBMITTED:
                document.submitted_at = datetime.utcnow()
            elif status in [DocumentStatus.PROCESSED, DocumentStatus.ERROR]:
                document.processed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document {document_id} status updated to {status}")
            return document
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update document status: {str(e)}")
            raise
    
    @staticmethod
    def replace_document(
        db: Session,
        user_id: uuid.UUID,
        document_type: DocumentType,
        new_filename: str,
        new_file_path: str,
        new_file_size: int,
        new_mime_type: str,
        application_id: Optional[uuid.UUID] = None
    ) -> Document:
        """Replace an existing document"""
        try:
            # Get existing document
            existing = DocumentDBService.get_document_by_type(
                db, user_id, document_type, application_id
            )
            
            if existing:
                # Delete old file from disk if exists
                if existing.file_path and Path(existing.file_path).exists():
                    Path(existing.file_path).unlink()
                
                # Update existing document
                existing.filename = new_filename
                existing.file_path = new_file_path
                existing.file_size = new_file_size
                existing.mime_type = new_mime_type
                existing.status = DocumentStatus.UPLOADED
                existing.uploaded_at = datetime.utcnow()
                existing.submitted_at = None
                existing.processed_at = None
                existing.ocr_text = None
                existing.analysis_result = None
                existing.confidence_score = None
                
                db.commit()
                db.refresh(existing)
                
                logger.info(f"Document replaced: {existing.id}")
                return existing
            else:
                # Create new document
                return DocumentDBService.create_document(
                    db, user_id, document_type, new_filename,
                    new_file_path, new_file_size, new_mime_type,
                    application_id
                )
                
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to replace document: {str(e)}")
            raise
    
    @staticmethod
    def delete_document(
        db: Session,
        document_id: uuid.UUID
    ) -> bool:
        """Delete a document"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if not document:
                return False
            
            # Delete file from disk if exists
            if document.file_path and Path(document.file_path).exists():
                Path(document.file_path).unlink()
            
            db.delete(document)
            db.commit()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete document: {str(e)}")
            raise
    
    @staticmethod
    def reset_document_status(
        db: Session,
        document_id: uuid.UUID
    ) -> Optional[Document]:
        """Reset document status to allow re-processing"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if not document:
                return None
            
            document.status = DocumentStatus.RESET
            document.processed_at = None
            document.ocr_text = None
            document.analysis_result = None
            document.confidence_score = None
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document {document_id} reset for re-processing")
            return document
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to reset document: {str(e)}")
            raise
    
    @staticmethod
    def submit_documents(
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID
    ) -> List[Document]:
        """Mark documents as submitted"""
        try:
            documents = db.query(Document).filter(
                Document.user_id == user_id,
                Document.application_id == application_id
            ).all()
            
            for doc in documents:
                doc.status = DocumentStatus.SUBMITTED
                doc.submitted_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Documents submitted for application {application_id}")
            return documents
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to submit documents: {str(e)}")
            raise
    
    @staticmethod
    def get_document_summary(
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get document summary for an application"""
        documents = DocumentDBService.get_user_documents(db, user_id, application_id)
        
        summary = {
            'total': len(documents),
            'uploaded': 0,
            'submitted': 0,
            'processing': 0,
            'processed': 0,
            'error': 0,
            'documents': {}
        }
        
        for doc in documents:
            # Count by status
            if doc.status == DocumentStatus.UPLOADED:
                summary['uploaded'] += 1
            elif doc.status == DocumentStatus.SUBMITTED:
                summary['submitted'] += 1
            elif doc.status == DocumentStatus.PROCESSING:
                summary['processing'] += 1
            elif doc.status == DocumentStatus.PROCESSED:
                summary['processed'] += 1
            elif doc.status == DocumentStatus.ERROR:
                summary['error'] += 1
            
            # Add document details
            summary['documents'][doc.document_type.value] = {
                'id': str(doc.id),
                'filename': doc.filename,
                'status': doc.status.value,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                'submitted_at': doc.submitted_at.isoformat() if doc.submitted_at else None,
                'processed_at': doc.processed_at.isoformat() if doc.processed_at else None,
                'file_size': doc.file_size,
                'mime_type': doc.mime_type
            }
        
        return summary
