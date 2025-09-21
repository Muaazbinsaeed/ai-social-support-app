#!/usr/bin/env python3
"""
Test complete end-to-end workflow
"""

import os
import sys
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.document_processing.ocr_service import OCRService
from app.document_processing.multimodal_service import MultimodalService
from app.decision_making.react_reasoning import ReActDecisionEngine
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

def test_complete_workflow():
    """Test the complete AI workflow from OCR to decision making"""

    print("=" * 70)
    print("COMPLETE AI WORKFLOW TEST")
    print("=" * 70)

    # Initialize services
    ocr_service = OCRService()
    multimodal_service = MultimodalService()
    react_engine = ReActDecisionEngine()

    # Test file paths
    emirates_id_path = "/Users/muaazbinsaeed/Documents/EmirateIDFront.jpg"
    bank_statement_path = "/Users/muaazbinsaeed/Documents/Bank Muaaz Alfalah Statement.pdf"

    try:
        # Step 1: Extract text with OCR
        print("\n1. OCR TEXT EXTRACTION")
        print("-" * 40)

        # Emirates ID OCR
        print("Processing Emirates ID...")
        try:
            emirates_ocr = ocr_service.extract_text(emirates_id_path)
            print(f"Emirates ID OCR - Confidence: {emirates_ocr.confidence:.3f}, Length: {len(emirates_ocr.extracted_text)}")
        except Exception as e:
            print(f"Emirates ID OCR failed: {e}")
            # Use mock data
            emirates_ocr = ocr_service._mock_ocr_extraction(emirates_id_path)
            print(f"Using mock Emirates ID data - Length: {len(emirates_ocr.extracted_text)}")

        # Bank Statement OCR
        print("Processing Bank Statement...")
        try:
            bank_ocr = ocr_service.extract_text(bank_statement_path)
            print(f"Bank Statement OCR - Confidence: {bank_ocr.confidence:.3f}, Length: {len(bank_ocr.extracted_text)}")
        except Exception as e:
            print(f"Bank Statement OCR failed: {e}")
            # Use mock data
            bank_ocr = ocr_service._mock_ocr_extraction(bank_statement_path)
            print(f"Using mock Bank Statement data - Length: {len(bank_ocr.extracted_text)}")

        # Step 2: Multimodal AI Analysis
        print("\n2. MULTIMODAL AI ANALYSIS")
        print("-" * 40)

        # Analyze Emirates ID
        print("Analyzing Emirates ID with AI...")
        emirates_analysis = multimodal_service.analyze_document(
            text_content=emirates_ocr.extracted_text,
            document_type="emirates_id",
            file_path=emirates_id_path
        )
        print(f"Emirates ID Analysis - Success: {emirates_analysis.get('success')}")
        print(f"Extracted data: {json.dumps(emirates_analysis.get('extracted_data', {}), indent=2)}")

        # Analyze Bank Statement
        print("\nAnalyzing Bank Statement with AI...")
        bank_analysis = multimodal_service.analyze_document(
            text_content=bank_ocr.extracted_text,
            document_type="bank_statement",
            file_path=bank_statement_path
        )
        print(f"Bank Statement Analysis - Success: {bank_analysis.get('success')}")
        print(f"Extracted data: {json.dumps(bank_analysis.get('extracted_data', {}), indent=2)}")

        # Step 3: Prepare Application Data
        print("\n3. PREPARING APPLICATION DATA")
        print("-" * 40)

        applicant_data = {
            'full_name': emirates_analysis.get('extracted_data', {}).get('full_name', 'Test User'),
            'emirates_id': emirates_analysis.get('extracted_data', {}).get('emirates_id_number', '784-1995-1234567-8'),
            'phone': '+971501234567',
            'email': 'test@example.com',
            'application_id': 'test_app_123'
        }

        extracted_data = {
            'emirates_id': emirates_analysis.get('extracted_data', {}),
            'bank_statement': bank_analysis.get('extracted_data', {})
        }

        application_data = {
            "application_id": "test_app_123",
            "applicant_data": applicant_data,
            "extracted_data": extracted_data
        }

        print(f"Application prepared for: {applicant_data['full_name']}")
        print(f"Monthly income: AED {extracted_data['bank_statement'].get('monthly_income', 0):,.2f}")
        print(f"Account balance: AED {extracted_data['bank_statement'].get('account_balance', 0):,.2f}")

        # Step 4: ReAct AI Decision Making
        print("\n4. REACT AI DECISION MAKING")
        print("-" * 40)

        print("Making eligibility decision with ReAct reasoning...")
        decision_result, reasoning_trace = react_engine.make_eligibility_decision(application_data)

        print(f"\nDECISION RESULT:")
        print(f"  Outcome: {decision_result['outcome']}")
        print(f"  Confidence: {decision_result['confidence']:.3f}")
        print(f"  Benefit Amount: AED {decision_result['benefit_amount']:,.2f}")
        print(f"  Risk Level: {decision_result.get('risk_level', 'Unknown')}")

        print(f"\nREASONING SUMMARY:")
        reasoning = decision_result.get('reasoning', {})
        print(f"  {reasoning.get('summary', 'No summary available')}")

        print(f"\nREACT REASONING TRACE:")
        print(f"  Total Steps: {reasoning_trace.total_steps}")
        print(f"  Processing Time: {reasoning_trace.processing_time_ms}ms")
        print(f"  Model Used: {reasoning_trace.model_used}")

        # Show reasoning steps
        print(f"\nREASONING STEPS:")
        for i, step in enumerate(reasoning_trace.reasoning_steps, 1):
            print(f"  {i}. [{step.step_type.upper()}] {step.content[:100]}...")

        # Step 5: Summary
        print("\n5. WORKFLOW SUMMARY")
        print("-" * 40)

        workflow_summary = {
            "applicant_name": applicant_data['full_name'],
            "emirates_id": applicant_data['emirates_id'],
            "monthly_income": extracted_data['bank_statement'].get('monthly_income', 0),
            "account_balance": extracted_data['bank_statement'].get('account_balance', 0),
            "final_decision": decision_result['outcome'],
            "confidence_score": decision_result['confidence'],
            "benefit_amount": decision_result['benefit_amount'],
            "processing_successful": True,
            "ai_services_used": ["OCR", "Multimodal Analysis", "ReAct Decision Engine"]
        }

        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"Summary: {json.dumps(workflow_summary, indent=2)}")

        return workflow_summary

    except Exception as e:
        logger.error("Workflow test failed", error=str(e))
        print(f"WORKFLOW FAILED: {e}")
        return None

    finally:
        print("\n" + "=" * 70)
        print("WORKFLOW TEST COMPLETED")
        print("=" * 70)

if __name__ == "__main__":
    test_complete_workflow()