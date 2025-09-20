"""
ReAct (Reasoning and Acting) framework for eligibility decision making
"""

import time
from typing import Dict, Any, List, Tuple
from datetime import datetime
from decimal import Decimal

from app.config import settings
from app.shared.llm_client import OllamaClient
from app.decision_making.decision_schemas import ReasoningStep, ReActDecisionTrace
from app.shared.exceptions import AIServiceError
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class ReActDecisionEngine:
    """ReAct framework for structured eligibility reasoning"""

    def __init__(self):
        self.llm_client = OllamaClient()
        self.max_reasoning_steps = 10
        self.confidence_threshold = settings.confidence_threshold

    def make_eligibility_decision(self, application_data: Dict[str, Any]) -> Tuple[Dict[str, Any], ReActDecisionTrace]:
        """
        Make eligibility decision using ReAct reasoning framework
        Returns: (decision_result, reasoning_trace)
        """
        start_time = time.time()
        reasoning_steps = []

        try:
            logger.info("Starting ReAct decision process", application_id=application_data.get("application_id"))

            # Step 1: Initial Thought - Analyze the situation
            thought_step = self._create_thought_step(
                "I need to evaluate this social security application based on UAE eligibility criteria. "
                "Let me analyze the applicant's income, financial situation, and document verification status.",
                application_data
            )
            reasoning_steps.append(thought_step)

            # Step 2: Action - Extract and validate key financial data
            financial_data = self._extract_financial_data(application_data)
            action_step = self._create_action_step(
                "Extracting financial data from documents",
                financial_data
            )
            reasoning_steps.append(action_step)

            # Step 3: Observation - Analyze financial eligibility
            income_analysis = self._analyze_income_eligibility(financial_data)
            observation_step = self._create_observation_step(
                f"Income analysis: Monthly income is {financial_data.get('monthly_income', 0)} AED. "
                f"Threshold is {settings.income_threshold_aed} AED. "
                f"Meets income criteria: {income_analysis['meets_income_criteria']}",
                income_analysis
            )
            reasoning_steps.append(observation_step)

            # Step 4: Thought - Consider document verification
            doc_verification = self._analyze_document_verification(application_data)
            thought_step = self._create_thought_step(
                f"Document verification shows: Identity verified: {doc_verification['identity_verified']}, "
                f"Financial docs quality: {doc_verification['financial_docs_quality']:.2f}",
                doc_verification
            )
            reasoning_steps.append(thought_step)

            # Step 5: Action - Calculate overall eligibility score
            eligibility_score = self._calculate_eligibility_score(income_analysis, doc_verification, financial_data)
            action_step = self._create_action_step(
                f"Calculating eligibility score based on all factors",
                eligibility_score
            )
            reasoning_steps.append(action_step)

            # Step 6: Observation - Risk assessment
            risk_assessment = self._assess_risk_factors(application_data, financial_data)
            observation_step = self._create_observation_step(
                f"Risk assessment completed. Risk level: {risk_assessment['risk_level']}, "
                f"flags: {len(risk_assessment['risk_flags'])}",
                risk_assessment
            )
            reasoning_steps.append(observation_step)

            # Step 7: Final Thought - Make decision
            final_decision = self._make_final_decision(
                eligibility_score, risk_assessment, income_analysis, doc_verification
            )
            thought_step = self._create_thought_step(
                f"Based on eligibility score of {eligibility_score['overall_score']:.3f} and risk assessment, "
                f"my decision is: {final_decision['outcome']}",
                final_decision
            )
            reasoning_steps.append(thought_step)

            processing_time = int((time.time() - start_time) * 1000)

            # Create reasoning trace
            trace = ReActDecisionTrace(
                application_id=application_data.get("application_id", "unknown"),
                reasoning_steps=reasoning_steps,
                final_decision=final_decision['outcome'],
                confidence_score=final_decision['confidence'],
                total_steps=len(reasoning_steps),
                processing_time_ms=processing_time,
                model_used="react_reasoning_engine"
            )

            logger.info(
                "ReAct decision process completed",
                application_id=application_data.get("application_id"),
                decision=final_decision['outcome'],
                confidence=final_decision['confidence'],
                steps=len(reasoning_steps)
            )

            return final_decision, trace

        except Exception as e:
            logger.error("ReAct decision process failed", error=str(e))
            # Return fallback decision
            fallback_decision = self._get_fallback_decision(application_data)
            processing_time = int((time.time() - start_time) * 1000)

            trace = ReActDecisionTrace(
                application_id=application_data.get("application_id", "unknown"),
                reasoning_steps=reasoning_steps,
                final_decision=fallback_decision['outcome'],
                confidence_score=fallback_decision['confidence'],
                total_steps=len(reasoning_steps),
                processing_time_ms=processing_time,
                model_used="fallback_reasoning"
            )

            return fallback_decision, trace

    def _create_thought_step(self, content: str, data_used: Dict[str, Any]) -> ReasoningStep:
        """Create a thought reasoning step"""
        return ReasoningStep(
            step_type="thought",
            content=content,
            timestamp=datetime.utcnow(),
            data_used=data_used
        )

    def _create_action_step(self, content: str, data_used: Dict[str, Any]) -> ReasoningStep:
        """Create an action reasoning step"""
        return ReasoningStep(
            step_type="action",
            content=content,
            timestamp=datetime.utcnow(),
            data_used=data_used
        )

    def _create_observation_step(self, content: str, data_used: Dict[str, Any]) -> ReasoningStep:
        """Create an observation reasoning step"""
        return ReasoningStep(
            step_type="observation",
            content=content,
            timestamp=datetime.utcnow(),
            data_used=data_used
        )

    def _extract_financial_data(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize financial data from application"""
        extracted_data = application_data.get("extracted_data", {})
        bank_data = extracted_data.get("bank_statement", {})

        return {
            "monthly_income": float(bank_data.get("monthly_income", 0)),
            "account_balance": float(bank_data.get("account_balance", 0)),
            "account_number": bank_data.get("account_number", ""),
            "bank_name": bank_data.get("bank_name", ""),
            "statement_period": bank_data.get("statement_period", ""),
            "data_confidence": float(bank_data.get("confidence", 0.5))
        }

    def _analyze_income_eligibility(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze income against eligibility thresholds"""
        monthly_income = financial_data.get("monthly_income", 0)
        income_threshold = settings.income_threshold_aed

        meets_criteria = monthly_income < income_threshold
        income_ratio = monthly_income / income_threshold if income_threshold > 0 else 1.0

        return {
            "monthly_income": monthly_income,
            "income_threshold": income_threshold,
            "meets_income_criteria": meets_criteria,
            "income_ratio": income_ratio,
            "income_gap": income_threshold - monthly_income if meets_criteria else 0,
            "confidence": financial_data.get("data_confidence", 0.5)
        }

    def _analyze_document_verification(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document verification status"""
        extracted_data = application_data.get("extracted_data", {})
        emirates_id_data = extracted_data.get("emirates_id", {})
        bank_data = extracted_data.get("bank_statement", {})

        # Check identity verification
        identity_verified = bool(
            emirates_id_data.get("id_number") and
            emirates_id_data.get("full_name") and
            float(emirates_id_data.get("confidence", 0)) > 0.6
        )

        # Check financial document quality
        financial_docs_quality = float(bank_data.get("confidence", 0))

        # Check name consistency
        emirate_name = emirates_id_data.get("full_name", "").lower()
        bank_name = bank_data.get("account_holder", "").lower()
        name_consistency = emirate_name in bank_name or bank_name in emirate_name

        return {
            "identity_verified": identity_verified,
            "financial_docs_quality": financial_docs_quality,
            "name_consistency": name_consistency,
            "emirates_id_confidence": float(emirates_id_data.get("confidence", 0)),
            "bank_statement_confidence": financial_docs_quality,
            "overall_verification_score": (
                (1.0 if identity_verified else 0.0) * 0.4 +
                financial_docs_quality * 0.4 +
                (1.0 if name_consistency else 0.0) * 0.2
            )
        }

    def _calculate_eligibility_score(self, income_analysis: Dict[str, Any],
                                   doc_verification: Dict[str, Any],
                                   financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall eligibility score"""
        # Income score (0-1)
        income_score = 1.0 if income_analysis["meets_income_criteria"] else 0.0
        if income_analysis["meets_income_criteria"]:
            # Bonus for being well below threshold
            income_ratio = income_analysis["income_ratio"]
            if income_ratio < 0.5:
                income_score = 1.0
            elif income_ratio < 0.8:
                income_score = 0.9
            else:
                income_score = 0.7

        # Document verification score (0-1)
        doc_score = doc_verification["overall_verification_score"]

        # Financial need score (based on account balance)
        account_balance = financial_data.get("account_balance", 0)
        balance_threshold = settings.balance_threshold_aed
        if account_balance < balance_threshold:
            need_score = 1.0
        elif account_balance < balance_threshold * 2:
            need_score = 0.7
        else:
            need_score = 0.3

        # Weighted overall score
        overall_score = (
            income_score * 0.5 +  # Income is most important
            doc_score * 0.3 +     # Document verification
            need_score * 0.2      # Financial need
        )

        return {
            "income_score": income_score,
            "document_score": doc_score,
            "financial_need_score": need_score,
            "overall_score": overall_score,
            "components": {
                "income_weight": 0.5,
                "document_weight": 0.3,
                "need_weight": 0.2
            }
        }

    def _assess_risk_factors(self, application_data: Dict[str, Any],
                           financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk factors for the application"""
        risk_flags = []
        risk_score = 0.0

        # Low document confidence
        if financial_data.get("data_confidence", 1.0) < 0.6:
            risk_flags.append("low_document_confidence")
            risk_score += 0.3

        # Missing or incomplete data
        required_fields = ["monthly_income", "account_balance"]
        missing_fields = [field for field in required_fields
                         if not financial_data.get(field)]
        if missing_fields:
            risk_flags.append(f"missing_data_{len(missing_fields)}_fields")
            risk_score += 0.2 * len(missing_fields)

        # Unusual financial patterns (simplified)
        monthly_income = financial_data.get("monthly_income", 0)
        account_balance = financial_data.get("account_balance", 0)

        if monthly_income > 0 and account_balance > monthly_income * 10:
            risk_flags.append("high_balance_vs_income")
            risk_score += 0.2

        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 1.0),
            "risk_flags": risk_flags,
            "requires_review": risk_level in ["medium", "high"] or len(risk_flags) >= 2
        }

    def _make_final_decision(self, eligibility_score: Dict[str, Any],
                           risk_assessment: Dict[str, Any],
                           income_analysis: Dict[str, Any],
                           doc_verification: Dict[str, Any]) -> Dict[str, Any]:
        """Make final eligibility decision"""
        overall_score = eligibility_score["overall_score"]
        risk_level = risk_assessment["risk_level"]

        # Determine outcome based on score and risk
        if overall_score >= settings.auto_approval_threshold and risk_level == "low":
            outcome = "approved"
            confidence = min(overall_score, 0.95)
            benefit_amount = 2500  # Full benefit
        elif overall_score >= settings.confidence_threshold and risk_level in ["low", "medium"]:
            if income_analysis["meets_income_criteria"]:
                outcome = "approved"
                confidence = overall_score * 0.9  # Slight reduction for medium risk
                benefit_amount = 2000  # Reduced benefit
            else:
                outcome = "needs_review"
                confidence = overall_score * 0.8
                benefit_amount = 0
        elif overall_score >= 0.4:  # Borderline cases
            outcome = "needs_review"
            confidence = overall_score * 0.7
            benefit_amount = 0
        else:
            outcome = "rejected"
            confidence = 1.0 - overall_score  # High confidence in rejection
            benefit_amount = 0

        # Generate reasoning
        reasoning = self._generate_reasoning(
            outcome, eligibility_score, risk_assessment, income_analysis, doc_verification
        )

        return {
            "outcome": outcome,
            "confidence": confidence,
            "benefit_amount": benefit_amount,
            "currency": "AED",
            "frequency": "monthly",
            "reasoning": reasoning,
            "eligibility_score": overall_score,
            "risk_level": risk_level
        }

    def _generate_reasoning(self, outcome: str, eligibility_score: Dict[str, Any],
                          risk_assessment: Dict[str, Any], income_analysis: Dict[str, Any],
                          doc_verification: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable reasoning for the decision"""
        reasoning = {
            "summary": "",
            "income_analysis": "",
            "document_verification": "",
            "risk_assessment": "",
            "eligibility_factors": {
                "income_eligible": income_analysis["meets_income_criteria"],
                "documents_verified": doc_verification["identity_verified"],
                "overall_score": eligibility_score["overall_score"],
                "risk_level": risk_assessment["risk_level"]
            }
        }

        # Income analysis
        monthly_income = income_analysis["monthly_income"]
        income_threshold = income_analysis["income_threshold"]
        if income_analysis["meets_income_criteria"]:
            reasoning["income_analysis"] = (
                f"Monthly income of AED {monthly_income:,.2f} is below the eligibility threshold "
                f"of AED {income_threshold:,.2f}, qualifying for assistance."
            )
        else:
            reasoning["income_analysis"] = (
                f"Monthly income of AED {monthly_income:,.2f} exceeds the eligibility threshold "
                f"of AED {income_threshold:,.2f}, indicating limited financial need."
            )

        # Document verification
        if doc_verification["identity_verified"]:
            reasoning["document_verification"] = (
                f"Identity verification successful with {doc_verification['overall_verification_score']:.1%} confidence. "
                f"Documents appear authentic and consistent."
            )
        else:
            reasoning["document_verification"] = (
                "Identity verification incomplete or documents show inconsistencies requiring manual review."
            )

        # Risk assessment
        risk_flags = risk_assessment["risk_flags"]
        if risk_assessment["risk_level"] == "low":
            reasoning["risk_assessment"] = "No significant risk factors identified."
        else:
            reasoning["risk_assessment"] = (
                f"Risk level: {risk_assessment['risk_level']}. "
                f"Flags: {', '.join(risk_flags) if risk_flags else 'None'}"
            )

        # Summary based on outcome
        if outcome == "approved":
            reasoning["summary"] = (
                "Application approved based on income eligibility, verified documentation, "
                "and low risk assessment."
            )
        elif outcome == "rejected":
            reasoning["summary"] = (
                "Application rejected due to income exceeding eligibility threshold "
                "or insufficient documentation."
            )
        else:  # needs_review
            reasoning["summary"] = (
                "Application requires manual review due to borderline eligibility "
                "or risk factors requiring human assessment."
            )

        return reasoning

    def _get_fallback_decision(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback decision when reasoning fails"""
        # Simple rule-based fallback
        extracted_data = application_data.get("extracted_data", {})
        bank_data = extracted_data.get("bank_statement", {})
        monthly_income = float(bank_data.get("monthly_income", 0))

        if monthly_income < settings.income_threshold_aed and monthly_income > 0:
            outcome = "approved"
            benefit_amount = 2000
            confidence = 0.6
        elif monthly_income == 0:
            outcome = "needs_review"
            benefit_amount = 0
            confidence = 0.5
        else:
            outcome = "rejected"
            benefit_amount = 0
            confidence = 0.7

        return {
            "outcome": outcome,
            "confidence": confidence,
            "benefit_amount": benefit_amount,
            "currency": "AED",
            "frequency": "monthly",
            "reasoning": {
                "summary": f"Fallback decision based on income of AED {monthly_income:,.2f}",
                "fallback": True
            }
        }