#!/usr/bin/env python3
"""
Test script for OCR service functionality
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.document_processing.ocr_service import OCRService
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

def test_ocr_service():
    """Test OCR service with real documents"""

    # Initialize OCR service
    ocr_service = OCRService()

    # Test documents
    emirates_id_path = "/Users/muaazbinsaeed/Documents/EmirateIDFront.jpg"
    bank_statement_path = "/Users/muaazbinsaeed/Documents/Bank Muaaz Alfalah Statement.pdf"

    print("=" * 60)
    print("OCR SERVICE TEST")
    print("=" * 60)

    # Test 1: Emirates ID OCR
    if os.path.exists(emirates_id_path):
        print(f"\n1. Testing Emirates ID OCR: {emirates_id_path}")
        print("-" * 40)
        try:
            result = ocr_service.extract_text(emirates_id_path)
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Text Length: {len(result.extracted_text)}")
            print(f"Processing Time: {result.processing_time_ms}ms")
            print(f"Text Regions: {len(result.text_regions)}")
            print("\nExtracted Text:")
            print(result.extracted_text[:500] + "..." if len(result.extracted_text) > 500 else result.extracted_text)

            # Test validation
            is_valid = ocr_service.validate_text_quality(result, "emirates_id")
            print(f"\nValidation Result: {'PASS' if is_valid else 'FAIL'}")

        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Emirates ID file not found: {emirates_id_path}")

    # Test 2: Bank Statement OCR
    if os.path.exists(bank_statement_path):
        print(f"\n2. Testing Bank Statement OCR: {bank_statement_path}")
        print("-" * 40)
        try:
            result = ocr_service.extract_text(bank_statement_path)
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Text Length: {len(result.extracted_text)}")
            print(f"Processing Time: {result.processing_time_ms}ms")
            print(f"Text Regions: {len(result.text_regions)}")
            print("\nExtracted Text (first 500 chars):")
            print(result.extracted_text[:500] + "..." if len(result.extracted_text) > 500 else result.extracted_text)

            # Test validation
            is_valid = ocr_service.validate_text_quality(result, "bank_statement")
            print(f"\nValidation Result: {'PASS' if is_valid else 'FAIL'}")

        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Bank statement file not found: {bank_statement_path}")

    print("\n" + "=" * 60)
    print("OCR TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_ocr_service()