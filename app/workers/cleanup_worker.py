"""
Cleanup and maintenance background worker
"""

import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.workers.celery_app import celery_app
from app.shared.database import SessionLocal, check_db_connection
from app.shared.file_utils import FileManager
from app.application_flow.application_models import Application
from app.document_processing.document_models import Document, DocumentProcessingLog
from app.decision_making.decision_models import Decision, DecisionAuditLog
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='app.workers.cleanup_worker.cleanup_old_files')
def cleanup_old_files(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old uploaded files
    """
    try:
        logger.info(
            "Starting file cleanup task",
            days_old=days_old,
            task_id=self.request.id
        )

        start_time = time.time()

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Scanning for old files', 'progress': 10}
        )

        # Clean up old files
        deleted_count = FileManager.cleanup_old_files(days_old)

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Cleaning up database references', 'progress': 70}
        )

        # Clean up orphaned database records
        db = SessionLocal()
        try:
            # Find documents with missing files
            cutoff_date = datetime.now() - timedelta(days=days_old)
            old_documents = db.query(Document).filter(
                Document.uploaded_at < cutoff_date
            ).all()

            orphaned_count = 0
            for doc in old_documents:
                if not os.path.exists(doc.file_path):
                    # Mark as orphaned or delete
                    doc.processing_status = 'orphaned'
                    orphaned_count += 1

            db.commit()

        finally:
            db.close()

        processing_time = time.time() - start_time

        result = {
            'status': 'completed',
            'success': True,
            'deleted_files': deleted_count,
            'orphaned_records': orphaned_count,
            'days_old': days_old,
            'processing_time': processing_time,
            'message': f'Cleaned up {deleted_count} old files and {orphaned_count} orphaned records'
        }

        logger.info("File cleanup completed", result=result)
        return result

    except Exception as e:
        logger.error("File cleanup failed", error=str(e))
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'File cleanup error: {str(e)}'
        }


@celery_app.task(bind=True, name='app.workers.cleanup_worker.cleanup_old_logs')
def cleanup_old_logs(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up old processing logs
    """
    db = SessionLocal()

    try:
        logger.info(
            "Starting log cleanup task",
            days_old=days_old,
            task_id=self.request.id
        )

        start_time = time.time()

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Cleaning up processing logs', 'progress': 30}
        )

        # Delete old document processing logs
        cutoff_date = datetime.now() - timedelta(days=days_old)

        deleted_processing_logs = db.query(DocumentProcessingLog).filter(
            DocumentProcessingLog.created_at < cutoff_date
        ).delete()

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Cleaning up audit logs', 'progress': 70}
        )

        # Delete old audit logs (keep longer - 6 months)
        audit_cutoff_date = datetime.now() - timedelta(days=180)
        deleted_audit_logs = db.query(DecisionAuditLog).filter(
            DecisionAuditLog.created_at < audit_cutoff_date
        ).delete()

        db.commit()

        processing_time = time.time() - start_time

        result = {
            'status': 'completed',
            'success': True,
            'deleted_processing_logs': deleted_processing_logs,
            'deleted_audit_logs': deleted_audit_logs,
            'days_old': days_old,
            'processing_time': processing_time,
            'message': f'Cleaned up {deleted_processing_logs} processing logs and {deleted_audit_logs} audit logs'
        }

        logger.info("Log cleanup completed", result=result)
        return result

    except Exception as e:
        logger.error("Log cleanup failed", error=str(e))
        db.rollback()
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'Log cleanup error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.cleanup_worker.health_check')
def health_check(self) -> Dict[str, Any]:
    """
    Perform system health check
    """
    try:
        logger.info("Starting health check task", task_id=self.request.id)

        start_time = time.time()
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'metrics': {}
        }

        # Check database
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking database', 'progress': 20}
        )

        db_healthy = check_db_connection()
        health_data['services']['database'] = {
            'status': 'healthy' if db_healthy else 'unhealthy',
            'checked_at': datetime.utcnow().isoformat()
        }

        # Check file system
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking file system', 'progress': 40}
        )

        try:
            from app.config import settings
            upload_dir_size = FileManager.get_directory_size(settings.upload_dir)
            health_data['services']['file_system'] = {
                'status': 'healthy',
                'upload_directory_size': upload_dir_size,
                'checked_at': datetime.utcnow().isoformat()
            }
        except Exception as fs_error:
            health_data['services']['file_system'] = {
                'status': 'unhealthy',
                'error': str(fs_error),
                'checked_at': datetime.utcnow().isoformat()
            }

        # Check application metrics
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Gathering metrics', 'progress': 60}
        )

        if db_healthy:
            db = SessionLocal()
            try:
                # Count applications by status
                total_apps = db.query(Application).count()
                approved_apps = db.query(Application).filter(Application.status == 'approved').count()
                rejected_apps = db.query(Application).filter(Application.status == 'rejected').count()
                review_apps = db.query(Application).filter(Application.status == 'needs_review').count()

                # Count recent applications (last 24 hours)
                recent_cutoff = datetime.now() - timedelta(hours=24)
                recent_apps = db.query(Application).filter(Application.created_at >= recent_cutoff).count()

                health_data['metrics'] = {
                    'total_applications': total_apps,
                    'approved_applications': approved_apps,
                    'rejected_applications': rejected_apps,
                    'review_applications': review_apps,
                    'recent_applications_24h': recent_apps,
                    'approval_rate': (approved_apps / total_apps * 100) if total_apps > 0 else 0
                }

            finally:
                db.close()

        # Check worker queue status
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking worker queues', 'progress': 80}
        )

        try:
            # Basic queue inspection
            from celery import current_app
            inspect = current_app.control.inspect()

            # Get active tasks
            active_tasks = inspect.active()
            health_data['services']['celery'] = {
                'status': 'healthy' if active_tasks is not None else 'unhealthy',
                'active_tasks': len(active_tasks) if active_tasks else 0,
                'checked_at': datetime.utcnow().isoformat()
            }
        except Exception as celery_error:
            health_data['services']['celery'] = {
                'status': 'unhealthy',
                'error': str(celery_error),
                'checked_at': datetime.utcnow().isoformat()
            }

        processing_time = time.time() - start_time

        # Determine overall health
        service_statuses = [service['status'] for service in health_data['services'].values()]
        overall_healthy = all(status == 'healthy' for status in service_statuses)

        result = {
            'status': 'completed',
            'success': True,
            'overall_health': 'healthy' if overall_healthy else 'unhealthy',
            'processing_time': processing_time,
            'health_data': health_data,
            'message': f'Health check completed - System is {"healthy" if overall_healthy else "unhealthy"}'
        }

        logger.info("Health check completed", result=result)
        return result

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'Health check error: {str(e)}'
        }


@celery_app.task(bind=True, name='app.workers.cleanup_worker.optimize_database')
def optimize_database(self) -> Dict[str, Any]:
    """
    Optimize database performance
    """
    db = SessionLocal()

    try:
        logger.info("Starting database optimization task", task_id=self.request.id)

        start_time = time.time()

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Analyzing database statistics', 'progress': 20}
        )

        # Analyze table statistics (PostgreSQL specific)
        try:
            db.execute("ANALYZE")
            analyzed = True
        except Exception as analyze_error:
            logger.warning("Failed to analyze database", error=str(analyze_error))
            analyzed = False

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Vacuuming database', 'progress': 60}
        )

        # Vacuum database (PostgreSQL specific)
        try:
            # Note: Full VACUUM requires special permissions, so we do light maintenance
            db.execute("VACUUM (ANALYZE)")
            vacuumed = True
        except Exception as vacuum_error:
            logger.warning("Failed to vacuum database", error=str(vacuum_error))
            vacuumed = False

        db.commit()

        processing_time = time.time() - start_time

        result = {
            'status': 'completed',
            'success': True,
            'analyzed': analyzed,
            'vacuumed': vacuumed,
            'processing_time': processing_time,
            'message': f'Database optimization completed (analyzed: {analyzed}, vacuumed: {vacuumed})'
        }

        logger.info("Database optimization completed", result=result)
        return result

    except Exception as e:
        logger.error("Database optimization failed", error=str(e))
        db.rollback()
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'Database optimization error: {str(e)}'
        }
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.cleanup_worker.generate_daily_report')
def generate_daily_report(self, report_date: str = None) -> Dict[str, Any]:
    """
    Generate daily processing report
    """
    db = SessionLocal()

    try:
        logger.info("Starting daily report generation", report_date=report_date, task_id=self.request.id)

        # Parse report date
        if report_date:
            target_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            target_date = datetime.now().date()

        start_time = time.time()

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Gathering application statistics', 'progress': 30}
        )

        # Get applications for the day
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        applications = db.query(Application).filter(
            Application.created_at >= day_start,
            Application.created_at <= day_end
        ).all()

        # Calculate statistics
        total_applications = len(applications)
        approved = sum(1 for app in applications if app.status == 'approved')
        rejected = sum(1 for app in applications if app.status == 'rejected')
        review = sum(1 for app in applications if app.status == 'needs_review')
        processing = sum(1 for app in applications if app.status not in ['approved', 'rejected', 'needs_review'])

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Calculating processing times', 'progress': 60}
        )

        # Calculate processing times
        completed_apps = [app for app in applications if app.decision_at]
        if completed_apps:
            processing_times = []
            for app in completed_apps:
                if app.created_at and app.decision_at:
                    processing_time = (app.decision_at - app.created_at).total_seconds()
                    processing_times.append(processing_time)

            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            min_processing_time = min(processing_times) if processing_times else 0
            max_processing_time = max(processing_times) if processing_times else 0
        else:
            avg_processing_time = 0
            min_processing_time = 0
            max_processing_time = 0

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating report', 'progress': 90}
        )

        processing_time = time.time() - start_time

        report = {
            'report_date': target_date.isoformat(),
            'statistics': {
                'total_applications': total_applications,
                'approved_applications': approved,
                'rejected_applications': rejected,
                'review_applications': review,
                'processing_applications': processing,
                'approval_rate': (approved / total_applications * 100) if total_applications > 0 else 0,
                'completion_rate': ((approved + rejected) / total_applications * 100) if total_applications > 0 else 0
            },
            'processing_times': {
                'average_seconds': avg_processing_time,
                'minimum_seconds': min_processing_time,
                'maximum_seconds': max_processing_time,
                'average_minutes': avg_processing_time / 60 if avg_processing_time > 0 else 0
            },
            'generated_at': datetime.utcnow().isoformat(),
            'generation_time': processing_time
        }

        result = {
            'status': 'completed',
            'success': True,
            'report': report,
            'processing_time': processing_time,
            'message': f'Daily report generated for {target_date.isoformat()}'
        }

        logger.info("Daily report generation completed", result=result)
        return result

    except Exception as e:
        logger.error("Daily report generation failed", error=str(e))
        return {
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': f'Daily report generation error: {str(e)}'
        }
    finally:
        db.close()