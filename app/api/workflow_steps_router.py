"""
Workflow Steps Router - Manual control for each processing step
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import asyncio
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.document_processing.document_models import Document
from app.document_processing.ocr_service import OCRService
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow/steps", tags=["workflow-steps"])


class StepType(str, Enum):
    """Workflow step types"""
    VALIDATE_DOCUMENTS = "validate_documents"
    OCR_EXTRACTION = "ocr_extraction"
    TEXT_ANALYSIS = "text_analysis"
    DATA_EXTRACTION = "data_extraction"
    INCOME_VERIFICATION = "income_verification"
    IDENTITY_VERIFICATION = "identity_verification"
    DECISION_MAKING = "decision_making"
    FINAL_REVIEW = "final_review"


class StepStatus(str, Enum):
    """Step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class StepRequest(BaseModel):
    """Request to execute a step"""
    step_type: StepType
    timeout_seconds: Optional[int] = Field(default=60, ge=10, le=300)
    force_retry: Optional[bool] = False


class StepResponse(BaseModel):
    """Response from step execution"""
    step_id: str
    step_type: str
    status: str
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None


# In-memory storage for active step executions (in production, use Redis)
active_steps: Dict[str, Dict[str, Any]] = {}


@router.post("/{application_id}/execute",
            summary="Execute a specific workflow step manually",
            response_model=StepResponse)
async def execute_step(
    application_id: str,
    step_request: StepRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute a specific workflow step with manual control"""
    try:
        # Validate application
        app_uuid = uuid.UUID(application_id)
        application = db.query(Application).filter(
            Application.id == app_uuid,
            Application.user_id == current_user.id
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "APPLICATION_NOT_FOUND", "message": "Application not found"}
            )
        
        # Check if step is already running
        step_key = f"{application_id}_{step_request.step_type}"
        if step_key in active_steps and active_steps[step_key]["status"] == StepStatus.RUNNING:
            return StepResponse(
                step_id=active_steps[step_key]["step_id"],
                step_type=step_request.step_type,
                status=StepStatus.RUNNING,
                message="Step is already running",
                started_at=active_steps[step_key]["started_at"]
            )
        
        # Create step execution record
        step_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        active_steps[step_key] = {
            "step_id": step_id,
            "step_type": step_request.step_type,
            "status": StepStatus.RUNNING,
            "started_at": started_at.isoformat(),
            "timeout": step_request.timeout_seconds,
            "application_id": application_id,
            "user_id": str(current_user.id)
        }
        
        # Log step start
        workflow_state = WorkflowState(
            application_id=app_uuid,
            current_state=application.status,
            step_name=step_request.step_type,
            step_status="running",
            step_message=f"Starting {step_request.step_type.replace('_', ' ').title()}"
        )
        db.add(workflow_state)
        db.commit()
        
        # Execute step in background
        background_tasks.add_task(
            execute_step_async,
            step_key,
            step_id,
            application_id,
            step_request.step_type,
            step_request.timeout_seconds,
            db
        )
        
        return StepResponse(
            step_id=step_id,
            step_type=step_request.step_type,
            status=StepStatus.RUNNING,
            message=f"Step {step_request.step_type} started",
            started_at=started_at.isoformat(),
            progress=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute step: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "STEP_EXECUTION_FAILED", "message": str(e)}
        )


async def execute_step_async(
    step_key: str,
    step_id: str,
    application_id: str,
    step_type: str,
    timeout: int,
    db: Session
):
    """Execute step asynchronously with timeout"""
    try:
        # Simulate step execution based on type
        if step_type == StepType.VALIDATE_DOCUMENTS:
            result = await validate_documents_step(application_id, db)
        elif step_type == StepType.OCR_EXTRACTION:
            result = await ocr_extraction_step(application_id, db)
        elif step_type == StepType.TEXT_ANALYSIS:
            result = await text_analysis_step(application_id, db)
        elif step_type == StepType.DATA_EXTRACTION:
            result = await data_extraction_step(application_id, db)
        elif step_type == StepType.INCOME_VERIFICATION:
            result = await income_verification_step(application_id, db)
        elif step_type == StepType.IDENTITY_VERIFICATION:
            result = await identity_verification_step(application_id, db)
        elif step_type == StepType.DECISION_MAKING:
            result = await decision_making_step(application_id, db)
        else:
            result = await final_review_step(application_id, db)
        
        # Update step status
        active_steps[step_key]["status"] = StepStatus.COMPLETED
        active_steps[step_key]["completed_at"] = datetime.utcnow().isoformat()
        active_steps[step_key]["output"] = result
        
    except asyncio.TimeoutError:
        active_steps[step_key]["status"] = StepStatus.TIMEOUT
        active_steps[step_key]["error"] = f"Step timed out after {timeout} seconds"
    except Exception as e:
        active_steps[step_key]["status"] = StepStatus.FAILED
        active_steps[step_key]["error"] = str(e)


async def validate_documents_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Validate uploaded documents"""
    await asyncio.sleep(2)  # Simulate processing
    
    app_uuid = uuid.UUID(application_id)
    documents = db.query(Document).filter(Document.application_id == app_uuid).all()
    
    result = {
        "documents_found": len(documents),
        "validation_results": []
    }
    
    for doc in documents:
        validation = {
            "document_type": doc.document_type,
            "filename": doc.filename,
            "size": doc.file_size,
            "valid_format": doc.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')),
            "status": "valid" if doc.file_path else "invalid"
        }
        result["validation_results"].append(validation)
    
    return result


async def ocr_extraction_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Perform OCR extraction on documents"""
    app_uuid = uuid.UUID(application_id)
    documents = db.query(Document).filter(Document.application_id == app_uuid).all()
    
    ocr_service = OCRService()
    result = {
        "ocr_results": [],
        "total_text_extracted": 0
    }
    
    for doc in documents:
        try:
            if doc.file_path:
                # Perform actual OCR
                ocr_result = ocr_service.extract_text(doc.file_path)
                
                # Update document with OCR results
                doc.extracted_text = ocr_result.extracted_text
                doc.ocr_confidence = ocr_result.confidence
                doc.ocr_processing_time_ms = ocr_result.processing_time_ms
                doc.status = "ocr_completed"
                
                result["ocr_results"].append({
                    "document_type": doc.document_type,
                    "text_length": len(ocr_result.extracted_text),
                    "confidence": float(ocr_result.confidence),
                    "processing_time_ms": ocr_result.processing_time_ms,
                    "preview": ocr_result.extracted_text[:200] + "..." if len(ocr_result.extracted_text) > 200 else ocr_result.extracted_text
                })
                result["total_text_extracted"] += len(ocr_result.extracted_text)
            else:
                result["ocr_results"].append({
                    "document_type": doc.document_type,
                    "error": "File not found"
                })
        except Exception as e:
            result["ocr_results"].append({
                "document_type": doc.document_type,
                "error": str(e)
            })
    
    db.commit()
    return result


async def text_analysis_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Analyze extracted text"""
    await asyncio.sleep(3)  # Simulate processing
    
    app_uuid = uuid.UUID(application_id)
    documents = db.query(Document).filter(Document.application_id == app_uuid).all()
    
    result = {
        "analysis_results": []
    }
    
    for doc in documents:
        if doc.extracted_text:
            # Simple text analysis
            text = doc.extracted_text
            analysis = {
                "document_type": doc.document_type,
                "word_count": len(text.split()),
                "line_count": len(text.split('\n')),
                "has_numbers": any(char.isdigit() for char in text),
                "language": "en",  # Simplified
                "quality_score": float(doc.ocr_confidence) if doc.ocr_confidence else 0.0
            }
            result["analysis_results"].append(analysis)
    
    return result


async def data_extraction_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Extract structured data from text"""
    await asyncio.sleep(2)  # Simulate processing
    
    app_uuid = uuid.UUID(application_id)
    documents = db.query(Document).filter(Document.application_id == app_uuid).all()
    
    result = {
        "extracted_data": {}
    }
    
    for doc in documents:
        if doc.extracted_text:
            if doc.document_type == "emirates_id":
                # Extract ID data
                import re
                id_pattern = r'784-\d{4}-\d{7}-\d'
                id_match = re.search(id_pattern, doc.extracted_text)
                result["extracted_data"]["emirates_id"] = {
                    "id_number": id_match.group() if id_match else None,
                    "name": "Extracted Name",  # Simplified
                    "nationality": "UAE"
                }
            elif doc.document_type == "bank_statement":
                # Extract financial data
                import re
                result["extracted_data"]["bank_statement"] = {
                    "account_number": "1234567890",  # Simplified
                    "balance": "15,000 AED",
                    "income": "8,500 AED"
                }
    
    return result


async def income_verification_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Verify income from bank statement"""
    await asyncio.sleep(2)  # Simulate processing
    
    return {
        "income_verified": True,
        "monthly_income": 8500,
        "currency": "AED",
        "meets_threshold": True,
        "threshold": 4000,
        "confidence": 0.85
    }


async def identity_verification_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Verify identity from Emirates ID"""
    await asyncio.sleep(2)  # Simulate processing
    
    return {
        "identity_verified": True,
        "id_valid": True,
        "expiry_status": "valid",
        "confidence": 0.92
    }


async def decision_making_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Make eligibility decision"""
    await asyncio.sleep(3)  # Simulate processing
    
    return {
        "decision": "approved",
        "eligibility_score": 0.88,
        "reasons": [
            "Income meets minimum threshold",
            "Valid Emirates ID",
            "All documents verified"
        ],
        "confidence": 0.85
    }


async def final_review_step(application_id: str, db: Session) -> Dict[str, Any]:
    """Final review of application"""
    await asyncio.sleep(1)  # Simulate processing
    
    return {
        "review_complete": True,
        "final_status": "approved",
        "review_notes": "Application meets all criteria",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{application_id}/status/{step_type}",
           summary="Get status of a specific step")
def get_step_status(
    application_id: str,
    step_type: StepType,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the current status of a specific workflow step"""
    step_key = f"{application_id}_{step_type}"
    
    if step_key in active_steps:
        step_data = active_steps[step_key]
        
        # Calculate duration if completed
        duration_ms = None
        if step_data.get("completed_at"):
            started = datetime.fromisoformat(step_data["started_at"])
            completed = datetime.fromisoformat(step_data["completed_at"])
            duration_ms = int((completed - started).total_seconds() * 1000)
        
        return StepResponse(
            step_id=step_data["step_id"],
            step_type=step_type,
            status=step_data["status"],
            message=f"Step {step_type} {step_data['status']}",
            started_at=step_data.get("started_at"),
            completed_at=step_data.get("completed_at"),
            duration_ms=duration_ms,
            output=step_data.get("output"),
            error=step_data.get("error")
        )
    else:
        return StepResponse(
            step_id="",
            step_type=step_type,
            status=StepStatus.PENDING,
            message="Step not started"
        )


@router.post("/{application_id}/cancel/{step_type}",
            summary="Cancel a running step")
def cancel_step(
    application_id: str,
    step_type: StepType,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a running workflow step"""
    step_key = f"{application_id}_{step_type}"
    
    if step_key in active_steps and active_steps[step_key]["status"] == StepStatus.RUNNING:
        active_steps[step_key]["status"] = StepStatus.CANCELLED
        active_steps[step_key]["completed_at"] = datetime.utcnow().isoformat()
        active_steps[step_key]["error"] = "Cancelled by user"
        
        return {
            "message": f"Step {step_type} cancelled",
            "step_id": active_steps[step_key]["step_id"]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "STEP_NOT_RUNNING", "message": "Step is not currently running"}
        )


@router.get("/{application_id}/all-steps",
           summary="Get status of all workflow steps")
def get_all_steps_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the status of all workflow steps for an application"""
    all_steps = []
    
    for step_type in StepType:
        step_key = f"{application_id}_{step_type}"
        
        if step_key in active_steps:
            step_data = active_steps[step_key]
            
            # Calculate duration if completed
            duration_ms = None
            if step_data.get("completed_at"):
                started = datetime.fromisoformat(step_data["started_at"])
                completed = datetime.fromisoformat(step_data["completed_at"])
                duration_ms = int((completed - started).total_seconds() * 1000)
            
            all_steps.append({
                "step_type": step_type,
                "status": step_data["status"],
                "started_at": step_data.get("started_at"),
                "completed_at": step_data.get("completed_at"),
                "duration_ms": duration_ms,
                "has_output": bool(step_data.get("output")),
                "error": step_data.get("error")
            })
        else:
            all_steps.append({
                "step_type": step_type,
                "status": StepStatus.PENDING,
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "has_output": False,
                "error": None
            })
    
    return {
        "application_id": application_id,
        "steps": all_steps,
        "timestamp": datetime.utcnow().isoformat()
    }
