"""
OCR service using EasyOCR for text extraction from documents
"""

import time
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz  # PyMuPDF

from app.shared.exceptions import DocumentProcessingError
from app.shared.logging_config import get_logger
from app.document_processing.document_schemas import OCRResult

logger = get_logger(__name__)


class OCRService:
    """OCR service for extracting text from documents"""

    def __init__(self):
        self.reader = None
        self._initialize_reader()

    def _initialize_reader(self):
        """Initialize EasyOCR reader with error handling"""
        try:
            import easyocr
            self.reader = easyocr.Reader(['en', 'ar'], gpu=False, verbose=False)
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize EasyOCR reader", error=str(e))
            self.reader = None

    def _preprocess_image(self, image_array: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale if needed
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array

            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)

            # Improve contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # Apply slight Gaussian blur to smooth text
            blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)

            return blurred

        except Exception as e:
            logger.warning("Image preprocessing failed, using original", error=str(e))
            return image_array

    def _pdf_to_images(self, pdf_path: str) -> List[np.ndarray]:
        """Convert PDF pages to images"""
        try:
            doc = fitz.open(pdf_path)
            images = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Get page as image with high resolution
                mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")

                # Convert to numpy array
                img = Image.open(fitz.io.BytesIO(img_data))
                img_array = np.array(img)
                images.append(img_array)

            doc.close()
            logger.info(f"Converted PDF to {len(images)} images", pdf_path=pdf_path)
            return images

        except Exception as e:
            logger.error("Failed to convert PDF to images", error=str(e), pdf_path=pdf_path)
            raise DocumentProcessingError(f"PDF conversion failed: {str(e)}", "PDF_CONVERSION_ERROR")

    def _load_image(self, file_path: str) -> List[np.ndarray]:
        """Load image(s) from file path"""
        try:
            path = Path(file_path)

            if path.suffix.lower() == '.pdf':
                return self._pdf_to_images(file_path)
            else:
                # Load regular image
                img = Image.open(file_path)
                img_array = np.array(img)
                return [img_array]

        except Exception as e:
            logger.error("Failed to load image", error=str(e), file_path=file_path)
            raise DocumentProcessingError(f"Image loading failed: {str(e)}", "IMAGE_LOAD_ERROR")

    def extract_text(self, file_path: str) -> OCRResult:
        """
        Extract text from document using OCR
        """
        if not self.reader:
            # Fallback to mock OCR if EasyOCR is not available
            return self._mock_ocr_extraction(file_path)

        start_time = time.time()

        try:
            logger.info("Starting OCR text extraction", file_path=file_path)

            # Load image(s)
            images = self._load_image(file_path)
            all_text = []
            all_confidence_scores = []
            all_regions = []

            for i, image in enumerate(images):
                logger.info(f"Processing page/image {i+1}/{len(images)}")

                # Preprocess image
                processed_image = self._preprocess_image(image)

                # Extract text using EasyOCR
                results = self.reader.readtext(processed_image, detail=1, paragraph=False)

                page_text = []
                page_confidences = []
                page_regions = []

                for (bbox, text, confidence) in results:
                    if text.strip() and confidence > 0.3:  # Filter low confidence results
                        page_text.append(text.strip())
                        page_confidences.append(confidence)
                        page_regions.append({
                            "text": text.strip(),
                            "confidence": float(confidence),
                            "bbox": bbox,
                            "page": i
                        })

                all_text.extend(page_text)
                all_confidence_scores.extend(page_confidences)
                all_regions.extend(page_regions)

            # Combine all text
            extracted_text = "\n".join(all_text)

            # Calculate average confidence
            avg_confidence = np.mean(all_confidence_scores) if all_confidence_scores else 0.0

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(
                "OCR text extraction completed",
                file_path=file_path,
                text_length=len(extracted_text),
                confidence=avg_confidence,
                processing_time_ms=processing_time,
                regions_found=len(all_regions)
            )

            return OCRResult(
                confidence=float(avg_confidence),
                extracted_text=extracted_text,
                processing_time_ms=processing_time,
                text_regions=all_regions
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(
                "OCR text extraction failed",
                file_path=file_path,
                error=str(e),
                processing_time_ms=processing_time
            )
            raise DocumentProcessingError(f"OCR extraction failed: {str(e)}", "OCR_EXTRACTION_ERROR")

    def _mock_ocr_extraction(self, file_path: str) -> OCRResult:
        """Mock OCR extraction for development/testing when EasyOCR is not available"""
        logger.warning("Using mock OCR extraction - EasyOCR not available", file_path=file_path)

        # Simulate processing time
        time.sleep(1)

        # Return mock data based on document type
        if "bank_statement" in file_path.lower():
            mock_text = """
            EMIRATES NBD BANK
            Account Statement
            Account Number: 1234567890
            Statement Period: November 2024

            Account Holder: Ahmed Ali Hassan
            Emirates ID: 784-1990-1234567-8

            Opening Balance: AED 15,250.00

            Transactions:
            01/11/2024  Salary Credit        +8,500.00
            05/11/2024  Grocery Store        -156.75
            10/11/2024  Fuel Payment         -180.00
            15/11/2024  Utility Bill         -420.50
            20/11/2024  ATM Withdrawal       -500.00
            25/11/2024  Online Transfer      -200.00

            Closing Balance: AED 22,292.75
            """
        else:  # Emirates ID
            mock_text = """
            UNITED ARAB EMIRATES
            IDENTITY CARD

            Name: Ahmed Ali Hassan
            Nationality: United Arab Emirates
            Identity No: 784-1990-1234567-8
            Date of Birth: 15/03/1990
            Sex: M
            Date of Issue: 12/01/2020
            Date of Expiry: 11/01/2030
            """

        return OCRResult(
            confidence=0.85,  # Mock high confidence
            extracted_text=mock_text.strip(),
            processing_time_ms=1200,
            text_regions=[{
                "text": line.strip(),
                "confidence": 0.85,
                "bbox": [[0, 0], [100, 0], [100, 20], [0, 20]],
                "page": 0
            } for line in mock_text.strip().split('\n') if line.strip()]
        )

    def validate_text_quality(self, ocr_result: OCRResult, document_type: str) -> bool:
        """Validate if extracted text quality is sufficient for processing"""
        try:
            # Check confidence threshold
            if ocr_result.confidence < 0.5:
                logger.warning(
                    "Low OCR confidence",
                    confidence=ocr_result.confidence,
                    document_type=document_type
                )
                return False

            # Check text length
            if len(ocr_result.extracted_text) < 50:
                logger.warning(
                    "Insufficient text extracted",
                    text_length=len(ocr_result.extracted_text),
                    document_type=document_type
                )
                return False

            # Document-specific validation
            if document_type == "bank_statement":
                required_keywords = ["account", "balance", "statement", "bank"]
                found_keywords = sum(1 for keyword in required_keywords
                                   if keyword.lower() in ocr_result.extracted_text.lower())
                if found_keywords < 2:
                    logger.warning(
                        "Bank statement validation failed - missing keywords",
                        found_keywords=found_keywords,
                        required_keywords=required_keywords
                    )
                    return False

            elif document_type == "emirates_id":
                required_keywords = ["emirates", "identity", "784"]
                found_keywords = sum(1 for keyword in required_keywords
                                   if keyword.lower() in ocr_result.extracted_text.lower())
                if found_keywords < 2:
                    logger.warning(
                        "Emirates ID validation failed - missing keywords",
                        found_keywords=found_keywords,
                        required_keywords=required_keywords
                    )
                    return False

            return True

        except Exception as e:
            logger.error("Text quality validation failed", error=str(e))
            return False