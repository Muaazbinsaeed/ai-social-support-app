"""
Multimodal document analysis API endpoints
"""

import os
import base64
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests
from PIL import Image
import io

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.document_processing.document_models import Document
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["multimodal-analysis"])

# Pydantic models
class AnalysisResult(BaseModel):
    content_type: str
    extracted_text: Optional[str] = None
    visual_description: Optional[str] = None
    entities: List[Dict[str, Any]] = []
    confidence_score: float
    language: str = "en"
    analysis_metadata: Dict[str, Any] = {}

class DocumentAnalysisRequest(BaseModel):
    document_id: str
    analysis_type: str = "full"  # full, text_only, visual_only
    custom_prompt: Optional[str] = None

class DocumentAnalysisResponse(BaseModel):
    analysis_id: str
    document_id: str
    status: str
    results: Optional[AnalysisResult] = None
    processing_time_ms: Optional[int] = None
    created_at: str

class BulkAnalysisRequest(BaseModel):
    document_ids: List[str]
    analysis_type: str = "full"
    custom_prompt: Optional[str] = None

class BulkAnalysisResponse(BaseModel):
    batch_id: str
    total_documents: int
    processed: int
    failed: int
    results: List[DocumentAnalysisResponse]

class MultimodalQuery(BaseModel):
    query: str
    image_data: Optional[str] = None  # base64 encoded
    context: Optional[str] = None

class MultimodalQueryResponse(BaseModel):
    query_id: str
    response: str
    confidence: float
    processing_time_ms: int
    timestamp: str


async def call_ollama_vision(image_data: bytes, prompt: str) -> Dict[str, Any]:
    """Call Ollama moondream model for visual analysis"""
    try:
        # Convert image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Prepare request to Ollama
        ollama_request = {
            "model": "moondream:1.8b",
            "prompt": prompt,
            "images": [image_b64],
            "stream": False
        }

        # Make request to Ollama API
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
                "confidence": 0.85  # Default confidence for moondream
            }
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"Ollama API error: {response.status_code}"
            }

    except Exception as e:
        logger.error(f"Error calling Ollama vision model: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract entities from text using Ollama"""
    try:
        prompt = f"""
        Extract key entities from this text and categorize them. Return a JSON list of entities with their types.
        Focus on: names, dates, amounts, document types, locations, organizations.

        Text: {text}

        Return format: [{"entity": "entity_name", "type": "entity_type", "confidence": 0.9}]
        """

        ollama_request = {
            "model": "qwen2:1.5b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=ollama_request,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            # Try to parse JSON from response
            try:
                import json
                entities = json.loads(result.get("response", "[]"))
                return entities if isinstance(entities, list) else []
            except:
                # Fallback if JSON parsing fails
                return [{"entity": "extraction_failed", "type": "error", "confidence": 0.0}]
        else:
            return []

    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        return []


@router.post("/documents/{document_id}", response_model=DocumentAnalysisResponse,
            summary="Analyze document with multimodal AI",
            description="Perform multimodal analysis on uploaded document using vision and text models")
async def analyze_document(
    document_id: str,
    analysis_request: DocumentAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Analyze document using multimodal AI models"""
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

        # Read file content
        with open(document.file_path, 'rb') as f:
            file_content = f.read()

        # Initialize results
        analysis_result = AnalysisResult(
            content_type=document.mime_type or "application/octet-stream",
            confidence_score=0.0,
            analysis_metadata={"file_size": len(file_content)}
        )

        # Determine analysis approach based on content type
        mime_type = document.mime_type or "application/octet-stream"
        if mime_type.startswith('image/'):
            # Enhanced image processing for Emirates ID
            # Image analysis
            prompt = analysis_request.custom_prompt or "Describe this document in detail. What type of document is this? What information can you extract from it?"

            vision_result = await call_ollama_vision(file_content, prompt)

            if vision_result["success"]:
                analysis_result.visual_description = vision_result["response"]
                analysis_result.confidence_score = vision_result["confidence"]

                # Extract entities from visual description
                if analysis_request.analysis_type in ["full", "text_only"]:
                    entities = await extract_entities_from_text(vision_result["response"])
                    analysis_result.entities = entities
            else:
                # Fallback for image analysis failure - still return success with lower confidence
                analysis_result.visual_description = "Image analysis failed, using fallback description"
                analysis_result.confidence_score = 0.3
                analysis_result.entities = [{"entity": "analysis_fallback", "type": "error", "confidence": 0.3}]
                logger.warning(f"Vision analysis failed for document {document_id}, using fallback", error=vision_result.get("error"))

        elif mime_type == 'application/pdf':
            # PDF analysis - combine OCR and vision if needed
            try:
                # Try to extract text first
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                extracted_text = ""
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"

                if extracted_text.strip():
                    analysis_result.extracted_text = extracted_text
                    analysis_result.confidence_score = 0.9

                    # Extract entities from text
                    if analysis_request.analysis_type in ["full", "text_only"]:
                        entities = await extract_entities_from_text(extracted_text)
                        analysis_result.entities = entities
                else:
                    # Fallback to OCR if no text extracted
                    analysis_result.extracted_text = "PDF contains no extractable text - OCR processing recommended"
                    analysis_result.confidence_score = 0.3

            except Exception as e:
                logger.error(f"PDF processing error: {str(e)}")
                analysis_result.extracted_text = f"PDF processing failed: {str(e)}"
                analysis_result.confidence_score = 0.1

        else:
            # Plain text or other formats
            try:
                text_content = file_content.decode('utf-8')
                analysis_result.extracted_text = text_content
                analysis_result.confidence_score = 0.95

                # Extract entities
                if analysis_request.analysis_type in ["full", "text_only"]:
                    entities = await extract_entities_from_text(text_content)
                    analysis_result.entities = entities

            except UnicodeDecodeError:
                analysis_result.extracted_text = "Binary file - cannot extract text"
                analysis_result.confidence_score = 0.0

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Generate analysis ID
        analysis_id = f"analysis_{document_id}_{int(start_time.timestamp())}"

        logger.info("Document analysis completed",
                   document_id=document_id,
                   analysis_id=analysis_id,
                   user_id=str(current_user.id),
                   processing_time_ms=processing_time)

        return DocumentAnalysisResponse(
            analysis_id=analysis_id,
            document_id=document_id,
            status="completed",
            results=analysis_result,
            processing_time_ms=processing_time,
            created_at=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document analysis failed",
                    document_id=document_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ANALYSIS_FAILED",
                "message": "Document analysis failed"
            }
        )


@router.post("/bulk", response_model=BulkAnalysisResponse,
            summary="Bulk analyze multiple documents",
            description="Analyze multiple documents in a single request")
async def bulk_analyze_documents(
    bulk_request: BulkAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Analyze multiple documents in bulk"""
    start_time = datetime.utcnow()
    batch_id = f"batch_{int(start_time.timestamp())}"

    results = []
    processed = 0
    failed = 0

    try:
        for doc_id in bulk_request.document_ids:
            try:
                # Create individual analysis request
                individual_request = DocumentAnalysisRequest(
                    document_id=doc_id,
                    analysis_type=bulk_request.analysis_type,
                    custom_prompt=bulk_request.custom_prompt
                )

                # Analyze document
                result = await analyze_document(doc_id, individual_request, current_user, db)
                results.append(result)
                processed += 1

            except Exception as e:
                logger.error(f"Failed to analyze document {doc_id}: {str(e)}")
                # Add failed result
                failed_result = DocumentAnalysisResponse(
                    analysis_id=f"failed_{doc_id}_{int(start_time.timestamp())}",
                    document_id=doc_id,
                    status="failed",
                    created_at=start_time.isoformat() + "Z"
                )
                results.append(failed_result)
                failed += 1

        logger.info("Bulk analysis completed",
                   batch_id=batch_id,
                   user_id=str(current_user.id),
                   total=len(bulk_request.document_ids),
                   processed=processed,
                   failed=failed)

        return BulkAnalysisResponse(
            batch_id=batch_id,
            total_documents=len(bulk_request.document_ids),
            processed=processed,
            failed=failed,
            results=results
        )

    except Exception as e:
        logger.error("Bulk analysis failed",
                    batch_id=batch_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BULK_ANALYSIS_FAILED",
                "message": "Bulk document analysis failed"
            }
        )


@router.post("/query", response_model=MultimodalQueryResponse,
            summary="Interactive multimodal query",
            description="Ask questions about images or perform visual reasoning")
async def multimodal_query(
    query_data: MultimodalQuery,
    current_user: User = Depends(get_current_active_user)
):
    """Interactive multimodal query with vision model"""
    start_time = datetime.utcnow()

    try:
        if not query_data.image_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "IMAGE_REQUIRED",
                    "message": "Image data is required for multimodal queries"
                }
            )

        # Decode base64 image
        try:
            image_bytes = base64.b64decode(query_data.image_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_IMAGE_DATA",
                    "message": "Invalid base64 image data"
                }
            )

        # Prepare prompt with context
        prompt = query_data.query
        if query_data.context:
            prompt = f"Context: {query_data.context}\n\nQuestion: {query_data.query}"

        # Call vision model
        vision_result = await call_ollama_vision(image_bytes, prompt)

        if not vision_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "VISION_QUERY_FAILED",
                    "message": vision_result["error"]
                }
            )

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        query_id = f"query_{int(start_time.timestamp())}"

        logger.info("Multimodal query completed",
                   query_id=query_id,
                   user_id=str(current_user.id),
                   processing_time_ms=processing_time)

        return MultimodalQueryResponse(
            query_id=query_id,
            response=vision_result["response"],
            confidence=vision_result["confidence"],
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Multimodal query failed",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QUERY_FAILED",
                "message": "Multimodal query failed"
            }
        )


@router.post("/upload-and-analyze", response_model=DocumentAnalysisResponse,
            summary="Upload and analyze document in one step",
            description="Upload a new document and immediately analyze it")
async def upload_and_analyze(
    file: UploadFile = File(...),
    analysis_type: str = Form("full"),
    custom_prompt: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and analyze document in single operation"""
    try:
        # First, create document record (simplified version)
        from app.api.document_management_router import upload_document

        # Upload document first - need to pass document_type parameter
        upload_result = await upload_document(file, "analysis_document", None, current_user, db)
        document_id = upload_result.id

        # Then analyze it
        analysis_request = DocumentAnalysisRequest(
            document_id=document_id,
            analysis_type=analysis_type,
            custom_prompt=custom_prompt
        )

        result = await analyze_document(document_id, analysis_request, current_user, db)

        logger.info("Upload and analyze completed",
                   document_id=document_id,
                   user_id=str(current_user.id))

        return result

    except Exception as e:
        logger.error("Upload and analyze failed",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UPLOAD_ANALYZE_FAILED",
                "message": "Failed to upload and analyze document"
            }
        )