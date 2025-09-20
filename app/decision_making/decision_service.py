"""
Decision making business logic service
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from decimal import Decimal
import json

from app.decision_making.decision_models import Decision, DecisionAuditLog
from app.decision_making.decision_schemas import (
    DecisionResponse, EligibilityFactors, DecisionReasoning
)
from app.decision_making.react_reasoning import ReActDecisionEngine
from app.shared.exceptions import (
    AIServiceError, ApplicationNotFoundError, ValidationError
)
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class DecisionService:
    """Service for making and managing eligibility decisions"""

    def __init__(self):
        self.react_engine = ReActDecisionEngine()

    def make_eligibility_decision(self, db: Session, application_id: str,
                                applicant_data: Dict[str, Any],
                                extracted_data: Dict[str, Any]) -> Decision:
        """Make eligibility decision for an application"""
        try:
            logger.info("Starting eligibility decision process", application_id=application_id)

            # Check if decision already exists
            existing_decision = db.query(Decision).filter(
                Decision.application_id == application_id
            ).first()

            if existing_decision:
                logger.info("Decision already exists", application_id=application_id)
                return existing_decision

            start_time = time.time()

            # Prepare data for decision engine
            decision_data = {
                "application_id": application_id,
                "applicant_data": applicant_data,
                "extracted_data": extracted_data
            }

            # Use ReAct reasoning engine to make decision
            decision_result, reasoning_trace = self.react_engine.make_eligibility_decision(decision_data)

            processing_time = int((time.time() - start_time) * 1000)

            # Create decision record
            decision = Decision(
                application_id=application_id,
                outcome=decision_result["outcome"],
                confidence_score=Decimal(str(decision_result["confidence"])),
                benefit_amount=Decimal(str(decision_result.get("benefit_amount", 0))),
                currency=decision_result.get("currency", "AED"),
                frequency=decision_result.get("frequency", "monthly"),
                reasoning=decision_result.get("reasoning", {}),
                eligibility_factors=self._extract_eligibility_factors(decision_data, decision_result),
                risk_assessment=self._extract_risk_assessment(decision_result),
                model_name="react_reasoning_engine",
                model_version="1.0",
                processing_time_ms=processing_time,
                requires_human_review=decision_result["outcome"] == "needs_review"
            )

            # Set dates based on decision
            if decision.outcome == "approved":
                decision.effective_date = datetime.now() + timedelta(days=7)  # 7 days to process
                decision.review_date = datetime.now() + timedelta(days=180)  # 6 month review
            elif decision.outcome == "needs_review":
                decision.review_date = datetime.now() + timedelta(days=14)  # 2 week review
                decision.review_priority = "normal"

            # Save decision
            db.add(decision)
            db.commit()
            db.refresh(decision)

            # Log decision audit
            self._create_audit_log(
                db, decision.id, application_id, "decision_made", "ai_system",
                previous_value=None,
                new_value={
                    "outcome": decision.outcome,
                    "confidence": float(decision.confidence_score),
                    "benefit_amount": float(decision.benefit_amount) if decision.benefit_amount else 0
                },
                system_context={
                    "model_name": decision.model_name,
                    "processing_time_ms": processing_time,
                    "reasoning_steps": len(reasoning_trace.reasoning_steps)
                }
            )

            logger.info(
                "Eligibility decision completed",
                application_id=application_id,
                decision_id=str(decision.id),
                outcome=decision.outcome,
                confidence=float(decision.confidence_score),
                processing_time_ms=processing_time
            )

            return decision

        except Exception as e:
            logger.error("Failed to make eligibility decision", error=str(e), application_id=application_id)
            db.rollback()
            # Create a fallback decision
            return self._create_fallback_decision(db, application_id, str(e))

    def get_decision_by_application(self, db: Session, application_id: str) -> Optional[Decision]:
        """Get decision for an application"""
        return db.query(Decision).filter(Decision.application_id == application_id).first()

    def get_decision_by_id(self, db: Session, decision_id: str) -> Decision:
        """Get decision by ID"""
        decision = db.query(Decision).filter(Decision.id == decision_id).first()
        if not decision:
            raise ApplicationNotFoundError(f"Decision with ID {decision_id} not found", "DECISION_NOT_FOUND")
        return decision

    def override_decision(self, db: Session, decision_id: str, new_outcome: str,
                         override_reason: str, reviewer_id: str,
                         reviewer_notes: Optional[str] = None) -> Decision:
        """Override an existing decision"""
        try:
            decision = self.get_decision_by_id(db, decision_id)

            if decision.outcome == new_outcome:
                raise ValidationError("New outcome is the same as current outcome", "SAME_OUTCOME")

            previous_outcome = decision.outcome
            previous_confidence = float(decision.confidence_score)
            previous_benefit = float(decision.benefit_amount) if decision.benefit_amount else 0

            # Update decision
            decision.outcome = new_outcome
            decision.confidence_score = Decimal("0.95")  # High confidence for manual override
            decision.requires_human_review = False
            decision.reviewed_at = datetime.utcnow()

            # Update benefit amount based on new outcome
            if new_outcome == "approved":
                decision.benefit_amount = Decimal("2500")  # Standard benefit
                decision.effective_date = datetime.now() + timedelta(days=3)  # Faster processing
                decision.review_date = datetime.now() + timedelta(days=180)
            elif new_outcome == "rejected":
                decision.benefit_amount = Decimal("0")
                decision.effective_date = None
                decision.review_date = None
            else:  # needs_review
                decision.benefit_amount = Decimal("0")
                decision.effective_date = None
                decision.review_date = datetime.now() + timedelta(days=7)

            # Add override reasoning
            override_reasoning = {
                "override_reason": override_reason,
                "reviewer_notes": reviewer_notes,
                "override_timestamp": datetime.utcnow().isoformat(),
                "previous_outcome": previous_outcome,
                "original_reasoning": decision.reasoning
            }
            decision.reasoning.update(override_reasoning)

            db.commit()
            db.refresh(decision)

            # Create audit log
            self._create_audit_log(
                db, decision_id, decision.application_id, "decision_overridden", "human_reviewer",
                actor_id=reviewer_id,
                previous_value={
                    "outcome": previous_outcome,
                    "confidence": previous_confidence,
                    "benefit_amount": previous_benefit
                },
                new_value={
                    "outcome": decision.outcome,
                    "confidence": float(decision.confidence_score),
                    "benefit_amount": float(decision.benefit_amount) if decision.benefit_amount else 0
                },
                change_reason=override_reason
            )

            logger.info(
                "Decision overridden",
                decision_id=decision_id,
                previous_outcome=previous_outcome,
                new_outcome=new_outcome,
                reviewer_id=reviewer_id
            )

            return decision

        except Exception as e:
            db.rollback()
            logger.error("Failed to override decision", error=str(e), decision_id=decision_id)
            raise

    def get_decisions_for_review(self, db: Session, limit: int = 50) -> list[Decision]:
        """Get decisions that require human review"""
        return db.query(Decision).filter(
            Decision.requires_human_review == True
        ).order_by(Decision.created_at.desc()).limit(limit).all()

    def get_decision_statistics(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get decision statistics for the last N days"""
        try:
            from sqlalchemy import func

            cutoff_date = datetime.now() - timedelta(days=days)

            # Basic counts
            total_decisions = db.query(Decision).filter(
                Decision.created_at >= cutoff_date
            ).count()

            approved = db.query(Decision).filter(
                Decision.created_at >= cutoff_date,
                Decision.outcome == "approved"
            ).count()

            rejected = db.query(Decision).filter(
                Decision.created_at >= cutoff_date,
                Decision.outcome == "rejected"
            ).count()

            needs_review = db.query(Decision).filter(
                Decision.created_at >= cutoff_date,
                Decision.outcome == "needs_review"
            ).count()

            # Calculate rates
            approval_rate = (approved / total_decisions * 100) if total_decisions > 0 else 0
            review_rate = (needs_review / total_decisions * 100) if total_decisions > 0 else 0

            # Average confidence
            avg_confidence_result = db.query(func.avg(Decision.confidence_score)).filter(
                Decision.created_at >= cutoff_date
            ).scalar()
            avg_confidence = float(avg_confidence_result) if avg_confidence_result else 0

            # Average processing time
            avg_processing_time = db.query(func.avg(Decision.processing_time_ms)).filter(
                Decision.created_at >= cutoff_date,
                Decision.processing_time_ms.isnot(None)
            ).scalar()

            return {
                "period_days": days,
                "total_decisions": total_decisions,
                "approved": approved,
                "rejected": rejected,
                "needs_review": needs_review,
                "approval_rate": round(approval_rate, 1),
                "review_rate": round(review_rate, 1),
                "average_confidence": round(avg_confidence, 3),
                "average_processing_time_ms": int(avg_processing_time) if avg_processing_time else 0,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error("Failed to get decision statistics", error=str(e))
            return {"error": str(e)}

    def _extract_eligibility_factors(self, decision_data: Dict[str, Any],
                                   decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract eligibility factors from decision data"""
        extracted_data = decision_data.get("extracted_data", {})
        bank_data = extracted_data.get("bank_statement", {})

        return {
            "monthly_income": float(bank_data.get("monthly_income", 0)),
            "account_balance": float(bank_data.get("account_balance", 0)),
            "document_confidence": float(bank_data.get("confidence", 0)),
            "eligibility_score": decision_result.get("eligibility_score", 0),
            "income_threshold_met": decision_result.get("reasoning", {}).get("eligibility_factors", {}).get("income_eligible", False),
            "documents_verified": decision_result.get("reasoning", {}).get("eligibility_factors", {}).get("documents_verified", False)
        }

    def _extract_risk_assessment(self, decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract risk assessment from decision result"""
        return {
            "risk_level": decision_result.get("risk_level", "unknown"),
            "risk_score": decision_result.get("risk_score", 0.5),
            "automated_decision": True,
            "requires_review": decision_result.get("outcome") == "needs_review"
        }

    def _create_audit_log(self, db: Session, decision_id: str, application_id: str,
                         action: str, actor_type: str, actor_id: Optional[str] = None,
                         previous_value: Optional[Dict[str, Any]] = None,
                         new_value: Optional[Dict[str, Any]] = None,
                         change_reason: Optional[str] = None,
                         system_context: Optional[Dict[str, Any]] = None) -> DecisionAuditLog:
        """Create an audit log entry"""
        try:
            audit_log = DecisionAuditLog(
                decision_id=decision_id,
                application_id=application_id,
                action=action,
                actor_type=actor_type,
                actor_id=actor_id,
                previous_value=previous_value,
                new_value=new_value,
                change_reason=change_reason,
                system_context=system_context or {}
            )

            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)

            return audit_log

        except Exception as e:
            logger.error("Failed to create audit log", error=str(e))
            db.rollback()
            raise

    def _create_fallback_decision(self, db: Session, application_id: str, error_message: str) -> Decision:
        """Create a fallback decision when main processing fails"""
        try:
            decision = Decision(
                application_id=application_id,
                outcome="needs_review",
                confidence_score=Decimal("0.3"),
                benefit_amount=Decimal("0"),
                currency="AED",
                frequency="monthly",
                reasoning={
                    "error": error_message,
                    "fallback": True,
                    "summary": "Automatic processing failed - manual review required"
                },
                eligibility_factors={"fallback": True},
                risk_assessment={"fallback": True, "requires_review": True},
                model_name="fallback_decision",
                model_version="1.0",
                processing_time_ms=0,
                requires_human_review=True,
                review_priority="high"
            )

            decision.review_date = datetime.now() + timedelta(days=1)  # Urgent review

            db.add(decision)
            db.commit()
            db.refresh(decision)

            logger.warning(
                "Created fallback decision due to processing failure",
                application_id=application_id,
                decision_id=str(decision.id),
                error=error_message
            )

            return decision

        except Exception as e:
            logger.error("Failed to create fallback decision", error=str(e))
            db.rollback()
            raise