"""
Workflow management API endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

# Pydantic models for requests/responses
class ApplicationCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    emirates_id: str = Field(..., regex=r'^784-[0-9]{4}-[0-9]{7}-[0-9]$')
    phone: str = Field(..., regex=r'^(\+971|05)[0-9]{8,9}$')
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')

class ApplicationResponse(BaseModel):
    application_id: str
    status: str
    progress: int
    message: str
    next_steps: List[str]
    expires_at: str

class WorkflowStep(BaseModel):
    name: str
    status: str
    message: str
    completed_at: Optional[str] = None
    started_at: Optional[str] = None
    duration: Optional[str] = None
    progress: Optional[int] = None

class WorkflowStatusResponse(BaseModel):
    application_id: str
    current_state: str
    progress: int
    processing_time_elapsed: str
    estimated_completion: str
    steps: List[WorkflowStep]
    partial_results: dict = {}
    errors: List[str] = []
    can_retry: bool = False
    next_action: str

class ProcessRequest(BaseModel):
    force_retry: bool = False
    retry_failed_steps: bool = False

# Application States
APPLICATION_STATES = {
    "DRAFT": "draft",
    "FORM_SUBMITTED": "form_submitted",
    "DOCUMENTS_UPLOADED": "documents_uploaded",
    "SCANNING_DOCUMENTS": "scanning_documents",
    "OCR_COMPLETED": "ocr_completed",
    "ANALYZING_INCOME": "analyzing_income",
    "ANALYZING_IDENTITY": "analyzing_identity",
    "ANALYSIS_COMPLETED": "analysis_completed",
    "MAKING_DECISION": "making_decision",
    "DECISION_COMPLETED": "decision_completed",
    "APPROVED": "approved",
    "REJECTED": "rejected",
    "NEEDS_REVIEW": "needs_review",
    "PARTIAL_SUCCESS": "partial_success",
    "MANUAL_REVIEW_REQUIRED": "manual_review_required"
}

STATE_MESSAGES = {
    "form_submitted": "📤 Application form received and validated",
    "documents_uploaded": "📄 Documents uploaded successfully",
    "scanning_documents": "🔍 Scanning documents for text extraction",
    "ocr_completed": "✅ Text extraction completed",
    "analyzing_income": "💰 Analyzing bank statement for income verification",
    "analyzing_identity": "🆔 Verifying Emirates ID details",
    "analysis_completed": "📊 Document analysis completed",
    "making_decision": "⚖️ Evaluating eligibility criteria",
    "decision_completed": "✅ Decision process completed",
    "approved": "🎉 APPROVED: Eligible for social security benefits",
    "rejected": "❌ REJECTED: Does not meet eligibility criteria",
    "needs_review": "👀 Manual review required - partial data processed"
}


@router.post("/start-application", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED,
             summary="Initialize new application workflow",
             description="Create a new social security application and start the workflow process")
def start_application(
    application_data: ApplicationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Initialize new application workflow"""
    try:
        # Check if user already has an active application
        existing_application = db.query(Application).filter(
            Application.user_id == current_user.id,
            Application.status.in_(["draft", "form_submitted", "documents_uploaded", "scanning_documents",
                                  "ocr_completed", "analyzing_income", "analyzing_identity",
                                  "analysis_completed", "making_decision"])
        ).first()

        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "APPLICATION_EXISTS",
                    "message": "Active application already exists for this user",
                    "existing_application_id": str(existing_application.id)
                }
            )

        # Create new application
        new_application = Application(
            user_id=current_user.id,
            full_name=application_data.full_name,
            emirates_id=application_data.emirates_id,
            phone=application_data.phone,
            email=application_data.email,
            status=APPLICATION_STATES["FORM_SUBMITTED"],
            progress=20,
            submitted_at=datetime.utcnow()
        )

        db.add(new_application)
        db.flush()  # Get the ID without committing

        # Create initial workflow state
        initial_state = WorkflowState(
            application_id=new_application.id,
            current_state=APPLICATION_STATES["FORM_SUBMITTED"],
            step_name="form_submission",
            step_status="completed",
            step_message=STATE_MESSAGES["form_submitted"],
            processing_time_ms=100
        )

        db.add(initial_state)
        db.commit()

        # Log successful creation
        logger.info("Application workflow started",
                   application_id=str(new_application.id),
                   user_id=str(current_user.id))

        return ApplicationResponse(
            application_id=str(new_application.id),
            status=APPLICATION_STATES["FORM_SUBMITTED"],
            progress=20,
            message="Application created successfully",
            next_steps=["Upload required documents"],
            expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start application workflow",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "WORKFLOW_START_FAILED",
                "message": "Failed to initialize application workflow"
            }
        )


@router.get("/status/{application_id}", response_model=WorkflowStatusResponse,
            summary="Get detailed processing status",
            description="Retrieve comprehensive workflow status with step-by-step progress")
def get_workflow_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed processing status and progress"""
    try:
        # Get application
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

        # Get workflow states
        workflow_states = db.query(WorkflowState).filter(
            WorkflowState.application_id == application.id
        ).order_by(WorkflowState.created_at).all()

        # Calculate processing time
        start_time = application.submitted_at or application.created_at
        processing_time_elapsed = str(int((datetime.utcnow() - start_time).total_seconds()))

        # Estimate completion time based on current progress
        if application.progress >= 90:
            estimated_completion = "< 30 seconds"
        elif application.progress >= 70:
            estimated_completion = "45-90 seconds"
        else:
            estimated_completion = "2-5 minutes"

        # Build steps from workflow states
        steps = []
        for state in workflow_states:
            step = WorkflowStep(
                name=state.current_state,
                status=state.step_status or "completed",
                message=state.step_message or STATE_MESSAGES.get(state.current_state, "Processing..."),
                completed_at=state.updated_at.isoformat() + "Z" if state.step_status == "completed" else None,
                started_at=state.created_at.isoformat() + "Z",
                duration=f"{state.processing_time_ms or 0}ms"
            )
            steps.append(step)

        # Add pending steps if not completed
        if application.status not in ["approved", "rejected", "needs_review"]:
            pending_states = ["analyzing_income", "analyzing_identity", "making_decision"]
            current_found = False
            for state_name in pending_states:
                if application.status == state_name:
                    current_found = True
                    steps.append(WorkflowStep(
                        name=state_name,
                        status="in_progress",
                        message=STATE_MESSAGES.get(state_name, "Processing..."),
                        started_at=datetime.utcnow().isoformat() + "Z",
                        progress=60
                    ))
                elif not current_found:
                    continue
                else:
                    steps.append(WorkflowStep(
                        name=state_name,
                        status="pending",
                        message=f"⏳ Waiting to {state_name.replace('_', ' ')}"
                    ))

        # Build partial results
        partial_results = {}
        if application.monthly_income:
            partial_results["documents_processed"] = 1
            partial_results["bank_statement"] = {
                "monthly_income": float(application.monthly_income),
                "account_balance": float(application.account_balance) if application.account_balance else None,
                "confidence": float(application.eligibility_score) if application.eligibility_score else 0.95,
                "processing_time": "25 seconds"
            }

        return WorkflowStatusResponse(
            application_id=str(application.id),
            current_state=application.status,
            progress=application.progress,
            processing_time_elapsed=f"{processing_time_elapsed} seconds",
            estimated_completion=estimated_completion,
            steps=steps,
            partial_results=partial_results,
            errors=[],
            can_retry=application.status in ["needs_review", "partial_success"],
            next_action="continue_processing" if application.status not in ["approved", "rejected"] else "view_results"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get workflow status",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATUS_FETCH_FAILED",
                "message": "Failed to retrieve workflow status"
            }
        )


@router.post("/process/{application_id}", status_code=status.HTTP_202_ACCEPTED,
             summary="Start or retry application processing",
             description="Initiate or retry the application processing workflow")
def process_application(
    application_id: str,
    process_request: ProcessRequest = ProcessRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start or retry application processing workflow"""
    try:
        # Get application
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

        # Check if application is in valid state for processing
        valid_states = ["form_submitted", "documents_uploaded", "needs_review", "partial_success"]
        if application.status not in valid_states and not process_request.force_retry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_STATE",
                    "message": "Application not ready for processing",
                    "current_state": application.status,
                    "required_state": "documents_uploaded"
                }
            )

        # Check if already processing
        if application.status in ["scanning_documents", "analyzing_income", "analyzing_identity", "making_decision"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "ALREADY_PROCESSING",
                    "message": "Application is already being processed",
                    "current_status": application.status
                }
            )

        # Update application status to start processing
        if application.status == "documents_uploaded":
            new_status = "scanning_documents"
        elif application.status in ["needs_review", "partial_success"]:
            new_status = "analyzing_income"  # Resume from analysis
        else:
            new_status = "scanning_documents"

        application.status = new_status
        application.progress = 40
        application.processed_at = datetime.utcnow()

        # Create workflow state for processing start
        processing_state = WorkflowState(
            application_id=application.id,
            current_state=new_status,
            step_name="processing_start",
            step_status="in_progress",
            step_message=STATE_MESSAGES.get(new_status, "Processing started"),
            retry_count=1 if process_request.force_retry else 0
        )

        db.add(processing_state)
        db.commit()

        # TODO: Here you would trigger background processing via Celery
        # For now, we'll just return success response

        logger.info("Application processing started",
                   application_id=str(application.id),
                   user_id=str(current_user.id),
                   force_retry=process_request.force_retry)

        return {
            "application_id": str(application.id),
            "status": "processing_started",
            "message": "Processing workflow initiated",
            "estimated_completion": "90 seconds",
            "processing_job_id": str(processing_state.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start processing workflow",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROCESSING_START_FAILED",
                "message": "Failed to start processing workflow"
            }
        )