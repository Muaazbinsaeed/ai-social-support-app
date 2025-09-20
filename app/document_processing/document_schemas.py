"""
Pydantic schemas for document processing
"""

from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class DocumentUpload(BaseModel):
    """Schema for document upload metadata"""
    document_type: str
    original_filename: str
    file_size: int
    mime_type: str

    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v):
        allowed_types = ['bank_statement', 'emirates_id']
        if v not in allowed_types:
            raise ValueError(f'Document type must be one of: {", ".join(allowed_types)}')
        return v

    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        max_size = 52428800  # 50MB
        if v > max_size:
            raise ValueError(f'File size cannot exceed {max_size} bytes')
        return v


class DocumentResponse(BaseModel):
    """Schema for document information in responses"""
    id: str
    application_id: str
    document_type: str
    original_filename: str
    file_size: int
    mime_type: str
    processing_status: str
    ocr_confidence: Optional[Decimal]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class OCRResult(BaseModel):
    """Schema for OCR processing results"""
    confidence: float
    extracted_text: str
    processing_time_ms: int
    language_detected: Optional[str] = None
    text_regions: Optional[List[Dict[str, Any]]] = None


class DocumentAnalysisResult(BaseModel):
    """Schema for structured document analysis results"""
    document_type: str
    confidence: float
    extracted_data: Dict[str, Any]
    processing_time_ms: int
    model_used: str

    # Bank statement specific fields
    monthly_income: Optional[Decimal] = None
    account_balance: Optional[Decimal] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    statement_period: Optional[str] = None

    # Emirates ID specific fields
    full_name: Optional[str] = None
    id_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiry_date: Optional[str] = None


class DocumentProcessingStatus(BaseModel):
    """Schema for document processing status"""
    document_id: str
    processing_status: str
    current_step: Optional[str] = None
    progress_percentage: int
    steps_completed: List[str]
    estimated_completion_time: Optional[int] = None  # seconds
    error_message: Optional[str] = None
    can_retry: bool = True


class ProcessingLogEntry(BaseModel):
    """Schema for individual processing log entries"""
    processing_step: str
    step_status: str
    step_result: Optional[Dict[str, Any]]
    confidence_score: Optional[Decimal]
    processing_time_ms: Optional[int]
    error_type: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentUploadRequest(BaseModel):
    """Schema for document upload request with metadata"""
    document_type: str
    description: Optional[str] = None

    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v):
        allowed_types = ['bank_statement', 'emirates_id']
        if v not in allowed_types:
            raise ValueError(f'Document type must be one of: {", ".join(allowed_types)}')
        return v


class DocumentRetryRequest(BaseModel):
    """Schema for retry processing request"""
    retry_step: Optional[str] = None  # If None, retry all failed steps
    force_retry: bool = False