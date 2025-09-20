"""
Decision making background worker
"""

import time
from typing import Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.shared.database import SessionLocal
from app.decision_making.decision_service import DecisionService
from app.document_processing.document_service import DocumentService
from app.application_flow.application_models import Application
from app.shared.exceptions import AIServiceError, ApplicationNotFoundError
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='app.workers.decision_worker.make_eligibility_decision')
def make_eligibility_decision(self, application_id: str) -> Dict[str, Any]:
    """
    Make eligibility decision for an application in background
    """
    db = SessionLocal()
    decision_service = DecisionService()
    document_service = DocumentService()

    try:
        logger.info(
            "Starting eligibility decision task",
            application_id=application_id,
            task_id=self.request.id
        )

        start_time = time.time()

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Preparing decision data', 'progress': 10}
        )

        # Get application data
        application = db.query(Application).filter(
            Application.id == application_id
        ).first()

        if not application:
            raise ApplicationNotFoundError(f"Application {application_id} not found", "APPLICATION_NOT_FOUND")

        # Prepare applicant data
        applicant_data = {
            'full_name': application.full_name,
            'emirates_id': application.emirates_id,
            'phone': application.phone,
            'email': application.email,
            'application_id': application_id
        }

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Gathering document analysis', 'progress': 30}
        )

        # Get extracted data from documents
        extraction_summary = document_service.get_extraction_summary(db, application_id)
        extracted_data = extraction_summary.get('extracted_data', {})

        if not extracted_data:
            logger.warning("No extracted data available for decision", application_id=application_id)
            # Continue with empty data - decision service will handle gracefully

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Analyzing eligibility criteria', 'progress': 50}
        )

        # Make decision
        decision = decision_service.make_eligibility_decision(
            db=db,
            application_id=application_id,
            applicant_data=applicant_data,
            extracted_data=extracted_data
        )

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing decision', 'progress': 90}
        )

        processing_time = time.time() - start_time

        # Update application with decision results
        application.decision = decision.outcome
        application.decision_confidence = decision.confidence_score
        application.decision_reasoning = decision.reasoning
        application.decision_at = db.execute("SELECT NOW()").scalar()

        # Set status based on decision
        if decision.outcome == 'approved':
            application.status = 'approved'
        elif decision.outcome == 'rejected':
            application.status = 'rejected'
        else:
            application.status = 'needs_review'

        db.commit()

        logger.info(
            "Eligibility decision completed",
            application_id=application_id,
            decision_id=str(decision.id),
            outcome=decision.outcome,
            confidence=float(decision.confidence_score),
            processing_time=processing_time
        )

        return {
            'status': 'completed',
            'application_id': application_id,
            'decision_id': str(decision.id),
            'success': True,
            'outcome': decision.outcome,
            'confidence': float(decision.confidence_score),
            'benefit_amount': float(decision.benefit_amount) if decision.benefit_amount else 0,
            'processing_time': processing_time,
            'message': f'Decision completed: {decision.outcome}'
        }

    except Exception as e:
        logger.error(
            "Eligibility decision task failed",
            error=str(e),
            application_id=application_id
        )

        # Try to update application status to indicate error
        try:
            application = db.query(Application).filter(
                Application.id == application_id
            ).first()
            if application:
                application.status = 'needs_review'
                application.decision = 'needs_review'
                application.decision_reasoning = {'error': str(e), 'fallback': True}
                db.commit()
        except:
            pass  # Ignore secondary errors

        return {
            'status': 'error',
            'application_id': application_id,
            'success': False,
            'error': str(e),
            'message': f'Decision processing error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.decision_worker.process_complete_application')
def process_complete_application(self, application_id: str) -> Dict[str, Any]:
    """
    Process complete application workflow: Documents + Decision
    """
    try:
        logger.info(
            "Starting complete application processing",
            application_id=application_id,
            task_id=self.request.id
        )

        start_time = time.time()

        # Step 1: Process all documents
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Processing documents', 'progress': 10, 'step': 'documents'}
        )

        # Call document processing task
        from app.workers.document_worker import process_application_documents
        doc_result = process_application_documents.apply(args=[application_id]).get()

        if not doc_result.get('success', False):
            # Check if we have any processed documents
            processed_count = doc_result.get('processed_documents', 0)
            if processed_count == 0:
                return {
                    'status': 'failed',
                    'application_id': application_id,
                    'success': False,
                    'failed_step': 'documents',
                    'message': 'No documents could be processed',
                    'document_result': doc_result
                }

        # Step 2: Make eligibility decision
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Making eligibility decision', 'progress': 70, 'step': 'decision'}
        )

        # Wait a moment for document processing to be fully committed
        time.sleep(2)

        # Call decision making task
        decision_result = make_eligibility_decision.apply(args=[application_id]).get()

        if not decision_result.get('success', False):
            return {
                'status': 'failed',
                'application_id': application_id,
                'success': False,
                'failed_step': 'decision',
                'message': 'Decision making failed',
                'document_result': doc_result,
                'decision_result': decision_result
            }

        # Step 3: Finalize
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing application', 'progress': 95, 'step': 'finalizing'}
        )

        processing_time = time.time() - start_time

        result = {
            'status': 'completed',
            'application_id': application_id,
            'success': True,
            'processing_time': processing_time,
            'outcome': decision_result.get('outcome'),
            'confidence': decision_result.get('confidence'),
            'benefit_amount': decision_result.get('benefit_amount'),
            'document_result': doc_result,
            'decision_result': decision_result,
            'message': f'Application processing completed: {decision_result.get("outcome")}'
        }

        logger.info(
            "Complete application processing finished",
            application_id=application_id,
            result=result
        )

        return result

    except Exception as e:
        logger.error(
            "Complete application processing failed",
            error=str(e),
            application_id=application_id
        )
        return {
            'status': 'error',
            'application_id': application_id,
            'success': False,
            'error': str(e),
            'message': f'Application processing error: {str(e)}'
        }


@celery_app.task(bind=True, name='app.workers.decision_worker.reprocess_decision')
def reprocess_decision(self, application_id: str, force_reprocess: bool = False) -> Dict[str, Any]:
    """
    Reprocess decision for an application
    """
    db = SessionLocal()
    decision_service = DecisionService()

    try:
        logger.info(
            "Starting decision reprocessing",
            application_id=application_id,
            force_reprocess=force_reprocess,
            task_id=self.request.id
        )

        # Check if decision already exists
        existing_decision = decision_service.get_decision_by_application(db, application_id)

        if existing_decision and not force_reprocess:
            logger.info("Decision already exists, skipping reprocessing", application_id=application_id)
            return {
                'status': 'skipped',
                'application_id': application_id,
                'success': True,
                'existing_outcome': existing_decision.outcome,
                'message': 'Decision already exists, use force_reprocess=True to override'
            }

        # Delete existing decision if force reprocessing
        if existing_decision and force_reprocess:
            db.delete(existing_decision)
            db.commit()
            logger.info("Deleted existing decision for reprocessing", application_id=application_id)

        # Call decision making task
        decision_result = make_eligibility_decision.apply(args=[application_id]).get()

        return decision_result

    except Exception as e:
        logger.error(
            "Decision reprocessing failed",
            error=str(e),
            application_id=application_id
        )
        return {
            'status': 'error',
            'application_id': application_id,
            'success': False,
            'error': str(e),
            'message': f'Decision reprocessing error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.decision_worker.batch_process_applications')
def batch_process_applications(self, application_ids: list) -> Dict[str, Any]:
    """
    Process multiple applications in batch
    """
    try:
        logger.info(
            "Starting batch application processing",
            application_count=len(application_ids),
            task_id=self.request.id
        )

        start_time = time.time()
        results = []
        successful_count = 0
        failed_count = 0

        for i, application_id in enumerate(application_ids):
            # Update progress
            progress = int((i / len(application_ids)) * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f'Processing application {i+1}/{len(application_ids)}',
                    'progress': progress,
                    'current_application': application_id,
                    'completed': i,
                    'total': len(application_ids)
                }
            )

            try:
                # Process individual application
                app_result = process_complete_application.apply(args=[application_id]).get()
                results.append(app_result)

                if app_result.get('success', False):
                    successful_count += 1
                else:
                    failed_count += 1

                logger.info(
                    f"Batch processing application {i+1}/{len(application_ids)}",
                    application_id=application_id,
                    success=app_result.get('success', False)
                )

            except Exception as app_error:
                logger.error(
                    "Batch processing application failed",
                    error=str(app_error),
                    application_id=application_id
                )
                results.append({
                    'status': 'error',
                    'application_id': application_id,
                    'success': False,
                    'error': str(app_error)
                })
                failed_count += 1

        processing_time = time.time() - start_time

        batch_result = {
            'status': 'completed',
            'success': True,
            'processing_time': processing_time,
            'total_applications': len(application_ids),
            'successful_applications': successful_count,
            'failed_applications': failed_count,
            'success_rate': successful_count / len(application_ids) if application_ids else 0,
            'results': results,
            'message': f'Batch processing completed: {successful_count}/{len(application_ids)} successful'
        }

        logger.info(
            "Batch application processing completed",
            batch_result=batch_result
        )

        return batch_result

    except Exception as e:
        logger.error(
            "Batch application processing failed",
            error=str(e),
            application_ids=application_ids
        )
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'Batch processing error: {str(e)}'
        }