"""
Document database models
"""

from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from app.shared.database import Base


class Document(Base):
    """Document model for file storage and processing tracking"""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # File metadata
    document_type = Column(String(50), nullable=False, index=True)  # 'bank_statement', 'emirates_id'
    original_filename = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Processing status
    processing_status = Column(String(50), default="uploaded", index=True)
    # Statuses: 'uploaded', 'processing', 'ocr_completed', 'analyzed', 'failed'

    # OCR Results
    ocr_confidence = Column(Numeric(3, 2), nullable=True)
    extracted_text = Column(Text, nullable=True)

    # Structured data extraction results (stored as JSON)
    structured_data = Column(JSONB, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Processing metrics
    ocr_processing_time_ms = Column(Integer, nullable=True)
    analysis_processing_time_ms = Column(Integer, nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("Application", back_populates="documents")
    user = relationship("User")

    def __repr__(self):
        return f"<Document(id='{self.id}', type='{self.document_type}', status='{self.processing_status}')>"


class DocumentProcessingLog(Base):
    """Detailed processing log for documents"""

    __tablename__ = "document_processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)

    # Processing step information
    processing_step = Column(String(100), nullable=False)  # 'ocr', 'multimodal_analysis', 'data_extraction'
    step_status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed'

    # Results and metrics
    step_result = Column(JSONB, nullable=True)  # Flexible JSON storage for step results
    confidence_score = Column(Numeric(3, 2), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Error information
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document")

    def __repr__(self):
        return f"<ProcessingLog(document_id='{self.document_id}', step='{self.processing_step}', status='{self.step_status}')>"