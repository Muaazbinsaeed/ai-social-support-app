"""
Enhanced Workflow Steps Router with Manual Step Execution
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application, WorkflowState
from app.document_processing.document_models import Document
from app.shared.logging_config import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)
router = APIRouter(prefix="/workflow-steps", tags=["workflow-steps"])

# Thread pool for executing steps with timeout
executor = ThreadPoolExecutor(max_workers=4)

# Store for step execution status
step_execution_status = {}


class StepExecutionRequest(BaseModel):
    """Request to execute a workflow step"""
    step_name: str = Field(..., description="Name of the step to execute")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Timeout in seconds")
    force: bool = Field(default=False, description="Force execution even if prerequisites not met")


class StepExecutionResponse(BaseModel):
    """Response from step execution"""
    step_name: str
    status: str  # started, running, completed, failed, timeout, cancelled
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0


class WorkflowStepsStatus(BaseModel):
    """Status of all workflow steps"""
    application_id: str
    current_state: str
    overall_progress: int
    steps: List[Dict[str, Any]]


# Step definitions with their execution logic
WORKFLOW_STEPS = {
    "ocr_extraction": {
        "name": "OCR Text Extraction",
        "description": "Extract text from documents using OCR",
        "prerequisites": [],  # No prerequisites - just need documents in DB
        "timeout": 60
    },
    "document_validation": {
        "name": "Document Validation",
        "description": "Validate document format and content",
        "prerequisites": ["ocr_extraction"],
        "timeout": 30
    },
    "income_analysis": {
        "name": "Income Analysis",
        "description": "Analyze income from bank statements",
        "prerequisites": ["document_validation"],
        "timeout": 45
    },
    "identity_verification": {
        "name": "Identity Verification",
        "description": "Verify identity from Emirates ID",
        "prerequisites": ["document_validation"],
        "timeout": 45
    },
    "ai_analysis": {
        "name": "AI Document Analysis",
        "description": "AI-based comprehensive document analysis",
        "prerequisites": ["income_analysis", "identity_verification"],
        "timeout": 90
    },
    "decision_making": {
        "name": "Decision Making",
        "description": "Make eligibility decision",
        "prerequisites": ["ai_analysis"],
        "timeout": 60
    }
}


def execute_ocr_extraction(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute OCR extraction step"""
    logger.info(f"Starting OCR extraction for application {application_id}")
    
    # Get documents
    documents = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id)
    ).all()
    
    if not documents:
        raise Exception("No documents found for OCR extraction")
    
    results = {}
    for doc in documents:
        # Simulate OCR processing
        time.sleep(2)  # Simulate processing time
        
        if doc.document_type == "emirates_id":
            extracted_text = """
UNITED ARAB EMIRATES
IDENTITY CARD

Name: AHMED ALI HASSAN
Emirates ID: 784-1990-1234567-8
Date of Birth: 15/03/1990
Nationality: UAE
Gender: Male
Card Number: 123-4567-8901234-5
Expiry Date: 15/03/2025
            """.strip()
            confidence = 0.92
        else:  # bank_statement
            extracted_text = """
EMIRATES NBD BANK
ACCOUNT STATEMENT

Account Number: 1234567890123
Account Holder: AHMED ALI HASSAN
Statement Period: 01/01/2024 - 31/01/2024
Opening Balance: AED 15,234.50
Closing Balance: AED 18,456.75
Monthly Income: AED 8,500.00
Average Balance: AED 19,845.63
            """.strip()
            confidence = 0.88
        
        # Update document with OCR results
        doc.extracted_text = extracted_text
        doc.ocr_confidence = confidence
        doc.ocr_processing_time_ms = 2000
        doc.status = "ocr_completed"
        
        results[doc.document_type] = {
            "text": extracted_text[:500],
            "confidence": confidence,
            "processing_time_ms": 2000
        }
    
    db.commit()
    
    return {
        "status": "completed",
        "documents_processed": len(documents),
        "results": results
    }


def execute_document_validation(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute document validation step"""
    logger.info(f"Starting document validation for application {application_id}")
    
    documents = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id)
    ).all()
    
    validation_results = {}
    for doc in documents:
        time.sleep(1)  # Simulate validation time
        
        # Check if OCR text exists
        if not doc.extracted_text:
            validation_results[doc.document_type] = {
                "valid": False,
                "errors": ["No OCR text available"]
            }
            continue
        
        # Validate based on document type
        if doc.document_type == "emirates_id":
            # Check for Emirates ID pattern
            import re
            id_pattern = r'784-\d{4}-\d{7}-\d'
            has_id = bool(re.search(id_pattern, doc.extracted_text))
            
            validation_results[doc.document_type] = {
                "valid": has_id,
                "checks": {
                    "has_emirates_id": has_id,
                    "has_name": "Name:" in doc.extracted_text,
                    "has_expiry": "Expiry" in doc.extracted_text
                }
            }
        else:  # bank_statement
            validation_results[doc.document_type] = {
                "valid": True,
                "checks": {
                    "has_account_number": "Account Number:" in doc.extracted_text,
                    "has_balance": "Balance:" in doc.extracted_text,
                    "has_transactions": "Income:" in doc.extracted_text or "Credit" in doc.extracted_text
                }
            }
    
    return {
        "status": "completed",
        "validation_results": validation_results,
        "all_valid": all(r["valid"] for r in validation_results.values())
    }


def execute_income_analysis(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute income analysis step"""
    logger.info(f"Starting income analysis for application {application_id}")
    
    # Get bank statement
    bank_doc = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id),
        Document.document_type == "bank_statement"
    ).first()
    
    if not bank_doc or not bank_doc.extracted_text:
        raise Exception("Bank statement not found or not processed")
    
    time.sleep(2)  # Simulate analysis time
    
    # Extract income information
    import re
    
    income_match = re.search(r'Monthly Income:\s*AED\s*([\d,]+\.?\d*)', bank_doc.extracted_text)
    balance_match = re.search(r'Average Balance:\s*AED\s*([\d,]+\.?\d*)', bank_doc.extracted_text)
    
    monthly_income = 0
    if income_match:
        monthly_income = float(income_match.group(1).replace(',', ''))
    
    average_balance = 0
    if balance_match:
        average_balance = float(balance_match.group(1).replace(',', ''))
    
    # Analyze income eligibility
    income_eligible = monthly_income >= 4000
    balance_eligible = average_balance >= 1500
    
    analysis_result = {
        "monthly_income": monthly_income,
        "average_balance": average_balance,
        "income_eligible": income_eligible,
        "balance_eligible": balance_eligible,
        "overall_eligible": income_eligible and balance_eligible,
        "confidence": 0.85
    }
    
    # Store analysis result
    bank_doc.analysis_result = analysis_result
    db.commit()
    
    return {
        "status": "completed",
        "analysis": analysis_result
    }


def execute_identity_verification(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute identity verification step"""
    logger.info(f"Starting identity verification for application {application_id}")
    
    # Get Emirates ID document
    emirates_doc = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id),
        Document.document_type == "emirates_id"
    ).first()
    
    if not emirates_doc or not emirates_doc.extracted_text:
        raise Exception("Emirates ID not found or not processed")
    
    time.sleep(2)  # Simulate verification time
    
    # Extract identity information
    import re
    
    id_match = re.search(r'784-\d{4}-\d{7}-\d', emirates_doc.extracted_text)
    name_match = re.search(r'Name:\s*([^\n]+)', emirates_doc.extracted_text)
    
    emirates_id = id_match.group(0) if id_match else None
    name = name_match.group(1).strip() if name_match else None
    
    # Get application data
    application = db.query(Application).filter(
        Application.id == uuid.UUID(application_id)
    ).first()
    
    # Verify identity
    id_matches = False
    if application and emirates_id:
        id_matches = application.emirates_id == emirates_id
    
    verification_result = {
        "extracted_id": emirates_id,
        "extracted_name": name,
        "id_matches_application": id_matches,
        "verification_status": "verified" if id_matches else "mismatch",
        "confidence": 0.90
    }
    
    # Store verification result
    emirates_doc.analysis_result = verification_result
    db.commit()
    
    return {
        "status": "completed",
        "verification": verification_result
    }


def execute_ai_analysis(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute AI-based comprehensive analysis"""
    logger.info(f"Starting AI analysis for application {application_id}")
    
    # Get all documents and previous analysis
    documents = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id)
    ).all()
    
    time.sleep(3)  # Simulate AI processing time
    
    # Combine all analysis results
    combined_analysis = {
        "documents_analyzed": len(documents),
        "income_verification": None,
        "identity_verification": None,
        "risk_score": 0.0,
        "recommendations": []
    }
    
    for doc in documents:
        if doc.analysis_result:
            if doc.document_type == "bank_statement":
                combined_analysis["income_verification"] = doc.analysis_result
            elif doc.document_type == "emirates_id":
                combined_analysis["identity_verification"] = doc.analysis_result
    
    # Calculate risk score
    risk_factors = []
    
    if combined_analysis["income_verification"]:
        if not combined_analysis["income_verification"].get("income_eligible"):
            risk_factors.append("Low income")
        if not combined_analysis["income_verification"].get("balance_eligible"):
            risk_factors.append("Low balance")
    
    if combined_analysis["identity_verification"]:
        if not combined_analysis["identity_verification"].get("id_matches_application"):
            risk_factors.append("ID mismatch")
    
    combined_analysis["risk_score"] = len(risk_factors) * 0.3
    combined_analysis["risk_factors"] = risk_factors
    
    # Generate recommendations
    if combined_analysis["risk_score"] < 0.3:
        combined_analysis["recommendations"].append("Approve application")
    elif combined_analysis["risk_score"] < 0.6:
        combined_analysis["recommendations"].append("Manual review recommended")
    else:
        combined_analysis["recommendations"].append("High risk - Consider rejection")
    
    return {
        "status": "completed",
        "ai_analysis": combined_analysis
    }


def execute_decision_making(application_id: str, db: Session) -> Dict[str, Any]:
    """Execute final decision making"""
    logger.info(f"Starting decision making for application {application_id}")
    
    # Get all analysis results
    documents = db.query(Document).filter(
        Document.application_id == uuid.UUID(application_id)
    ).all()
    
    time.sleep(2)  # Simulate decision time
    
    # Compile decision factors
    income_eligible = False
    identity_verified = False
    
    for doc in documents:
        if doc.analysis_result:
            if doc.document_type == "bank_statement":
                income_eligible = doc.analysis_result.get("overall_eligible", False)
            elif doc.document_type == "emirates_id":
                identity_verified = doc.analysis_result.get("id_matches_application", False)
    
    # Make decision
    decision = "approved" if (income_eligible and identity_verified) else "rejected"
    confidence = 0.95 if (income_eligible and identity_verified) else 0.85
    
    decision_result = {
        "decision": decision,
        "confidence": confidence,
        "factors": {
            "income_eligible": income_eligible,
            "identity_verified": identity_verified
        },
        "reason": "All criteria met" if decision == "approved" else "Eligibility criteria not met",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Update application status
    application = db.query(Application).filter(
        Application.id == uuid.UUID(application_id)
    ).first()
    
    if application:
        application.status = decision
        application.progress = 100
        db.commit()
    
    return {
        "status": "completed",
        "decision": decision_result
    }


# Step execution functions mapping
STEP_EXECUTORS = {
    "ocr_extraction": execute_ocr_extraction,
    "document_validation": execute_document_validation,
    "income_analysis": execute_income_analysis,
    "identity_verification": execute_identity_verification,
    "ai_analysis": execute_ai_analysis,
    "decision_making": execute_decision_making
}


@router.get("/status/{application_id}", response_model=WorkflowStepsStatus)
def get_workflow_steps_status(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get status of all workflow steps"""
    try:
        # Validate application exists and belongs to user
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
        
        # Get workflow states
        workflow_states = db.query(WorkflowState).filter(
            WorkflowState.application_id == app_uuid
        ).order_by(WorkflowState.created_at.desc()).all()
        
        # Build steps status
        steps_status = []
        for step_name, step_info in WORKFLOW_STEPS.items():
            # Check if step has been executed
            step_state = None
            for state in workflow_states:
                if state.step_name == step_name:
                    step_state = state
                    break
            
            # Check if step is currently executing
            exec_status = step_execution_status.get(f"{application_id}_{step_name}")
            
            step_status = {
                "name": step_name,
                "display_name": step_info["name"],
                "description": step_info["description"],
                "status": "not_started",
                "can_execute": False,
                "progress": 0,
                "output": None,
                "error": None,
                "started_at": None,
                "completed_at": None,
                "duration_seconds": None
            }
            
            # Update status based on execution status
            if exec_status:
                step_status["status"] = exec_status["status"]
                step_status["progress"] = exec_status.get("progress", 0)
                step_status["started_at"] = exec_status.get("started_at")
                step_status["completed_at"] = exec_status.get("completed_at")
                step_status["output"] = exec_status.get("output")
                step_status["error"] = exec_status.get("error")
                if exec_status.get("duration_seconds"):
                    step_status["duration_seconds"] = exec_status["duration_seconds"]
            elif step_state:
                step_status["status"] = step_state.step_status
                # Try to parse output from message if it contains JSON
                if step_state.step_message and "successfully:" in step_state.step_message:
                    try:
                        output_json = step_state.step_message.split("successfully:")[1].strip()
                        step_status["output"] = json.loads(output_json)
                    except:
                        pass
                step_status["started_at"] = step_state.created_at
                step_status["completed_at"] = step_state.completed_at
            
            # Check if prerequisites are met
            prerequisites_met = True
            for prereq in step_info.get("prerequisites", []):
                prereq_status = None
                for s in steps_status:
                    if s["name"] == prereq:
                        prereq_status = s["status"]
                        break
                if prereq_status != "completed":
                    # Check in workflow states
                    prereq_state = db.query(WorkflowState).filter(
                        WorkflowState.application_id == app_uuid,
                        WorkflowState.step_name == prereq,
                        WorkflowState.step_status == "completed"
                    ).first()
                    if not prereq_state:
                        prerequisites_met = False
                        break
            
            # Special case: check if documents are uploaded
            if "documents_uploaded" in step_info.get("prerequisites", []):
                docs_count = db.query(Document).filter(
                    Document.application_id == app_uuid
                ).count()
                if docs_count == 0:
                    prerequisites_met = False
                else:
                    # Documents exist, so consider this prerequisite met
                    prerequisites_met = True
            
            # For OCR, also check if documents exist
            if step_name == "ocr_extraction" and prerequisites_met:
                docs_count = db.query(Document).filter(
                    Document.application_id == app_uuid
                ).count()
                if docs_count == 0:
                    prerequisites_met = False
            
            step_status["can_execute"] = prerequisites_met and step_status["status"] not in ["running", "completed"]
            
            steps_status.append(step_status)
        
        # Calculate overall progress
        completed_steps = sum(1 for s in steps_status if s["status"] == "completed")
        total_steps = len(steps_status)
        overall_progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        return WorkflowStepsStatus(
            application_id=application_id,
            current_state=application.status,
            overall_progress=overall_progress,
            steps=steps_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow steps status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "STATUS_FETCH_FAILED", "message": str(e)}
        )


@router.post("/execute/{application_id}", response_model=StepExecutionResponse)
def execute_workflow_step(
    application_id: str,
    request: StepExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute a specific workflow step manually"""
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
        
        # Validate step exists
        if request.step_name not in WORKFLOW_STEPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_STEP", "message": f"Unknown step: {request.step_name}"}
            )
        
        # Check if step is already running
        exec_key = f"{application_id}_{request.step_name}"
        if exec_key in step_execution_status:
            if step_execution_status[exec_key]["status"] == "running":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": "STEP_RUNNING", "message": "Step is already running"}
                )
        
        # Check prerequisites if not forcing
        if not request.force:
            step_info = WORKFLOW_STEPS[request.step_name]
            for prereq in step_info.get("prerequisites", []):
                if prereq == "documents_uploaded":
                    docs_count = db.query(Document).filter(
                        Document.application_id == app_uuid
                    ).count()
                    if docs_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"error": "PREREQUISITES_NOT_MET", "message": "Documents not uploaded"}
                        )
                else:
                    prereq_state = db.query(WorkflowState).filter(
                        WorkflowState.application_id == app_uuid,
                        WorkflowState.step_name == prereq,
                        WorkflowState.step_status == "completed"
                    ).first()
                    if not prereq_state:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"error": "PREREQUISITES_NOT_MET", "message": f"Prerequisite step '{prereq}' not completed"}
                        )
        
        # Start execution
        started_at = datetime.utcnow()
        step_execution_status[exec_key] = {
            "status": "running",
            "started_at": started_at,
            "progress": 10
        }
        
        # Execute step in background with timeout
        def run_step():
            try:
                # Get executor function
                executor_func = STEP_EXECUTORS.get(request.step_name)
                if not executor_func:
                    raise Exception(f"No executor for step: {request.step_name}")
                
                # Update progress
                step_execution_status[exec_key]["progress"] = 30
                
                # Execute with timeout
                future = executor.submit(executor_func, application_id, db)
                try:
                    result = future.result(timeout=request.timeout_seconds)
                    
                    # Success
                    completed_at = datetime.utcnow()
                    duration = (completed_at - started_at).total_seconds()
                    
                    step_execution_status[exec_key].update({
                        "status": "completed",
                        "completed_at": completed_at,
                        "duration_seconds": duration,
                        "output": result,
                        "progress": 100
                    })
                    
                    # Save to database
                    workflow_state = WorkflowState(
                        application_id=app_uuid,
                        current_state=request.step_name,
                        step_name=request.step_name,
                        step_status="completed",
                        step_message=f"Step completed successfully: {json.dumps(result)[:500]}",
                        completed_at=completed_at
                    )
                    db.add(workflow_state)
                    db.commit()
                    
                except FutureTimeoutError:
                    # Timeout
                    step_execution_status[exec_key].update({
                        "status": "timeout",
                        "error": f"Step execution timed out after {request.timeout_seconds} seconds",
                        "progress": 0
                    })
                    future.cancel()
                    
            except Exception as e:
                # Error
                step_execution_status[exec_key].update({
                    "status": "failed",
                    "error": str(e),
                    "progress": 0
                })
                
                # Save error to database
                workflow_state = WorkflowState(
                    application_id=app_uuid,
                    current_state=request.step_name,
                    step_name=request.step_name,
                    step_status="failed",
                    step_message=str(e),
                    error_message=str(e)
                )
                db.add(workflow_state)
                db.commit()
        
        # Run in background
        background_tasks.add_task(run_step)
        
        return StepExecutionResponse(
            step_name=request.step_name,
            status="started",
            started_at=started_at,
            progress=10
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute step: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "EXECUTION_FAILED", "message": str(e)}
        )


@router.post("/cancel/{application_id}/{step_name}")
def cancel_workflow_step(
    application_id: str,
    step_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a running workflow step"""
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
        
        # Check if step is running
        exec_key = f"{application_id}_{step_name}"
        if exec_key not in step_execution_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "STEP_NOT_RUNNING", "message": "Step is not running"}
            )
        
        if step_execution_status[exec_key]["status"] != "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "STEP_NOT_RUNNING", "message": f"Step is {step_execution_status[exec_key]['status']}"}
            )
        
        # Cancel the step
        step_execution_status[exec_key].update({
            "status": "cancelled",
            "completed_at": datetime.utcnow(),
            "error": "Cancelled by user"
        })
        
        return {"message": "Step cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel step: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CANCEL_FAILED", "message": str(e)}
        )
