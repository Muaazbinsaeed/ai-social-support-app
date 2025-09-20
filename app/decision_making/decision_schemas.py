"""
Pydantic schemas for decision making
"""

from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class EligibilityRequest(BaseModel):
    """Schema for eligibility evaluation request"""
    application_id: str
    applicant_data: Dict[str, Any]
    extracted_data: Dict[str, Any]
    force_decision: bool = False


class DecisionResponse(BaseModel):
    """Schema for decision response"""
    decision_id: str
    application_id: str
    outcome: str  # 'approved', 'rejected', 'needs_review'
    confidence_score: Decimal
    benefit_amount: Optional[Decimal]
    currency: str = "AED"
    frequency: str = "monthly"
    effective_date: Optional[datetime]
    review_date: Optional[datetime]
    reasoning: Dict[str, Any]
    next_steps: List[str]
    appeal_deadline: Optional[datetime]

    class Config:
        from_attributes = True


class DecisionReasoning(BaseModel):
    """Schema for decision reasoning details"""
    income_analysis: str
    document_verification: str
    eligibility_factors: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    confidence_breakdown: Dict[str, float]


class EligibilityFactors(BaseModel):
    """Schema for eligibility evaluation factors"""
    monthly_income: Optional[Decimal]
    income_threshold_met: bool
    account_balance: Optional[Decimal]
    balance_threshold_met: bool
    identity_verified: bool
    document_quality_score: float
    overall_score: float

    @field_validator('overall_score')
    @classmethod
    def validate_score_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Overall score must be between 0 and 1')
        return v


class DecisionAudit(BaseModel):
    """Schema for decision audit information"""
    decision_id: str
    action: str
    actor_type: str
    previous_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    change_reason: Optional[str]
    system_context: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionOverride(BaseModel):
    """Schema for manual decision override"""
    new_outcome: str
    override_reason: str
    reviewer_notes: Optional[str]

    @field_validator('new_outcome')
    @classmethod
    def validate_outcome(cls, v):
        allowed_outcomes = ['approved', 'rejected', 'needs_review']
        if v not in allowed_outcomes:
            raise ValueError(f'Outcome must be one of: {", ".join(allowed_outcomes)}')
        return v


class DecisionSummary(BaseModel):
    """Schema for decision summary statistics"""
    total_decisions: int
    approved: int
    rejected: int
    needs_review: int
    approval_rate: float
    average_confidence: float
    processing_time_stats: Dict[str, float]


class ReasoningStep(BaseModel):
    """Schema for individual reasoning steps in ReAct framework"""
    step_type: str  # 'thought', 'action', 'observation'
    content: str
    confidence: Optional[float]
    timestamp: datetime
    data_used: Optional[Dict[str, Any]]


class ReActDecisionTrace(BaseModel):
    """Schema for complete ReAct reasoning trace"""
    application_id: str
    reasoning_steps: List[ReasoningStep]
    final_decision: str
    confidence_score: float
    total_steps: int
    processing_time_ms: int
    model_used: str