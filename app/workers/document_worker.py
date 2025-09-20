"""
Document processing background worker
"""

import time
from typing import Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.shared.database import SessionLocal
from app.document_processing.document_service import DocumentService
from app.application_flow.application_models import Application
from app.shared.exceptions import DocumentProcessingError
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='app.workers.document_worker.process_document_ocr')
def process_document_ocr(self, document_id: str) -> Dict[str, Any]:
    """
    Process document OCR extraction in background
    """
    db = SessionLocal()
    document_service = DocumentService()

    try:
        logger.info("Starting OCR processing task", document_id=document_id, task_id=self.request.id)

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting OCR processing', 'progress': 0}
        )

        # Process OCR
        success = document_service.process_document_ocr(db, document_id)

        if success:
            logger.info("OCR processing completed successfully", document_id=document_id)
            return {
                'status': 'completed',
                'document_id': document_id,
                'success': True,
                'message': 'OCR processing completed successfully'
            }
        else:
            logger.error("OCR processing failed", document_id=document_id)
            return {
                'status': 'failed',
                'document_id': document_id,
                'success': False,
                'message': 'OCR processing failed'
            }

    except Exception as e:
        logger.error("OCR processing task failed", error=str(e), document_id=document_id)
        # Don't raise exception - return error result instead
        return {
            'status': 'error',
            'document_id': document_id,
            'success': False,
            'error': str(e),
            'message': f'OCR processing error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.document_worker.process_document_analysis')
def process_document_analysis(self, document_id: str) -> Dict[str, Any]:
    """
    Process document AI analysis in background
    """
    db = SessionLocal()
    document_service = DocumentService()

    try:
        logger.info("Starting document analysis task", document_id=document_id, task_id=self.request.id)

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting AI analysis', 'progress': 0}
        )

        # Process analysis
        success = document_service.process_document_analysis(db, document_id)

        if success:
            logger.info("Document analysis completed successfully", document_id=document_id)
            return {
                'status': 'completed',
                'document_id': document_id,
                'success': True,
                'message': 'Document analysis completed successfully'
            }
        else:
            logger.error("Document analysis failed", document_id=document_id)
            return {
                'status': 'failed',
                'document_id': document_id,
                'success': False,
                'message': 'Document analysis failed'
            }

    except Exception as e:
        logger.error("Document analysis task failed", error=str(e), document_id=document_id)
        return {
            'status': 'error',
            'document_id': document_id,
            'success': False,
            'error': str(e),
            'message': f'Document analysis error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.document_worker.process_complete_document_pipeline')
def process_complete_document_pipeline(self, application_id: str, document_id: str) -> Dict[str, Any]:
    """
    Process complete document pipeline: OCR + Analysis
    """
    db = SessionLocal()
    document_service = DocumentService()

    try:
        logger.info(
            "Starting complete document processing pipeline",
            application_id=application_id,
            document_id=document_id,
            task_id=self.request.id
        )

        start_time = time.time()

        # Step 1: OCR Processing
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Processing OCR', 'progress': 20, 'step': 'ocr'}
        )

        ocr_success = document_service.process_document_ocr(db, document_id)
        if not ocr_success:
            return {
                'status': 'failed',
                'application_id': application_id,
                'document_id': document_id,
                'success': False,
                'failed_step': 'ocr',
                'message': 'OCR processing failed'
            }

        # Step 2: AI Analysis
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Processing AI analysis', 'progress': 60, 'step': 'analysis'}
        )

        analysis_success = document_service.process_document_analysis(db, document_id)
        if not analysis_success:
            return {
                'status': 'failed',
                'application_id': application_id,
                'document_id': document_id,
                'success': False,
                'failed_step': 'analysis',
                'message': 'Document analysis failed'
            }

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing', 'progress': 90, 'step': 'finalizing'}
        )

        processing_time = time.time() - start_time

        logger.info(
            "Complete document processing pipeline completed",
            application_id=application_id,
            document_id=document_id,
            processing_time=processing_time
        )

        return {
            'status': 'completed',
            'application_id': application_id,
            'document_id': document_id,
            'success': True,
            'processing_time': processing_time,
            'message': 'Document processing completed successfully'
        }

    except Exception as e:
        logger.error(
            "Complete document processing pipeline failed",
            error=str(e),
            application_id=application_id,
            document_id=document_id
        )
        return {
            'status': 'error',
            'application_id': application_id,
            'document_id': document_id,
            'success': False,
            'error': str(e),
            'message': f'Document processing error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.document_worker.process_application_documents')
def process_application_documents(self, application_id: str) -> Dict[str, Any]:
    """
    Process all documents for an application
    """
    db = SessionLocal()
    document_service = DocumentService()

    try:
        logger.info(
            "Starting application document processing",
            application_id=application_id,
            task_id=self.request.id
        )

        start_time = time.time()

        # Get all documents for the application
        documents = document_service.get_documents_by_application(db, application_id)

        if not documents:
            return {
                'status': 'failed',
                'application_id': application_id,
                'success': False,
                'message': 'No documents found for application'
            }

        total_documents = len(documents)
        processed_documents = 0
        failed_documents = []

        # Process each document
        for i, document in enumerate(documents):
            document_id = str(document.id)

            logger.info(
                f"Processing document {i+1}/{total_documents}",
                application_id=application_id,
                document_id=document_id,
                document_type=document.document_type
            )

            # Update progress
            progress = int((i / total_documents) * 80)  # Reserve 20% for final steps
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f'Processing document {i+1}/{total_documents}',
                    'progress': progress,
                    'document_type': document.document_type,
                    'current_document': i+1,
                    'total_documents': total_documents
                }
            )

            try:
                # Process OCR
                ocr_success = document_service.process_document_ocr(db, document_id)

                if ocr_success:
                    # Process Analysis
                    analysis_success = document_service.process_document_analysis(db, document_id)

                    if analysis_success:
                        processed_documents += 1
                        logger.info(
                            "Document processed successfully",
                            document_id=document_id,
                            document_type=document.document_type
                        )
                    else:
                        failed_documents.append({
                            'document_id': document_id,
                            'document_type': document.document_type,
                            'failed_step': 'analysis'
                        })
                else:
                    failed_documents.append({
                        'document_id': document_id,
                        'document_type': document.document_type,
                        'failed_step': 'ocr'
                    })

            except Exception as doc_error:
                logger.error(
                    "Document processing failed",
                    error=str(doc_error),
                    document_id=document_id
                )
                failed_documents.append({
                    'document_id': document_id,
                    'document_type': document.document_type,
                    'failed_step': 'error',
                    'error': str(doc_error)
                })

        # Final processing
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing document processing', 'progress': 95}
        )

        processing_time = time.time() - start_time

        # Determine overall success
        success_rate = processed_documents / total_documents if total_documents > 0 else 0
        overall_success = success_rate >= 0.5  # At least 50% success

        result = {
            'status': 'completed' if overall_success else 'partial_failure',
            'application_id': application_id,
            'success': overall_success,
            'processing_time': processing_time,
            'total_documents': total_documents,
            'processed_documents': processed_documents,
            'failed_documents': len(failed_documents),
            'success_rate': success_rate,
            'failed_document_details': failed_documents,
            'message': f'Processed {processed_documents}/{total_documents} documents successfully'
        }

        logger.info(
            "Application document processing completed",
            application_id=application_id,
            result=result
        )

        return result

    except Exception as e:
        logger.error(
            "Application document processing failed",
            error=str(e),
            application_id=application_id
        )
        return {
            'status': 'error',
            'application_id': application_id,
            'success': False,
            'error': str(e),
            'message': f'Application document processing error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.document_worker.retry_failed_document')
def retry_failed_document(self, document_id: str, retry_step: str = None) -> Dict[str, Any]:
    """
    Retry failed document processing
    """
    db = SessionLocal()
    document_service = DocumentService()

    try:
        logger.info(
            "Retrying failed document processing",
            document_id=document_id,
            retry_step=retry_step,
            task_id=self.request.id
        )

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Retrying {retry_step or "processing"}', 'progress': 10}
        )

        # Retry processing
        success = document_service.retry_document_processing(db, document_id, retry_step)

        if success:
            logger.info("Document retry completed successfully", document_id=document_id)
            return {
                'status': 'completed',
                'document_id': document_id,
                'success': True,
                'retry_step': retry_step,
                'message': 'Document retry completed successfully'
            }
        else:
            logger.error("Document retry failed", document_id=document_id)
            return {
                'status': 'failed',
                'document_id': document_id,
                'success': False,
                'retry_step': retry_step,
                'message': 'Document retry failed'
            }

    except Exception as e:
        logger.error("Document retry task failed", error=str(e), document_id=document_id)
        return {
            'status': 'error',
            'document_id': document_id,
            'success': False,
            'error': str(e),
            'message': f'Document retry error: {str(e)}'
        }
    finally:
        db.close()