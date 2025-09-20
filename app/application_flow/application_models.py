"""
Application database models
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, UUID, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.shared.database import Base


class Application(Base):
    """Main application model with comprehensive state tracking"""

    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Form data
    full_name = Column(String(255), nullable=False)
    emirates_id = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)

    # State management
    status = Column(String(50), nullable=False, default="draft", index=True)
    progress = Column(Integer, default=0)

    # Document references (denormalized for performance)
    bank_statement_id = Column(UUID(as_uuid=True), nullable=True)
    emirates_id_doc_id = Column(UUID(as_uuid=True), nullable=True)

    # Processing results (denormalized for quick access)
    monthly_income = Column(Numeric(10, 2), nullable=True)
    account_balance = Column(Numeric(10, 2), nullable=True)
    eligibility_score = Column(Numeric(3, 2), nullable=True)

    # Decision results
    decision = Column(String(20), nullable=True)  # 'approved', 'rejected', 'needs_review'
    decision_confidence = Column(Numeric(3, 2), nullable=True)
    decision_reasoning = Column(Text, nullable=True)

    # Additional decision metadata
    benefit_amount = Column(Numeric(10, 2), nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    decision_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    workflow_states = relationship("WorkflowState", back_populates="application", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(id='{self.id}', status='{self.status}', user_id='{self.user_id}')>"


class WorkflowState(Base):
    """Detailed workflow state tracking for applications"""

    __tablename__ = "workflow_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)

    # State information
    current_state = Column(String(50), nullable=False, index=True)
    previous_state = Column(String(50), nullable=True)

    # Processing information
    step_name = Column(String(100), nullable=True)
    step_status = Column(String(50), nullable=True)  # 'pending', 'in_progress', 'completed', 'failed'
    step_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    can_retry = Column(Boolean, default=True)

    # Metadata
    confidence_score = Column(Numeric(3, 2), nullable=True)
    extracted_data = Column(Text, nullable=True)  # JSON string for flexibility

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    application = relationship("Application", back_populates="workflow_states")

    def __repr__(self):
        return f"<WorkflowState(application_id='{self.application_id}', current_state='{self.current_state}')>"