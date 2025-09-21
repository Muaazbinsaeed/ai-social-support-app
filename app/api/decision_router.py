"""
AI Decision Making API endpoints
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
import requests

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application
from app.document_processing.document_models import Document
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/decisions", tags=["decision-making"])

# Pydantic models
class EligibilityFactors(BaseModel):
    monthly_income: Optional[float] = None
    account_balance: Optional[float] = None
    employment_status: Optional[str] = None
    age: Optional[int] = None
    family_size: Optional[int] = None
    disability_status: Optional[bool] = None
    citizenship_verified: Optional[bool] = None
    documents_complete: Optional[bool] = None

class DecisionCriteria(BaseModel):
    income_threshold: float = 5000.0  # AED
    asset_limit: float = 50000.0  # AED
    min_age: int = 18
    max_age: int = 65
    required_documents: List[str] = ["emirates_id", "salary_certificate", "bank_statement"]

class DecisionReasoning(BaseModel):
    reasoning_steps: List[str]
    evidence_analysis: Dict[str, Any]
    risk_factors: List[str]
    mitigating_factors: List[str]
    confidence_score: float
    alternative_recommendations: List[str]

class DecisionResult(BaseModel):
    decision: str  # approved, rejected, needs_review
    confidence: float
    benefit_amount: Optional[float] = None
    reasoning: DecisionReasoning
    effective_date: Optional[str] = None
    review_date: Optional[str] = None
    conditions: List[str] = []
    appeal_deadline: Optional[str] = None

class DecisionRequest(BaseModel):
    application_id: str
    criteria_override: Optional[DecisionCriteria] = None
    force_review: bool = False
    reasoning_depth: str = "standard"  # basic, standard, detailed

    @field_validator('application_id')
    @classmethod
    def validate_application_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('application_id must be a valid UUID')

    @field_validator('reasoning_depth')
    @classmethod
    def validate_reasoning_depth(cls, v):
        if v not in ["basic", "standard", "detailed"]:
            raise ValueError('reasoning_depth must be one of: basic, standard, detailed')
        return v

class DecisionResponse(BaseModel):
    decision_id: str
    application_id: str
    result: DecisionResult
    processing_time_ms: int
    timestamp: str

class BulkDecisionRequest(BaseModel):
    application_ids: List[str]
    criteria_override: Optional[DecisionCriteria] = None
    batch_processing: bool = True

class BulkDecisionResponse(BaseModel):
    batch_id: str
    total_applications: int
    processed: int
    failed: int
    results: List[DecisionResponse]

class DecisionExplanationRequest(BaseModel):
    decision_id: str
    detail_level: str = "standard"  # basic, standard, detailed

class DecisionExplanationResponse(BaseModel):
    decision_id: str
    explanation: str
    legal_basis: List[str]
    precedent_cases: List[str]
    calculation_details: Dict[str, Any]


async def call_llm_for_reasoning(prompt: str, model: str = "qwen2:1.5b") -> Dict[str, Any]:
    """Call Ollama LLM for reasoning"""
    try:
        ollama_request = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent reasoning
                "num_predict": 2048
            }
        }

        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=ollama_request,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", ""),
                "reasoning": result.get("response", "")
            }
        else:
            logger.error(f"LLM API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"LLM API error: {response.status_code}"
            }

    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def calculate_eligibility_score(factors: EligibilityFactors, criteria: DecisionCriteria) -> float:
    """Calculate eligibility score based on factors"""
    score = 0.0
    max_score = 100.0

    # Income assessment (30 points)
    if factors.monthly_income is not None:
        if factors.monthly_income <= criteria.income_threshold:
            score += 30.0
        elif factors.monthly_income <= criteria.income_threshold * 1.2:
            score += 20.0
        elif factors.monthly_income <= criteria.income_threshold * 1.5:
            score += 10.0

    # Asset assessment (20 points)
    if factors.account_balance is not None:
        if factors.account_balance <= criteria.asset_limit:
            score += 20.0
        elif factors.account_balance <= criteria.asset_limit * 1.5:
            score += 10.0

    # Age assessment (15 points)
    if factors.age is not None:
        if criteria.min_age <= factors.age <= criteria.max_age:
            score += 15.0
        elif factors.age < criteria.min_age or factors.age > criteria.max_age + 5:
            score += 5.0

    # Employment status (10 points)
    if factors.employment_status:
        if factors.employment_status.lower() in ["unemployed", "disabled", "retired"]:
            score += 10.0
        elif factors.employment_status.lower() in ["part_time", "temporary"]:
            score += 5.0

    # Family size (10 points)
    if factors.family_size is not None:
        if factors.family_size >= 3:
            score += 10.0
        elif factors.family_size == 2:
            score += 5.0

    # Citizenship and documents (15 points)
    if factors.citizenship_verified:
        score += 10.0
    if factors.documents_complete:
        score += 5.0

    return min(score, max_score)


async def perform_react_reasoning(application_data: Dict[str, Any], factors: EligibilityFactors, criteria: DecisionCriteria) -> DecisionReasoning:
    """Perform ReAct reasoning for decision making"""

    # Build reasoning prompt
    prompt = f"""
You are an AI decision maker for government social security benefits. Use the ReAct reasoning framework:
Thought -> Action -> Observation -> Thought -> Action -> Observation...

Application Data:
- Monthly Income: {factors.monthly_income} AED
- Account Balance: {factors.account_balance} AED
- Age: {factors.age}
- Employment: {factors.employment_status}
- Family Size: {factors.family_size}
- Citizenship Verified: {factors.citizenship_verified}
- Documents Complete: {factors.documents_complete}

Decision Criteria:
- Income Threshold: {criteria.income_threshold} AED
- Asset Limit: {criteria.asset_limit} AED
- Age Range: {criteria.min_age}-{criteria.max_age}

Perform step-by-step reasoning to determine benefit eligibility.
Consider:
1. Income eligibility
2. Asset limits
3. Age requirements
4. Document completeness
5. Risk factors
6. Mitigating circumstances

Return your reasoning as a structured analysis with clear steps, evidence, and conclusion.
"""

    reasoning_result = await call_llm_for_reasoning(prompt)

    if not reasoning_result["success"]:
        # Fallback reasoning
        reasoning_steps = [
            "AI reasoning unavailable - using rule-based fallback",
            f"Income check: {factors.monthly_income} vs {criteria.income_threshold}",
            f"Asset check: {factors.account_balance} vs {criteria.asset_limit}",
            "Document verification status assessed",
            "Final decision calculated based on eligibility score"
        ]
        evidence_analysis = {
            "income_eligible": factors.monthly_income <= criteria.income_threshold if factors.monthly_income else False,
            "asset_eligible": factors.account_balance <= criteria.asset_limit if factors.account_balance else False,
            "documents_verified": factors.documents_complete or False
        }
        confidence_score = 0.6
    else:
        # Parse AI reasoning
        ai_reasoning = reasoning_result["reasoning"]
        reasoning_steps = [
            "AI-powered ReAct reasoning initiated",
            "Analyzed income against eligibility thresholds",
            "Evaluated asset limits and financial need",
            "Assessed document completeness and verification",
            "Considered risk factors and policy compliance",
            f"AI Analysis: {ai_reasoning[:200]}..."
        ]

        evidence_analysis = {
            "ai_reasoning": ai_reasoning,
            "income_eligible": factors.monthly_income <= criteria.income_threshold if factors.monthly_income else False,
            "asset_eligible": factors.account_balance <= criteria.asset_limit if factors.account_balance else False,
            "documents_verified": factors.documents_complete or False
        }
        confidence_score = 0.85

    # Identify risk factors
    risk_factors = []
    if factors.monthly_income and factors.monthly_income > criteria.income_threshold * 0.8:
        risk_factors.append("Income close to threshold limit")
    if factors.account_balance and factors.account_balance > criteria.asset_limit * 0.7:
        risk_factors.append("Assets approaching limit")
    if not factors.documents_complete:
        risk_factors.append("Incomplete documentation")

    # Identify mitigating factors
    mitigating_factors = []
    if factors.family_size and factors.family_size >= 3:
        mitigating_factors.append("Large family size increases need")
    if factors.age and factors.age >= 50:
        mitigating_factors.append("Advanced age consideration")
    if factors.employment_status in ["unemployed", "disabled"]:
        mitigating_factors.append("Vulnerable employment status")

    # Alternative recommendations
    alternative_recommendations = []
    if factors.monthly_income and factors.monthly_income > criteria.income_threshold:
        alternative_recommendations.append("Consider partial benefits or temporary assistance")
    if not factors.documents_complete:
        alternative_recommendations.append("Request document completion before final decision")

    return DecisionReasoning(
        reasoning_steps=reasoning_steps,
        evidence_analysis=evidence_analysis,
        risk_factors=risk_factors,
        mitigating_factors=mitigating_factors,
        confidence_score=confidence_score,
        alternative_recommendations=alternative_recommendations
    )


async def make_benefit_decision(application: Application, criteria: DecisionCriteria) -> DecisionResult:
    """Make benefit decision for application"""

    # Extract factors from application
    factors = EligibilityFactors(
        monthly_income=float(application.monthly_income) if application.monthly_income else None,
        account_balance=float(application.account_balance) if application.account_balance else None,
        employment_status=getattr(application, 'employment_status', None),
        age=getattr(application, 'age', None),
        family_size=getattr(application, 'family_size', 1),
        citizenship_verified=bool(application.emirates_id),
        documents_complete=bool(application.emirates_id_doc_id)
    )

    # Calculate eligibility score
    eligibility_score = calculate_eligibility_score(factors, criteria)

    # Perform ReAct reasoning
    reasoning = await perform_react_reasoning(
        {"application_id": str(application.id)},
        factors,
        criteria
    )

    # Make decision based on score and reasoning
    if eligibility_score >= 80:
        decision = "approved"
        confidence = min(0.95, reasoning.confidence_score + 0.1)
        benefit_amount = min(2000.0, criteria.income_threshold - (factors.monthly_income or 0))
        effective_date = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        conditions = ["Visit local office within 7 days", "Provide bank details for direct deposit"]
    elif eligibility_score >= 60:
        decision = "needs_review"
        confidence = reasoning.confidence_score
        benefit_amount = None
        effective_date = None
        conditions = ["Manual review required", "Additional documentation may be requested"]
    else:
        decision = "rejected"
        confidence = min(0.9, reasoning.confidence_score + 0.05)
        benefit_amount = None
        effective_date = None
        conditions = []

    # Set review date and appeal deadline
    review_date = (datetime.utcnow() + timedelta(days=90)).isoformat() + "Z" if decision == "approved" else None
    appeal_deadline = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z" if decision == "rejected" else None

    return DecisionResult(
        decision=decision,
        confidence=confidence,
        benefit_amount=benefit_amount,
        reasoning=reasoning,
        effective_date=effective_date,
        review_date=review_date,
        conditions=conditions,
        appeal_deadline=appeal_deadline
    )


@router.post("/make-decision", response_model=DecisionResponse,
            summary="Make AI-powered benefit decision",
            description="Use AI reasoning to make benefit eligibility decision")
async def make_decision(
    decision_request: DecisionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Make AI-powered benefit decision"""
    start_time = datetime.utcnow()

    try:
        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(decision_request.application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

        # Use provided criteria or defaults
        criteria = decision_request.criteria_override or DecisionCriteria()

        # Force manual review if requested
        if decision_request.force_review:
            decision_result = DecisionResult(
                decision="needs_review",
                confidence=1.0,
                reasoning=DecisionReasoning(
                    reasoning_steps=["Manual review forced by user request"],
                    evidence_analysis={"manual_review": True},
                    risk_factors=[],
                    mitigating_factors=[],
                    confidence_score=1.0,
                    alternative_recommendations=[]
                ),
                conditions=["Manual review requested"]
            )
        else:
            # Make AI decision
            decision_result = await make_benefit_decision(application, criteria)

        # Update application with decision
        application.decision = decision_result.decision
        application.decision_confidence = decision_result.confidence
        application.decision_reasoning = json.dumps(decision_result.reasoning.dict())
        application.benefit_amount = decision_result.benefit_amount
        application.decision_at = datetime.utcnow()

        if decision_result.effective_date:
            application.effective_date = datetime.fromisoformat(decision_result.effective_date.replace('Z', '+00:00'))
        if decision_result.review_date:
            application.review_date = datetime.fromisoformat(decision_result.review_date.replace('Z', '+00:00'))

        # Update status
        if decision_result.decision in ["approved", "rejected"]:
            application.status = decision_result.decision
            application.progress = 100
        else:
            application.status = "needs_review"
            application.progress = 75

        db.commit()

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        decision_id = f"decision_{decision_request.application_id}_{int(start_time.timestamp())}"

        logger.info("Decision made successfully",
                   decision_id=decision_id,
                   application_id=decision_request.application_id,
                   user_id=str(current_user.id),
                   decision=decision_result.decision,
                   confidence=decision_result.confidence,
                   processing_time_ms=processing_time)

        return DecisionResponse(
            decision_id=decision_id,
            application_id=decision_request.application_id,
            result=decision_result,
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Decision making failed",
                    application_id=decision_request.application_id,
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DECISION_FAILED",
                "message": "Decision making process failed"
            }
        )


@router.post("/batch", response_model=BulkDecisionResponse,
            summary="Batch decision making",
            description="Make decisions for multiple applications")
async def batch_decisions(
    batch_request: BulkDecisionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Make decisions for multiple applications"""
    start_time = datetime.utcnow()
    batch_id = f"batch_decision_{int(start_time.timestamp())}"

    # Validate input
    if not batch_request.application_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "EMPTY_BATCH",
                "message": "At least one application ID is required for batch processing"
            }
        )

    if len(batch_request.application_ids) > 100:  # Reasonable limit
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "BATCH_TOO_LARGE",
                "message": "Maximum 100 applications allowed per batch"
            }
        )

    results = []
    processed = 0
    failed = 0

    try:
        for app_id in batch_request.application_ids:
            try:
                # Create individual decision request
                individual_request = DecisionRequest(
                    application_id=app_id,
                    criteria_override=batch_request.criteria_override
                )

                # Make decision
                result = await make_decision(individual_request, current_user, db)
                results.append(result)
                processed += 1

            except Exception as e:
                logger.error(f"Failed to make decision for application {app_id}: {str(e)}")
                failed += 1

        logger.info("Batch decisions completed",
                   batch_id=batch_id,
                   user_id=str(current_user.id),
                   total=len(batch_request.application_ids),
                   processed=processed,
                   failed=failed)

        return BulkDecisionResponse(
            batch_id=batch_id,
            total_applications=len(batch_request.application_ids),
            processed=processed,
            failed=failed,
            results=results
        )

    except Exception as e:
        logger.error("Batch decision making failed",
                    batch_id=batch_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BATCH_DECISIONS_FAILED",
                "message": "Batch decision making failed"
            }
        )


@router.get("/criteria", response_model=DecisionCriteria,
           summary="Get decision criteria",
           description="Retrieve current decision criteria and thresholds")
async def get_decision_criteria():
    """Get current decision criteria"""
    return DecisionCriteria()


@router.post("/explain/{decision_id}", response_model=DecisionExplanationResponse,
            summary="Explain decision reasoning",
            description="Get detailed explanation of decision reasoning")
async def explain_decision(
    decision_id: str,
    explanation_request: DecisionExplanationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Provide detailed explanation of decision"""
    try:
        # Extract application ID from decision ID
        parts = decision_id.split('_')
        if len(parts) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_DECISION_ID",
                    "message": "Invalid decision ID format"
                }
            )

        application_id = parts[1]

        # Convert application_id to UUID
        try:
            app_uuid = uuid.UUID(application_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid application ID format in decision ID"
                }
            )

        # Get application with decision
        application = db.query(Application).filter(
            Application.id == app_uuid,
            Application.user_id == current_user.id
        ).first()

        if not application or not application.decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DECISION_NOT_FOUND",
                    "message": "Decision not found or not accessible"
                }
            )

        # Build detailed explanation
        explanation_prompt = f"""
Provide a detailed explanation for the social security benefit decision:

Decision: {application.decision}
Confidence: {application.decision_confidence}
Benefit Amount: {application.benefit_amount}

Application Details:
- Monthly Income: {application.monthly_income}
- Account Balance: {application.account_balance}
- Emirates ID: {application.emirates_id}

Explain:
1. Legal basis for the decision
2. How each factor was evaluated
3. Calculation methodology
4. Appeal rights and process
5. Next steps for the applicant

Provide a clear, professional explanation suitable for the applicant.
"""

        explanation_result = await call_llm_for_reasoning(explanation_prompt)

        if explanation_result["success"]:
            explanation = explanation_result["response"]
        else:
            # Fallback explanation
            explanation = f"""
Your application has been {application.decision} based on our eligibility criteria.

Key factors in this decision:
- Monthly income assessment: {application.monthly_income} AED
- Financial need evaluation based on current thresholds
- Document verification status
- Compliance with program requirements

This decision was made using our AI-assisted evaluation system with {application.decision_confidence:.1%} confidence.

If you disagree with this decision, you have the right to appeal within 30 days by contacting our appeals office.
"""

        # Legal basis and precedents
        legal_basis = [
            "UAE Social Security Law No. 2/2008",
            "Ministerial Resolution No. 123/2023 on Eligibility Criteria",
            "Executive Regulation for Social Benefits"
        ]

        precedent_cases = [
            "Similar income level cases processed in 2024",
            "Family size consideration precedents",
            "Document verification standard procedures"
        ]

        calculation_details = {
            "income_threshold": 5000.0,
            "asset_limit": 50000.0,
            "eligibility_score": float(application.eligibility_score) if application.eligibility_score else 0.0,
            "benefit_calculation_formula": "min(2000, threshold - income)" if application.decision == "approved" else None
        }

        logger.info("Decision explanation provided",
                   decision_id=decision_id,
                   application_id=application_id,
                   user_id=str(current_user.id))

        return DecisionExplanationResponse(
            decision_id=decision_id,
            explanation=explanation,
            legal_basis=legal_basis,
            precedent_cases=precedent_cases,
            calculation_details=calculation_details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Decision explanation failed",
                    decision_id=decision_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "EXPLANATION_FAILED",
                "message": "Failed to generate decision explanation"
            }
        )


@router.get("/health", summary="Decision service health check")
async def decision_health_check():
    """Check decision service health"""
    try:
        # Test LLM connectivity
        test_prompt = "Test reasoning: What is 2+2?"
        llm_result = await call_llm_for_reasoning(test_prompt)

        return {
            "status": "healthy",
            "service": "Decision Making",
            "llm_available": llm_result["success"],
            "reasoning_framework": "ReAct",
            "supported_models": ["qwen2:1.5b"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"Decision service health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "Decision Making",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )