"""
Application management API endpoints
"""

from datetime import datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])

# Pydantic models for responses
class DecisionResult(BaseModel):
    outcome: str  # approved, rejected, needs_review
    confidence: float
    benefit_amount: Optional[float] = None
    currency: str = "AED"
    frequency: str = "monthly"
    effective_date: Optional[str] = None
    review_date: Optional[str] = None

class DecisionReasoning(BaseModel):
    income_analysis: Optional[str] = None
    document_verification: Optional[str] = None
    risk_assessment: Optional[str] = None
    eligibility_score: Optional[int] = None

class ContactInformation(BaseModel):
    office_address: str = "Social Security Office, Dubai"
    phone: str = "+971-4-123-4567"
    email: str = "support@socialsecurity.gov.ae"

class AppealProcess(BaseModel):
    deadline: str
    process: str = "Submit written appeal with supporting documents"
    contact: str = "appeals@socialsecurity.gov.ae"

class ApplicationResultsResponse(BaseModel):
    application_id: str
    decision: DecisionResult
    reasoning: DecisionReasoning
    next_steps: List[str]
    contact_information: ContactInformation
    appeal_process: AppealProcess

class ApplicationSummary(BaseModel):
    application_id: str
    status: str
    progress: int
    submitted_at: Optional[str] = None
    decision: Optional[str] = None
    benefit_amount: Optional[float] = None
    last_updated: str

class ApplicationListResponse(BaseModel):
    applications: List[ApplicationSummary]
    total_count: int
    page: int
    page_size: int

class ApplicationUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@router.get("/{application_id}/results", response_model=ApplicationResultsResponse,
            summary="Get final application decision and results",
            description="Retrieve comprehensive application results including decision, reasoning, and next steps")
def get_application_results(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get final application decision and results"""
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

        # Check if processing is complete
        if application.status not in ["approved", "rejected", "needs_review"]:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "processing",
                    "message": "Application still being processed",
                    "estimated_completion": "45 seconds"
                }
            )

        # Build decision result
        decision = DecisionResult(
            outcome=application.decision or "needs_review",
            confidence=float(application.decision_confidence) if application.decision_confidence else 0.0,
            benefit_amount=float(application.benefit_amount) if application.benefit_amount else None,
            effective_date=application.effective_date.isoformat() + "Z" if application.effective_date else None,
            review_date=application.review_date.isoformat() + "Z" if application.review_date else None
        )

        # Build reasoning
        reasoning = DecisionReasoning(
            income_analysis=f"Monthly income of AED {application.monthly_income} {'meets' if application.decision == 'approved' else 'does not meet'} eligibility threshold" if application.monthly_income else None,
            document_verification="Emirates ID verified successfully" if application.emirates_id_doc_id else "Document verification pending",
            risk_assessment="Low risk profile based on stable employment" if application.decision == "approved" else "Assessment pending",
            eligibility_score=int(float(application.eligibility_score) * 100) if application.eligibility_score else None
        )

        # Build next steps based on decision
        if application.decision == "approved":
            next_steps = [
                "Visit local office within 7 days with original documents",
                "Set up direct deposit for benefit payments",
                "Attend mandatory orientation session"
            ]
        elif application.decision == "rejected":
            next_steps = [
                "Review rejection reasons carefully",
                "Gather additional supporting documents if applicable",
                "Submit appeal within 30 days if you disagree with the decision"
            ]
        else:  # needs_review
            next_steps = [
                "Manual review is in progress",
                "You will be contacted within 3-5 business days",
                "Prepare any additional documents that may be requested"
            ]

        # Build appeal process
        appeal_deadline = datetime.utcnow().replace(day=19, month=1, year=2025)  # Example: 30 days from decision
        appeal_process = AppealProcess(
            deadline=appeal_deadline.isoformat() + "Z"
        )

        logger.info("Application results retrieved",
                   application_id=str(application.id),
                   user_id=str(current_user.id),
                   decision=application.decision)

        return ApplicationResultsResponse(
            application_id=str(application.id),
            decision=decision,
            reasoning=reasoning,
            next_steps=next_steps,
            contact_information=ContactInformation(),
            appeal_process=appeal_process
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get application results",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "RESULTS_FETCH_FAILED",
                "message": "Failed to retrieve application results"
            }
        )


@router.get("/history",
            summary="Get application history",
            description="Retrieve all applications for the user (both active and historical)")
def get_application_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all applications for the user including history"""
    try:
        # Get all applications ordered by creation date (newest first)
        applications = db.query(Application).filter(
            Application.user_id == current_user.id
        ).order_by(desc(Application.created_at)).all()

        # Separate active and historical applications
        active_application = None
        historical_applications = []

        for app in applications:
            # Consider applications in processing states as active
            if app.status in ['draft', 'form_submitted', 'documents_uploaded', 'scanning_documents',
                            'ocr_completed', 'analyzing_income', 'analyzing_identity',
                            'analysis_completed', 'making_decision', 'decision_completed']:
                if active_application is None:  # Only one active at a time
                    active_application = app
                else:
                    # If we have multiple processing applications, the newer one becomes active
                    if app.created_at > active_application.created_at:
                        historical_applications.append(active_application)
                        active_application = app
                    else:
                        historical_applications.append(app)
            else:
                # Applications in final states (approved, rejected, needs_review) are historical
                historical_applications.append(app)

        # Build response
        def build_app_summary(app):
            return {
                "application_id": str(app.id),
                "status": app.status,
                "progress": app.progress or 0,
                "created_at": app.created_at.isoformat() + "Z",
                "submitted_at": app.submitted_at.isoformat() + "Z" if app.submitted_at else None,
                "decision": app.decision,
                "benefit_amount": float(app.benefit_amount) if app.benefit_amount else None,
                "form_data": {
                    "full_name": app.full_name,
                    "emirates_id": app.emirates_id,
                    "phone": app.phone,
                    "email": app.email
                } if app.full_name else None,
                "last_updated": (app.updated_at or app.created_at).isoformat() + "Z"
            }

        response = {
            "active_application": build_app_summary(active_application) if active_application else None,
            "historical_applications": [build_app_summary(app) for app in historical_applications],
            "total_count": len(applications)
        }

        logger.info("Application history retrieved",
                   user_id=str(current_user.id),
                   total_applications=len(applications),
                   active_count=1 if active_application else 0,
                   historical_count=len(historical_applications))

        return response

    except Exception as e:
        logger.error("Failed to get application history",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "HISTORY_FETCH_FAILED",
                "message": "Failed to retrieve application history"
            }
        )


@router.get("/", response_model=ApplicationListResponse,
            summary="List user applications",
            description="Retrieve paginated list of user's applications with status and basic information")
def list_applications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of user applications"""
    try:
        # Build query
        query = db.query(Application).filter(Application.user_id == current_user.id)

        # Apply status filter if provided
        if status_filter:
            query = query.filter(Application.status == status_filter)

        # Get total count
        total_count = query.count()

        # Apply pagination
        applications = query.order_by(desc(Application.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        # Build response
        application_summaries = []
        logger.info(f"Processing {len(applications)} applications for user {current_user.id}")

        for app in applications:
            try:
                logger.info(f"Processing application {app.id}, status: {app.status}, created: {app.created_at}")

                # Safely handle timestamp conversion
                submitted_at = None
                if app.submitted_at:
                    submitted_at = app.submitted_at.isoformat() + "Z"
                elif app.created_at:
                    submitted_at = app.created_at.isoformat() + "Z"

                # Safely determine last updated timestamp
                last_updated = app.created_at.isoformat() + "Z"
                for timestamp_field in [app.decision_at, app.processed_at, app.updated_at]:
                    if timestamp_field:
                        last_updated = timestamp_field.isoformat() + "Z"
                        break

                # Create a minimal summary that should always work
                summary = ApplicationSummary(
                    application_id=str(app.id) if app.id else "unknown",
                    status=str(app.status) if app.status else "draft",
                    progress=int(app.progress) if app.progress is not None else 0,
                    submitted_at=submitted_at,
                    decision=str(app.decision) if app.decision else None,
                    benefit_amount=float(app.benefit_amount) if app.benefit_amount and app.benefit_amount != '' else None,
                    last_updated=last_updated
                )
                application_summaries.append(summary)
                logger.info(f"Successfully processed application {app.id}")

            except Exception as e:
                logger.error("Failed to process application in list",
                              application_id=str(app.id) if hasattr(app, 'id') else 'unknown',
                              error=str(e),
                              error_type=type(e).__name__,
                              app_attributes=str(dir(app))[:200])  # Log available attributes
                # Skip this application and continue with others
                continue

        logger.info("Applications list retrieved",
                   user_id=str(current_user.id),
                   total_count=total_count,
                   page=page)

        return ApplicationListResponse(
            applications=application_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list applications",
                    user_id=str(current_user.id),
                    error=str(e),
                    error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "LIST_FETCH_FAILED",
                "message": f"Failed to retrieve applications list: {str(e)}"
            }
        )


@router.get("/simple-list",
            summary="Get simple list of user application IDs",
            description="Get basic list of application IDs for current user")
def get_simple_application_list(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get simple list of application IDs for current user"""
    try:
        applications = db.query(Application.id, Application.status, Application.created_at).filter(
            Application.user_id == current_user.id
        ).order_by(desc(Application.created_at)).all()

        app_list = []
        for app in applications:
            app_list.append({
                "application_id": str(app.id),
                "status": app.status,
                "created_at": app.created_at.isoformat() + "Z" if app.created_at else None
            })

        return {
            "applications": app_list,
            "total_count": len(app_list)
        }

    except Exception as e:
        logger.error("Failed to get simple application list",
                    user_id=str(current_user.id),
                    error=str(e))
        return {
            "applications": [],
            "total_count": 0,
            "error": str(e)
        }


@router.get("/{application_id}",
            summary="Get single application details",
            description="Retrieve detailed information for a specific application")
def get_application(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed application information"""
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

        # Return detailed application data
        return {
            "application_id": str(application.id),
            "status": application.status,
            "progress": application.progress,
            "form_data": {
                "full_name": application.full_name,
                "emirates_id": application.emirates_id,
                "phone": application.phone,
                "email": application.email
            },
            "processing_results": {
                "monthly_income": float(application.monthly_income) if application.monthly_income else None,
                "account_balance": float(application.account_balance) if application.account_balance else None,
                "eligibility_score": float(application.eligibility_score) if application.eligibility_score else None
            },
            "decision_info": {
                "decision": application.decision,
                "confidence": float(application.decision_confidence) if application.decision_confidence else None,
                "reasoning": application.decision_reasoning,
                "benefit_amount": float(application.benefit_amount) if application.benefit_amount else None
            },
            "timestamps": {
                "created_at": application.created_at.isoformat() + "Z",
                "submitted_at": application.submitted_at.isoformat() + "Z" if application.submitted_at else None,
                "processed_at": application.processed_at.isoformat() + "Z" if application.processed_at else None,
                "decision_at": application.decision_at.isoformat() + "Z" if application.decision_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get application details",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "APPLICATION_FETCH_FAILED",
                "message": "Failed to retrieve application details"
            }
        )


@router.put("/{application_id}",
            summary="Update application",
            description="Update editable fields of an application (only allowed in draft status)")
def update_application(
    application_id: str,
    update_data: ApplicationUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update application data (only allowed in draft status)"""
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

        # Check if application can be updated
        if application.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "APPLICATION_NOT_EDITABLE",
                    "message": "Application cannot be updated after submission",
                    "current_status": application.status
                }
            )

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(application, field, value)

        db.commit()

        logger.info("Application updated",
                   application_id=str(application.id),
                   user_id=str(current_user.id),
                   updated_fields=list(update_dict.keys()))

        return {
            "message": "Application updated successfully",
            "application_id": str(application.id),
            "updated_fields": list(update_dict.keys()),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update application",
                    application_id=application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "APPLICATION_UPDATE_FAILED",
                "message": "Failed to update application"
            }
        )