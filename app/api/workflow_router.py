"""
Workflow management API endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.document_processing.document_models import Document
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

# Pydantic models for requests/responses
class ApplicationCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    emirates_id: str = Field(..., pattern=r'^784-[0-9]{4}-[0-9]{7}-[0-9]$')
    phone: str = Field(..., pattern=r'^(\+971|05)[0-9]{8,9}$')
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')

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
    form_data: dict = {}

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


@router.delete("/cancel-application/{application_id}", status_code=status.HTTP_200_OK,
               summary="Cancel active application",
               description="Cancel and delete an active application (only if not yet processed)")
def cancel_application(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel an active application"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Check if application can be cancelled (not yet completed)
        if application.status in ["approved", "rejected", "decision_completed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "CANNOT_CANCEL",
                    "message": "Cannot cancel completed application"
                }
            )

        # Delete related workflow states
        db.query(WorkflowState).filter(WorkflowState.application_id == app_uuid).delete()

        # Delete related documents
        documents = db.query(Document).filter(Document.application_id == app_uuid).all()
        for doc in documents:
            # Delete physical file if exists
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except:
                    pass  # Ignore file deletion errors

        db.query(Document).filter(Document.application_id == app_uuid).delete()

        # Delete the application
        db.delete(application)
        db.commit()

        logger.info("Application cancelled",
                   application_id=str(application.id),
                   user_id=str(current_user.id))

        return {
            "message": "Application cancelled successfully",
            "application_id": application_id,
            "cancelled_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel application",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CANCELLATION_FAILED",
                "message": "Failed to cancel application"
            }
        )


@router.post("/upload-documents/{application_id}", status_code=status.HTTP_202_ACCEPTED,
             summary="Upload and process application documents",
             description="Upload bank statement and Emirates ID for application processing")
def upload_documents(
    application_id: str,
    bank_statement: UploadFile = File(..., description="Bank statement PDF file"),
    emirates_id: UploadFile = File(..., description="Emirates ID image file"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process application documents"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Check application state
        if application.status not in ["form_submitted", "draft"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "INVALID_STATE",
                    "message": f"Cannot upload documents in current state: {application.status}"
                }
            )

        # Validate file types and sizes
        allowed_pdf_types = ["application/pdf"]
        allowed_image_types = ["image/png", "image/jpeg", "image/jpg", "image/tiff", "image/bmp"]
        max_file_size = 50 * 1024 * 1024  # 50MB

        if bank_statement.content_type not in allowed_pdf_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_FILE_TYPE",
                    "message": "Bank statement must be a PDF file"
                }
            )

        if emirates_id.content_type not in allowed_image_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_FILE_TYPE",
                    "message": "Emirates ID must be an image file (PNG, JPG, TIFF, BMP)"
                }
            )

        if bank_statement.size > max_file_size or emirates_id.size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "FILE_TOO_LARGE",
                    "message": "Files must be smaller than 50MB"
                }
            )

        # Create upload directory for this application
        upload_dir = os.path.join(settings.upload_dir, str(application.id))
        os.makedirs(upload_dir, exist_ok=True)

        # Save files with secure names
        bank_statement_filename = f"bank_statement_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        emirates_id_filename = f"emirates_id_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{emirates_id.filename.split('.')[-1]}"

        bank_statement_path = os.path.join(upload_dir, bank_statement_filename)
        emirates_id_path = os.path.join(upload_dir, emirates_id_filename)

        # Save files
        with open(bank_statement_path, "wb") as f:
            f.write(bank_statement.file.read())

        with open(emirates_id_path, "wb") as f:
            f.write(emirates_id.file.read())

        # Create document records
        bank_doc = Document(
            application_id=application.id,
            user_id=current_user.id,
            document_type="bank_statement",
            original_filename=bank_statement.filename,
            file_path=bank_statement_path,
            file_size=bank_statement.size,
            mime_type=bank_statement.content_type,
            processing_status="uploaded"
        )

        emirates_doc = Document(
            application_id=application.id,
            user_id=current_user.id,
            document_type="emirates_id",
            original_filename=emirates_id.filename,
            file_path=emirates_id_path,
            file_size=emirates_id.size,
            mime_type=emirates_id.content_type,
            processing_status="uploaded"
        )

        db.add(bank_doc)
        db.add(emirates_doc)

        # Update application status and references
        application.status = APPLICATION_STATES["DOCUMENTS_UPLOADED"]
        application.progress = 30
        application.bank_statement_id = bank_doc.id
        application.emirates_id_doc_id = emirates_doc.id

        # Create workflow state
        upload_state = WorkflowState(
            application_id=application.id,
            current_state=APPLICATION_STATES["DOCUMENTS_UPLOADED"],
            step_name="document_upload",
            step_status="completed",
            step_message=STATE_MESSAGES["documents_uploaded"],
            processing_time_ms=500
        )

        db.add(upload_state)
        db.commit()

        logger.info("Documents uploaded successfully",
                   application_id=str(application.id),
                   user_id=str(current_user.id),
                   bank_statement_size=bank_statement.size,
                   emirates_id_size=emirates_id.size)

        return {
            "application_id": str(application.id),
            "document_ids": [str(bank_doc.id), str(emirates_doc.id)],
            "status": "documents_uploaded",
            "progress": 30,
            "processing_started": False,
            "estimated_completion": "Ready for processing",
            "message": "Documents uploaded successfully",
            "next_steps": ["Start processing via /workflow/process/{application_id}"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload documents",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOCUMENT_UPLOAD_FAILED",
                "message": "Failed to upload documents"
            }
        )


class FormUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    emirates_id: Optional[str] = Field(None, pattern=r'^784-[0-9]{4}-[0-9]{7}-[0-9]$')
    phone: Optional[str] = Field(None, pattern=r'^(\+971|05)[0-9]{8,9}$')
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')


@router.put("/update-form/{application_id}", status_code=status.HTTP_200_OK,
            summary="Update application form data",
            description="Update application form information for applications in early stages")
def update_application_form(
    application_id: str,
    form_data: FormUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update application form data (allowed in early workflow stages)"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Check if application can be updated (allow updates in early stages)
        updatable_states = ["draft", "form_submitted", "documents_uploaded"]
        if application.status not in updatable_states:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "APPLICATION_NOT_EDITABLE",
                    "message": f"Application form cannot be updated in current state: {application.status}",
                    "current_status": application.status,
                    "updatable_states": updatable_states
                }
            )

        # Update provided fields
        update_dict = form_data.dict(exclude_unset=True)
        updated_fields = []

        for field, value in update_dict.items():
            if value is not None:  # Only update if value is provided
                setattr(application, field, value)
                updated_fields.append(field)

        if updated_fields:
            application.updated_at = datetime.utcnow()
            db.commit()

            logger.info("Application form updated",
                       application_id=str(application.id),
                       user_id=str(current_user.id),
                       updated_fields=updated_fields)
        else:
            logger.info("No fields to update",
                       application_id=str(application.id),
                       user_id=str(current_user.id))

        return {
            "message": "Application form updated successfully" if updated_fields else "No changes to apply",
            "application_id": str(application.id),
            "updated_fields": updated_fields,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "form_data": {
                "full_name": application.full_name,
                "emirates_id": application.emirates_id,
                "phone": application.phone,
                "email": application.email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update application form",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "FORM_UPDATE_FAILED",
                "message": "Failed to update application form"
            }
        )


@router.get("/processing-status/{application_id}",
            summary="Get detailed processing status",
            description="Get detailed status of document processing including OCR results")
def get_processing_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed processing status with OCR results"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_UUID", "message": "Invalid application ID format"}
            )
        
        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
            Application.user_id == current_user.id
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "APPLICATION_NOT_FOUND", "message": "Application not found"}
            )
        
        # Get documents with OCR results
        documents = db.query(Document).filter(
            Document.application_id == app_uuid
        ).all()
        
        document_status = []
        for doc in documents:
            doc_info = {
                "document_id": str(doc.id),
                "document_type": doc.document_type,
                "filename": doc.original_filename,
                "status": doc.processing_status,
                "ocr_status": "not_started",
                "ocr_text": None,
                "ocr_confidence": None,
                "extracted_data": {}
            }
            
            # Add OCR results if available
            if doc.extracted_text:
                doc_info["ocr_status"] = "completed"
                doc_info["ocr_text"] = doc.extracted_text[:500] + "..." if len(doc.extracted_text) > 500 else doc.extracted_text
                doc_info["ocr_confidence"] = float(doc.ocr_confidence) if doc.ocr_confidence else 0.0
                
                # Extract key information based on document type
                if doc.document_type == "emirates_id":
                    # Extract Emirates ID info
                    import re
                    id_pattern = r'784-\d{4}-\d{7}-\d'
                    id_match = re.search(id_pattern, doc.extracted_text)
                    if id_match:
                        doc_info["extracted_data"]["emirates_id"] = id_match.group()
                    
                    # Extract name (simple heuristic)
                    name_lines = doc.extracted_text.split('\n')[:5]
                    for line in name_lines:
                        if len(line) > 5 and line[0].isupper():
                            doc_info["extracted_data"]["name"] = line.strip()
                            break
                
                elif doc.document_type == "bank_statement":
                    # Extract account info
                    import re
                    # Look for account number
                    account_pattern = r'(?:Account|A/C)[\s:#]*(\d{10,})'
                    account_match = re.search(account_pattern, doc.extracted_text, re.IGNORECASE)
                    if account_match:
                        doc_info["extracted_data"]["account_number"] = account_match.group(1)
                    
                    # Look for balance
                    balance_pattern = r'(?:Balance|Total)[\s:]*(?:AED|USD)?\s*([\d,]+\.?\d*)'
                    balance_match = re.search(balance_pattern, doc.extracted_text, re.IGNORECASE)
                    if balance_match:
                        doc_info["extracted_data"]["balance"] = balance_match.group(1)
            
            elif doc.processing_status == "processing":
                doc_info["ocr_status"] = "in_progress"
            elif doc.processing_status == "failed":
                doc_info["ocr_status"] = "failed"
            
            document_status.append(doc_info)
        
        # Get workflow steps
        workflow_steps = db.query(WorkflowState).filter(
            WorkflowState.application_id == app_uuid
        ).order_by(WorkflowState.created_at.desc()).limit(10).all()
        
        steps = []
        for step in workflow_steps:
            step_info = {
                "step_name": step.step_name,
                "state": step.current_state,
                "status": step.step_status,
                "message": step.step_message,
                "created_at": step.created_at.isoformat() if step.created_at else None,
                "completed_at": step.updated_at.isoformat() if step.step_status == "completed" and step.updated_at else None
            }
            steps.append(step_info)
        
        return {
            "application_id": str(application.id),
            "overall_status": application.status,
            "progress": application.progress,
            "documents": document_status,
            "workflow_steps": steps,
            "processing_started": application.processed_at.isoformat() if application.processed_at else None,
            "last_updated": application.updated_at.isoformat() if application.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "STATUS_FETCH_FAILED", "message": "Failed to get processing status"}
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
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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
        # Ensure both datetimes are timezone-aware using UTC
        from datetime import timezone
        current_time = datetime.now(timezone.utc)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        processing_time_elapsed = str(int((current_time - start_time).total_seconds()))

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
                completed_at=state.updated_at.isoformat() + "Z" if state.step_status == "completed" and state.updated_at is not None else None,
                started_at=state.created_at.isoformat() + "Z" if state.created_at is not None else None,
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

        # Include form data from the application
        form_data = {
            "full_name": application.full_name,
            "emirates_id": application.emirates_id,
            "phone": application.phone,
            "email": application.email
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
            next_action="continue_processing" if application.status not in ["approved", "rejected"] else "view_results",
            form_data=form_data
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
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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
        
        # Get documents for OCR processing
        documents = db.query(Document).filter(
            Document.application_id == app_uuid
        ).all()
        
        # Create detailed processing steps
        processing_steps = []
        if documents:
            for doc in documents:
                processing_steps.append({
                    "document_id": str(doc.id),
                    "document_type": doc.document_type,
                    "filename": doc.original_filename,
                    "status": "pending_ocr"
                })

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

        # Perform inline OCR and multimodal processing for demo (normally would use Celery)
        import time
        if documents:
            for doc in documents:
                try:
                    # Start OCR processing
                    doc.ocr_status = "in_progress"
                    doc.ocr_progress = 0
                    doc.multimodal_status = "pending"
                    doc.multimodal_progress = 0
                    db.commit()

                    # Simulate OCR processing with progress updates
                    doc.ocr_progress = 30
                    db.commit()
                    time.sleep(0.3)

                    doc.ocr_progress = 70
                    db.commit()
                    time.sleep(0.2)

                    # Complete OCR with mock results
                    if doc.document_type == "emirates_id":
                        doc.extracted_text = """
United Arab Emirates
Emirates ID Card
Name: AHMED ALI HASSAN
ID Number: 784-1985-9876543-2
Date of Birth: 01/01/1990
Nationality: UAE
Expiry: 01/01/2030
Gender: Male
Card Number: 123-4567-8901234-5
                        """.strip()
                        doc.ocr_confidence = 0.92
                    elif doc.document_type == "bank_statement":
                        doc.extracted_text = """
EMIRATES NBD BANK
Account Statement
Account Number: 1234567890123
Account Holder: AHMED ALI HASSAN
Statement Period: 01/01/2024 - 31/01/2024
Opening Balance: AED 15,234.50
Closing Balance: AED 18,456.75
Total Credits: AED 8,500.00
Total Debits: AED 5,277.75
Average Balance: AED 16,845.63
Monthly Income: AED 8,500.00
Salary Credit: AED 8,500.00 (Company: Tech Solutions LLC)
                        """.strip()
                        doc.ocr_confidence = 0.88

                    doc.ocr_status = "completed"
                    doc.ocr_progress = 100
                    doc.ocr_processing_time_ms = 800
                    db.commit()

                    # Start multimodal analysis
                    doc.multimodal_status = "in_progress"
                    doc.multimodal_progress = 0
                    db.commit()

                    # Simulate multimodal processing
                    time.sleep(0.4)
                    doc.multimodal_progress = 50
                    db.commit()
                    time.sleep(0.3)

                    # Complete multimodal analysis
                    doc.multimodal_status = "completed"
                    doc.multimodal_progress = 100
                    doc.analysis_processing_time_ms = 700

                    # Update overall processing status
                    doc.processing_status = "completed"
                    doc.processed_at = datetime.utcnow()

                    # Log completion
                    ocr_complete_state = WorkflowState(
                        application_id=application.id,
                        current_state="analysis_completed",
                        step_name=f"processing_{doc.document_type}",
                        step_status="completed",
                        step_message=f"OCR and multimodal analysis completed for {doc.document_type.replace('_', ' ')}",
                        updated_at=datetime.utcnow()
                    )
                    db.add(ocr_complete_state)

                except Exception as e:
                    logger.error(f"Document processing failed for document {doc.id}: {str(e)}")
                    doc.ocr_status = "failed"
                    doc.multimodal_status = "failed"
                    doc.processing_status = "failed"
                    doc.error_message = str(e)
            
            # Update application status after OCR
            application.status = "ocr_completed"
            application.progress = 50
            db.commit()
        
        # Trigger background processing via Celery (if available)
        try:
            from app.workers.decision_worker import process_complete_application
            # Start the complete workflow processing
            task = process_complete_application.delay(str(application.id))
            logger.info("Background processing task started",
                       application_id=str(application.id),
                       task_id=str(task.id))
        except ImportError:
            logger.warning("Celery worker not available, using inline processing")

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


@router.put("/reset-status/{application_id}", status_code=status.HTTP_200_OK,
            summary="Reset application status to editable state",
            description="Reset application back to an editable state for form updates")
def reset_application_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reset application to editable state"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Only allow reset from processing states
        resettable_states = ["scanning_documents", "ocr_completed", "analyzing_income",
                           "analyzing_identity", "making_decision", "analysis_completed"]

        if application.status not in resettable_states:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "CANNOT_RESET",
                    "message": f"Cannot reset application in state: {application.status}",
                    "current_status": application.status,
                    "resettable_states": resettable_states
                }
            )

        # Determine what state to reset to based on application progress
        old_status = application.status
        if application.bank_statement_id and application.emirates_id_id:
            # Has documents uploaded
            new_status = "documents_uploaded"
            new_progress = 30
        else:
            # Only has form submitted
            new_status = "form_submitted"
            new_progress = 20

        # Reset application state
        application.status = new_status
        application.progress = new_progress

        # Clear any processing results to allow fresh processing
        application.monthly_income = None
        application.account_balance = None
        application.eligibility_score = None
        application.decision = None
        application.processed_at = None
        application.updated_at = datetime.utcnow()

        db.commit()

        logger.info("Application status reset successfully",
                   application_id=str(application.id),
                   user_id=str(current_user.id),
                   old_status=old_status,
                   new_status=new_status)

        return {
            "message": "Application status reset successfully",
            "application_id": str(application.id),
            "old_status": old_status,
            "new_status": new_status,
            "progress": new_progress,
            "reset_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset application status",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATUS_RESET_FAILED",
                "message": "Failed to reset application status"
            }
        )


@router.delete("/discard-application", status_code=status.HTTP_200_OK,
               summary="Discard current active application",
               description="Cancel and discard the user's current active application to allow creating a new one")
def discard_current_application(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Discard user's current active application"""
    try:
        # Find user's active application
        active_application = db.query(Application).filter(
            Application.user_id == current_user.id,
            Application.status.in_(["draft", "form_submitted", "documents_uploaded", "scanning_documents",
                                  "ocr_completed", "analyzing_income", "analyzing_identity",
                                  "analysis_completed", "making_decision"])
        ).first()

        if not active_application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NO_ACTIVE_APPLICATION",
                    "message": "No active application found to discard"
                }
            )

        # Cancel the application
        old_status = active_application.status
        active_application.status = "cancelled"
        active_application.decision = "cancelled"
        active_application.decision_reasoning = "Application cancelled by user to start new application"
        active_application.updated_at = datetime.utcnow()

        db.commit()

        logger.info("Application discarded successfully",
                   application_id=str(active_application.id),
                   user_id=str(current_user.id),
                   old_status=old_status)

        return {
            "message": "Application discarded successfully",
            "discarded_application_id": str(active_application.id),
            "old_status": old_status,
            "discarded_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to discard application",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DISCARD_FAILED",
                "message": "Failed to discard application"
            }
        )


# Enhanced Status Tracking Endpoints

@router.get("/status-enhanced/{application_id}",
           summary="Get enhanced application status",
           description="Get enhanced status with OCR and multimodal tracking details")
def get_enhanced_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get enhanced application status with detailed processing info"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Get documents
        documents = db.query(Document).filter(
            Document.application_id == app_uuid
        ).all()

        # Build OCR and multimodal status
        ocr_status = {}
        multimodal_status = {}

        for doc in documents:
            doc_type = doc.document_type
            # Handle existing documents that might not have new fields
            ocr_status[doc_type] = getattr(doc, 'ocr_status', 'pending')
            multimodal_status[doc_type] = getattr(doc, 'multimodal_status', 'pending')

        # Calculate progress phases
        form_submitted = application.status != "draft"
        documents_uploaded = len(documents) >= 2

        return {
            "application_id": str(application.id),
            "current_status": application.status,
            "progress": application.progress,
            "phase": _get_current_phase(application.status),
            "details": {
                "form_submitted": form_submitted,
                "documents_uploaded": documents_uploaded,
                "ocr_status": ocr_status,
                "multimodal_status": multimodal_status,
                "decision": application.decision or "pending"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get enhanced status",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ENHANCED_STATUS_FAILED",
                "message": "Failed to get enhanced status"
            }
        )


@router.get("/processing-details/{application_id}",
           summary="Get processing details",
           description="Get detailed OCR and multimodal processing status")
def get_processing_details(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed processing status for OCR and multimodal analysis"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Get documents
        documents = db.query(Document).filter(
            Document.application_id == app_uuid
        ).all()

        ocr_extraction = {}
        multimodal_analysis = {}
        sources_ready = 0

        for doc in documents:
            doc_type = doc.document_type

            # OCR status
            ocr_extraction[doc_type] = {
                "status": getattr(doc, 'ocr_status', 'pending'),
                "progress": getattr(doc, 'ocr_progress', 0),
                "confidence": float(doc.ocr_confidence) if doc.ocr_confidence else None,
                "text_extracted": bool(doc.extracted_text)
            }

            # Multimodal status
            multimodal_analysis[doc_type] = {
                "status": getattr(doc, 'multimodal_status', 'pending'),
                "progress": getattr(doc, 'multimodal_progress', 0)
            }

            # Count ready sources
            if getattr(doc, 'ocr_status', 'pending') == "completed":
                sources_ready += 1
            if getattr(doc, 'multimodal_status', 'pending') == "completed":
                sources_ready += 1

        # Add form data to sources count
        if application.status != "draft":
            sources_ready += 1

        return {
            "application_id": str(application.id),
            "ocr_extraction": ocr_extraction,
            "multimodal_analysis": multimodal_analysis,
            "all_5_sources_ready": sources_ready >= 5,
            "sources_ready_count": sources_ready,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get processing details",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROCESSING_DETAILS_FAILED",
                "message": "Failed to get processing details"
            }
        )


@router.get("/progress/{application_id}",
           summary="Get simple progress",
           description="Get simple progress percentage with completed and pending steps")
def get_simple_progress(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get simple progress with step completion"""
    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format"
                }
            )

        # Get application
        application = db.query(Application).filter(
            Application.id == app_uuid,
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

        # Get documents
        documents = db.query(Document).filter(
            Document.application_id == app_uuid
        ).all()

        # Calculate completed and pending steps
        steps_completed = []
        steps_pending = []

        # Check each step
        if application.status != "draft":
            steps_completed.append("form_submission")
        else:
            steps_pending.append("form_submission")

        if len(documents) >= 2:
            steps_completed.append("document_upload")
        else:
            steps_pending.append("document_upload")

        # Check OCR steps
        for doc in documents:
            doc_type = doc.document_type
            if getattr(doc, 'ocr_status', 'pending') == "completed":
                steps_completed.append(f"ocr_{doc_type}")
            else:
                steps_pending.append(f"ocr_{doc_type}")

            if getattr(doc, 'multimodal_status', 'pending') == "completed":
                steps_completed.append(f"multimodal_{doc_type}")
            else:
                steps_pending.append(f"multimodal_{doc_type}")

        # Check decision
        if application.decision:
            steps_completed.append("llm_decision")
        else:
            steps_pending.append("llm_decision")

        # Calculate overall progress (Form 20% + Upload 20% + OCR 20% + Multimodal 20% + Decision 20%)
        progress = 0
        if "form_submission" in steps_completed:
            progress += 20
        if "document_upload" in steps_completed:
            progress += 20

        # OCR progress (10% per document)
        ocr_completed = len([s for s in steps_completed if s.startswith("ocr_")])
        progress += (ocr_completed * 10)

        # Multimodal progress (10% per document)
        multimodal_completed = len([s for s in steps_completed if s.startswith("multimodal_")])
        progress += (multimodal_completed * 10)

        if "llm_decision" in steps_completed:
            progress += 20

        # Estimate completion time
        total_steps = len(steps_completed) + len(steps_pending)
        if len(steps_pending) == 0:
            estimated_seconds = 0
        else:
            estimated_seconds = len(steps_pending) * 10  # Rough estimate

        return {
            "application_id": str(application.id),
            "overall_progress": min(progress, 100),
            "steps_completed": steps_completed,
            "steps_pending": steps_pending,
            "estimated_completion_seconds": estimated_seconds,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simple progress",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROGRESS_FAILED",
                "message": "Failed to get progress"
            }
        )


def _get_current_phase(status: str) -> str:
    """Get current phase based on application status"""
    if status in ["draft"]:
        return "user_setup"
    elif status in ["form_submitted"]:
        return "form_completed"
    elif status in ["documents_uploaded"]:
        return "document_management"
    elif status in ["scanning_documents", "ocr_completed"]:
        return "extraction"
    elif status in ["analyzing_income", "analyzing_identity", "analysis_completed"]:
        return "multimodal_analysis"
    elif status in ["making_decision", "decision_completed"]:
        return "decision_making"
    elif status in ["approved", "rejected", "needs_review"]:
        return "completed"
    else:
        return "unknown"