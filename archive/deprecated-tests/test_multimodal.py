#!/usr/bin/env python3
"""
Test script for multimodal AI analysis functionality
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.document_processing.multimodal_service import MultimodalService
from app.document_processing.ocr_service import OCRService
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

def test_multimodal_analysis():
    """Test multimodal AI analysis with mock OCR data"""

    # Initialize services
    ocr_service = OCRService()
    multimodal_service = MultimodalService()

    # Test file paths
    emirates_id_path = "/Users/muaazbinsaeed/Documents/EmirateIDFront.jpg"
    bank_statement_path = "/Users/muaazbinsaeed/Documents/Bank Muaaz Alfalah Statement.pdf"

    print("=" * 60)
    print("MULTIMODAL AI ANALYSIS TEST")
    print("=" * 60)

    # Test 1: Emirates ID Analysis
    print(f"\n1. Testing Emirates ID Analysis")
    print("-" * 40)
    try:
        # Extract text with OCR first
        ocr_result = ocr_service.extract_text(emirates_id_path)
        print(f"OCR Text Length: {len(ocr_result.extracted_text)}")

        # Analyze with multimodal AI
        analysis_result = multimodal_service.analyze_document(
            text_content=ocr_result.extracted_text,
            document_type="emirates_id",
            file_path=emirates_id_path
        )

        print(f"Analysis Success: {analysis_result.get('success')}")
        print(f"Analysis Type: {analysis_result.get('analysis_type')}")
        print(f"Model Used: {analysis_result.get('model_used')}")
        print(f"Processing Time: {analysis_result.get('processing_time', 0):.3f}s")

        extracted_data = analysis_result.get('extracted_data', {})
        print(f"\nExtracted Data:")
        for key, value in extracted_data.items():
            print(f"  {key}: {value}")

        if analysis_result.get('error'):
            print(f"Error: {analysis_result['error']}")

    except Exception as e:
        print(f"Error in Emirates ID analysis: {e}")

    # Test 2: Bank Statement Analysis
    print(f"\n2. Testing Bank Statement Analysis")
    print("-" * 40)
    try:
        # Extract text with OCR first
        ocr_result = ocr_service.extract_text(bank_statement_path)
        print(f"OCR Text Length: {len(ocr_result.extracted_text)}")

        # Analyze with multimodal AI
        analysis_result = multimodal_service.analyze_document(
            text_content=ocr_result.extracted_text,
            document_type="bank_statement",
            file_path=bank_statement_path
        )

        print(f"Analysis Success: {analysis_result.get('success')}")
        print(f"Analysis Type: {analysis_result.get('analysis_type')}")
        print(f"Model Used: {analysis_result.get('model_used')}")
        print(f"Processing Time: {analysis_result.get('processing_time', 0):.3f}s")

        extracted_data = analysis_result.get('extracted_data', {})
        print(f"\nExtracted Data:")
        for key, value in extracted_data.items():
            print(f"  {key}: {value}")

        if analysis_result.get('error'):
            print(f"Error: {analysis_result['error']}")

    except Exception as e:
        print(f"Error in Bank Statement analysis: {e}")

    # Test 3: Combined Analysis Summary
    print(f"\n3. Testing Analysis Summary")
    print("-" * 40)
    try:
        # Create sample analyses for summary test
        sample_analyses = [
            {
                'success': True,
                'analysis_type': 'emirates_id',
                'processing_time': 2.5,
                'extracted_data': {
                    'full_name': 'Muaaz Bin Saeed',
                    'emirates_id_number': '784-1995-1234567-8',
                    'confidence_score': 0.85
                }
            },
            {
                'success': True,
                'analysis_type': 'bank_statement',
                'processing_time': 3.2,
                'extracted_data': {
                    'monthly_income': 8500.0,
                    'account_balance': 22207.25,
                    'confidence_score': 0.88
                }
            }
        ]

        summary = multimodal_service.get_analysis_summary(sample_analyses)
        print(f"Analysis Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error in summary analysis: {e}")

    print("\n" + "=" * 60)
    print("MULTIMODAL AI ANALYSIS TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_multimodal_analysis()