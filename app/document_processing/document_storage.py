"""
Document storage and management service
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, LargeBinary, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.shared.database import Base


class DocumentType(str, enum.Enum):
    BANK_STATEMENT = "bank_statement"
    EMIRATES_ID = "emirates_id"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
    RESET = "reset"


class Document(Base):
    """Document model for storing user documents"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    application_id = Column(UUID(as_uuid=True), nullable=True)
    
    document_type = Column(Enum(DocumentType), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to file on disk
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    
    # Metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Processing results
    ocr_text = Column(Text, nullable=True)
    analysis_result = Column(Text, nullable=True)  # JSON string
    confidence_score = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document {self.document_type}: {self.filename}>"


# Add to User model (update user_models.py)
# documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
