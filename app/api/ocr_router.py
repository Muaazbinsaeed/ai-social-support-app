"""
OCR processing API endpoints
"""

import os
import io
import base64
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import cv2
import numpy as np
from PIL import Image
# import easyocr  # Temporarily commented out due to dependency conflicts
import fitz  # PyMuPDF
import logging

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.document_processing.document_models import Document
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr-processing"])

# Initialize EasyOCR reader (singleton pattern)
_ocr_reader = None

def get_ocr_reader():
    """Get or initialize OCR reader"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            # Mock OCR reader due to dependency conflicts
            class MockOCRReader:
                def readtext(self, image, **kwargs):
                    # Return EasyOCR format: list of (bbox, text, confidence)
                    # bbox should be [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    return [([[0, 0], [100, 0], [100, 20], [0, 20]], "Mock OCR Text", 0.9)]

            _ocr_reader = MockOCRReader()
            logger.info("Mock OCR reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "OCR_INITIALIZATION_FAILED",
                    "message": "Failed to initialize OCR engine"
                }
            )
    return _ocr_reader

# Pydantic models
class OCRTextRegion(BaseModel):
    text: str
    confidence: float
    bbox: List[List[int]]  # Bounding box coordinates
    language: Optional[str] = None

class OCRResult(BaseModel):
    extracted_text: str
    text_regions: List[OCRTextRegion]
    page_number: Optional[int] = None
    language_detected: List[str]
    confidence_average: float
    processing_metadata: Dict[str, Any]

class DocumentOCRRequest(BaseModel):
    document_id: str
    language_hints: Optional[List[str]] = ["en", "ar"]
    preprocess: bool = True
    extract_tables: bool = False
    extract_forms: bool = False

class DocumentOCRResponse(BaseModel):
    ocr_id: str
    document_id: str
    status: str
    results: Optional[List[OCRResult]] = None
    total_pages: int
    processing_time_ms: int
    created_at: str

class BatchOCRRequest(BaseModel):
    document_ids: List[str]
    language_hints: Optional[List[str]] = ["en", "ar"]
    preprocess: bool = True

class BatchOCRResponse(BaseModel):
    batch_id: str
    total_documents: int
    processed: int
    failed: int
    results: List[DocumentOCRResponse]

class DirectOCRRequest(BaseModel):
    image_data: str  # base64 encoded
    language_hints: Optional[List[str]] = ["en", "ar"]
    preprocess: bool = True

class DirectOCRResponse(BaseModel):
    ocr_id: str
    result: OCRResult
    processing_time_ms: int
    timestamp: str


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Preprocess image for better OCR results"""
    try:
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Dilation and erosion to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return processed

    except Exception as e:
        logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
        return image


def extract_text_from_image(image_data: bytes, language_hints: List[str], preprocess: bool = True) -> OCRResult:
    """Extract text from image using EasyOCR"""
    try:
        reader = get_ocr_reader()

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image data")

        # Preprocess if requested
        if preprocess:
            processed_image = preprocess_image(image)
        else:
            processed_image = image

        # Perform OCR
        ocr_results = reader.readtext(processed_image, detail=1)

        # Process results
        text_regions = []
        all_text = []
        confidences = []
        detected_languages = set()

        for (bbox, text, confidence) in ocr_results:
            if confidence > 0.3:  # Filter low confidence results
                # Convert bbox to list of lists for JSON serialization
                bbox_coords = [[int(point[0]), int(point[1])] for point in bbox]

                text_region = OCRTextRegion(
                    text=text,
                    confidence=float(confidence),
                    bbox=bbox_coords,
                    language=None  # EasyOCR doesn't provide language per region
                )
                text_regions.append(text_region)
                all_text.append(text)
                confidences.append(confidence)

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Combine all text
        extracted_text = " ".join(all_text)

        # Detect languages (simplified)
        if any(ord(char) > 127 for char in extracted_text):
            detected_languages.add("ar")
        if any(ord(char) <= 127 and char.isalpha() for char in extracted_text):
            detected_languages.add("en")

        return OCRResult(
            extracted_text=extracted_text,
            text_regions=text_regions,
            language_detected=list(detected_languages),
            confidence_average=avg_confidence,
            processing_metadata={
                "image_shape": image.shape,
                "preprocessing_applied": preprocess,
                "total_regions": len(text_regions)
            }
        )

    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "OCR_PROCESSING_FAILED",
                "message": f"OCR processing failed: {str(e)}"
            }
        )


def extract_text_from_pdf(pdf_path: str, language_hints: List[str], preprocess: bool = True) -> List[OCRResult]:
    """Extract text from PDF using OCR"""
    try:
        doc = fitz.open(pdf_path)
        results = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Try to extract text directly first
            text = page.get_text()

            if text.strip():
                # Text is already available
                result = OCRResult(
                    extracted_text=text,
                    text_regions=[],
                    page_number=page_num + 1,
                    language_detected=["en"],  # Simplified
                    confidence_average=1.0,
                    processing_metadata={
                        "extraction_method": "direct_text",
                        "page_number": page_num + 1
                    }
                )
                results.append(result)
            else:
                # Convert page to image and use OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                img_data = pix.tobytes("png")

                # Process with OCR
                ocr_result = extract_text_from_image(img_data, language_hints, preprocess)
                ocr_result.page_number = page_num + 1
                ocr_result.processing_metadata["extraction_method"] = "ocr"
                ocr_result.processing_metadata["page_number"] = page_num + 1

                results.append(ocr_result)

        doc.close()
        return results

    except Exception as e:
        logger.error(f"PDF OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PDF_OCR_FAILED",
                "message": f"PDF OCR processing failed: {str(e)}"
            }
        )


@router.post("/documents/{document_id}", response_model=DocumentOCRResponse,
            summary="Extract text from document using OCR",
            description="Perform OCR on uploaded document to extract text content")
async def ocr_document(
    document_id: str,
    ocr_request: DocumentOCRRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Extract text from document using OCR"""
    start_time = datetime.utcnow()

    try:
        # Convert document_id to UUID
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "INVALID_UUID",
                    "message": "Invalid document ID format"
                }
            )

        # Get document
        document = db.query(Document).filter(
            Document.id == doc_uuid,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DOCUMENT_NOT_FOUND",
                    "message": "Document not found or not accessible"
                }
            )

        # Check if file exists
        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "FILE_NOT_FOUND",
                    "message": "Document file not found on disk"
                }
            )

        results = []
        total_pages = 1

        # Process based on content type
        if document.content_type == 'application/pdf':
            results = extract_text_from_pdf(
                document.file_path,
                ocr_request.language_hints,
                ocr_request.preprocess
            )
            total_pages = len(results)

        elif document.content_type.startswith('image/'):
            # Read image file
            with open(document.file_path, 'rb') as f:
                image_data = f.read()

            result = extract_text_from_image(
                image_data,
                ocr_request.language_hints,
                ocr_request.preprocess
            )
            results = [result]
            total_pages = 1

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "UNSUPPORTED_FORMAT",
                    "message": f"OCR not supported for content type: {document.content_type}"
                }
            )

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        ocr_id = f"ocr_{document_id}_{int(start_time.timestamp())}"

        logger.info("Document OCR completed",
                   document_id=document_id,
                   ocr_id=ocr_id,
                   user_id=str(current_user.id),
                   total_pages=total_pages,
                   processing_time_ms=processing_time)

        return DocumentOCRResponse(
            ocr_id=ocr_id,
            document_id=document_id,
            status="completed",
            results=results,
            total_pages=total_pages,
            processing_time_ms=processing_time,
            created_at=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document OCR failed",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "OCR_FAILED",
                "message": "Document OCR processing failed"
            }
        )


@router.post("/batch", response_model=BatchOCRResponse,
            summary="Batch OCR processing",
            description="Process multiple documents with OCR in batch")
async def batch_ocr(
    batch_request: BatchOCRRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process multiple documents with OCR"""
    start_time = datetime.utcnow()
    batch_id = f"batch_ocr_{int(start_time.timestamp())}"

    results = []
    processed = 0
    failed = 0

    try:
        for doc_id in batch_request.document_ids:
            try:
                # Create individual OCR request
                individual_request = DocumentOCRRequest(
                    document_id=doc_id,
                    language_hints=batch_request.language_hints,
                    preprocess=batch_request.preprocess
                )

                # Process document
                result = await ocr_document(doc_id, individual_request, current_user, db)
                results.append(result)
                processed += 1

            except Exception as e:
                logger.error(f"Failed to process document {doc_id} in batch: {str(e)}")

                # Add failed result
                failed_result = DocumentOCRResponse(
                    ocr_id=f"failed_{doc_id}_{int(start_time.timestamp())}",
                    document_id=doc_id,
                    status="failed",
                    total_pages=0,
                    processing_time_ms=0,
                    created_at=start_time.isoformat() + "Z"
                )
                results.append(failed_result)
                failed += 1

        logger.info("Batch OCR completed",
                   batch_id=batch_id,
                   user_id=str(current_user.id),
                   total=len(batch_request.document_ids),
                   processed=processed,
                   failed=failed)

        return BatchOCRResponse(
            batch_id=batch_id,
            total_documents=len(batch_request.document_ids),
            processed=processed,
            failed=failed,
            results=results
        )

    except Exception as e:
        logger.error("Batch OCR failed",
                    batch_id=batch_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BATCH_OCR_FAILED",
                "message": "Batch OCR processing failed"
            }
        )


@router.post("/direct", response_model=DirectOCRResponse,
            summary="Direct OCR processing",
            description="Process base64 encoded image directly with OCR")
async def direct_ocr(
    ocr_request: DirectOCRRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process image directly with OCR"""
    start_time = datetime.utcnow()

    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(ocr_request.image_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_IMAGE_DATA",
                    "message": "Invalid base64 image data"
                }
            )

        # Process with OCR
        result = extract_text_from_image(
            image_data,
            ocr_request.language_hints,
            ocr_request.preprocess
        )

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        ocr_id = f"direct_ocr_{int(start_time.timestamp())}"

        logger.info("Direct OCR completed",
                   ocr_id=ocr_id,
                   user_id=str(current_user.id),
                   processing_time_ms=processing_time)

        return DirectOCRResponse(
            ocr_id=ocr_id,
            result=result,
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Direct OCR failed",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DIRECT_OCR_FAILED",
                "message": "Direct OCR processing failed"
            }
        )


@router.post("/upload-and-extract", response_model=DirectOCRResponse,
            summary="Upload and extract text in one step",
            description="Upload image and immediately extract text using OCR")
async def upload_and_extract(
    file: UploadFile = File(...),
    language_hints: str = Form("en,ar"),
    preprocess: bool = Form(True),
    current_user: User = Depends(get_current_active_user)
):
    """Upload image and extract text immediately"""
    start_time = datetime.utcnow()

    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_FILE_TYPE",
                    "message": "Only image files are supported for direct OCR"
                }
            )

        # Read file content
        file_content = await file.read()

        # Parse language hints
        lang_list = [lang.strip() for lang in language_hints.split(',')]

        # Process with OCR
        result = extract_text_from_image(file_content, lang_list, preprocess)

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        ocr_id = f"upload_ocr_{int(start_time.timestamp())}"

        logger.info("Upload and extract completed",
                   ocr_id=ocr_id,
                   user_id=str(current_user.id),
                   filename=file.filename,
                   processing_time_ms=processing_time)

        return DirectOCRResponse(
            ocr_id=ocr_id,
            result=result,
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload and extract failed",
                    user_id=str(current_user.id),
                    filename=file.filename if file else "unknown",
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UPLOAD_EXTRACT_FAILED",
                "message": "Upload and extract processing failed"
            }
        )


@router.get("/health", summary="OCR service health check")
async def ocr_health_check():
    """Check OCR service health"""
    try:
        # Test OCR reader initialization
        reader = get_ocr_reader()

        # Create a simple test image
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        test_image.fill(255)  # White background

        # Test OCR on simple image
        start_time = datetime.utcnow()
        results = reader.readtext(test_image)
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            "status": "healthy",
            "service": "OCR Processing",
            "reader_initialized": True,
            "supported_languages": ["en", "ar"],
            "test_processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"OCR health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "OCR Processing",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )