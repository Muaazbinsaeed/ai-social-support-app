"""
Celery application configuration
"""

from celery import Celery
from app.config import settings
from app.shared.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "social_security_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        # 'app.workers.document_worker',
        # 'app.workers.decision_worker',
        # 'app.workers.cleanup_worker'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task routing
    task_routes={
        'app.workers.document_worker.*': {'queue': 'document_processing'},
        'app.workers.decision_worker.*': {'queue': 'decision_making'},
        'app.workers.cleanup_worker.*': {'queue': 'maintenance'},
    },

    # Task execution settings
    task_time_limit=settings.celery_task_time_limit,  # 10 minutes hard limit
    task_soft_time_limit=settings.celery_task_soft_time_limit,  # 5 minutes soft limit
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    worker_disable_rate_limits=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 minute delay
    task_max_retries=3,

    # Worker settings
    worker_concurrency=settings.celery_worker_concurrency,
    worker_prefetch_multiplier=1,  # Don't prefetch tasks

    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-old-files': {
            'task': 'app.workers.cleanup_worker.cleanup_old_files',
            'schedule': 3600.0,  # Run every hour
        },
        'health-check': {
            'task': 'app.workers.cleanup_worker.health_check',
            'schedule': 300.0,  # Run every 5 minutes
        },
    },
)

# Task failure handling
@celery_app.task(bind=True)
def handle_task_failure(self, task_id, error, traceback):
    """Handle task failures"""
    logger.error(
        "Task failed",
        task_id=task_id,
        error=str(error),
        traceback=traceback
    )

# Custom task base class
from celery import Task

class CallbackTask(Task):
    """Base task class with failure callback"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(
            "Task failed",
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            return_value=str(retval)[:100] if retval else None
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(
            "Task retrying",
            task_id=task_id,
            exception=str(exc),
            retry_count=self.request.retries
        )

# Set default task base class
celery_app.Task = CallbackTask

# Application startup
logger.info(
    "Celery application configured",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    concurrency=settings.celery_worker_concurrency
)