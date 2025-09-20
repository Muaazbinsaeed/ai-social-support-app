"""
Decision making database models
"""

from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Text, Numeric, Boolean, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from app.shared.database import Base


class Decision(Base):
    """Decision model for storing AI decision results"""

    __tablename__ = "decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)

    # Decision outcome
    outcome = Column(String(20), nullable=False)  # 'approved', 'rejected', 'needs_review'
    confidence_score = Column(Numeric(3, 2), nullable=False)

    # Financial details
    benefit_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="AED")
    frequency = Column(String(20), default="monthly")

    # Timeline
    effective_date = Column(DateTime(timezone=True), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)

    # Decision reasoning (structured)
    reasoning = Column(JSONB, nullable=True)
    eligibility_factors = Column(JSONB, nullable=True)
    risk_assessment = Column(JSONB, nullable=True)

    # AI Model information
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Review flags
    requires_human_review = Column(Boolean, default=False)
    review_priority = Column(String(20), default="normal")  # 'low', 'normal', 'high', 'urgent'

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("Application")

    def __repr__(self):
        return f"<Decision(application_id='{self.application_id}', outcome='{self.outcome}', confidence={self.confidence_score})>"


class DecisionAuditLog(Base):
    """Audit log for decision-making process"""

    __tablename__ = "decision_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)

    # Audit information
    action = Column(String(100), nullable=False)  # 'decision_made', 'review_requested', 'decision_overridden'
    actor_type = Column(String(50), nullable=False)  # 'ai_system', 'human_reviewer', 'admin'
    actor_id = Column(UUID(as_uuid=True), nullable=True)  # User ID if human actor

    # Change details
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    change_reason = Column(Text, nullable=True)

    # Context
    system_context = Column(JSONB, nullable=True)  # System state, model versions, etc.
    user_context = Column(JSONB, nullable=True)    # User session, IP, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    decision = relationship("Decision")
    application = relationship("Application")

    def __repr__(self):
        return f"<DecisionAuditLog(decision_id='{self.decision_id}', action='{self.action}', actor_type='{self.actor_type}')>"