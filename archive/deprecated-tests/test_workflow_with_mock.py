#!/usr/bin/env python3
"""
Test complete workflow using mock data to simulate a successful end-to-end process
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

def test_workflow_with_mock_data():
    """Test complete workflow using mock OCR data to simulate proper extraction"""

    print("=" * 70)
    print("COMPLETE AI WORKFLOW TEST (WITH MOCK DATA)")
    print("=" * 70)

    # Initialize services
    ocr_service = OCRService()
    multimodal_service = MultimodalService()
    react_engine = ReActDecisionEngine()

    try:
        # Step 1: Use Mock OCR Data
        print("\n1. MOCK OCR DATA EXTRACTION")
        print("-" * 40)

        # Get mock Emirates ID text
        emirates_ocr = ocr_service._mock_ocr_extraction("/fake/emirates_id.jpg")
        print(f"Mock Emirates ID data - Length: {len(emirates_ocr.extracted_text)}")
        print(f"Emirates ID Text: {emirates_ocr.extracted_text[:200]}...")

        # Get mock Bank Statement text
        bank_ocr = ocr_service._mock_ocr_extraction("/fake/bank_statement.pdf")
        print(f"Mock Bank Statement data - Length: {len(bank_ocr.extracted_text)}")
        print(f"Bank Statement Text: {bank_ocr.extracted_text[:200]}...")

        # Step 2: Multimodal AI Analysis
        print("\n2. MULTIMODAL AI ANALYSIS WITH MOCK DATA")
        print("-" * 40)

        # Analyze Emirates ID
        emirates_analysis = multimodal_service.analyze_document(
            text_content=emirates_ocr.extracted_text,
            document_type="emirates_id",
            file_path="/fake/emirates_id.jpg"
        )
        print(f"Emirates ID Analysis - Success: {emirates_analysis.get('success')}")
        print(f"Extracted data: {json.dumps(emirates_analysis.get('extracted_data', {}), indent=2)}")

        # Analyze Bank Statement
        bank_analysis = multimodal_service.analyze_document(
            text_content=bank_ocr.extracted_text,
            document_type="bank_statement",
            file_path="/fake/bank_statement.pdf"
        )
        print(f"Bank Statement Analysis - Success: {bank_analysis.get('success')}")
        print(f"Extracted data: {json.dumps(bank_analysis.get('extracted_data', {}), indent=2)}")

        # Step 3: Prepare Application Data
        print("\n3. PREPARING APPLICATION DATA")
        print("-" * 40)

        applicant_data = {
            'full_name': emirates_analysis.get('extracted_data', {}).get('full_name', 'Muaaz Bin Saeed'),
            'emirates_id': emirates_analysis.get('extracted_data', {}).get('emirates_id_number', '784-1995-1234567-8'),
            'phone': '+971501234567',
            'email': 'test@example.com',
            'application_id': 'test_app_456'
        }

        extracted_data = {
            'emirates_id': emirates_analysis.get('extracted_data', {}),
            'bank_statement': bank_analysis.get('extracted_data', {})
        }

        application_data = {
            "application_id": "test_app_456",
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

        print(f"\nDETAILED REASONING:")
        print(f"  Income Analysis: {reasoning.get('income_analysis', 'N/A')}")
        print(f"  Document Verification: {reasoning.get('document_verification', 'N/A')}")
        print(f"  Risk Assessment: {reasoning.get('risk_assessment', 'N/A')}")

        print(f"\nREACT REASONING TRACE:")
        print(f"  Total Steps: {reasoning_trace.total_steps}")
        print(f"  Processing Time: {reasoning_trace.processing_time_ms}ms")
        print(f"  Model Used: {reasoning_trace.model_used}")

        # Show reasoning steps
        print(f"\nREASONING STEPS:")
        for i, step in enumerate(reasoning_trace.reasoning_steps, 1):
            print(f"  {i}. [{step.step_type.upper()}] (conf: {step.confidence:.2f}) {step.content}")

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
            "ai_services_used": ["Mock OCR", "Intelligent Text Extraction", "ReAct Decision Engine"],
            "eligibility_factors": reasoning.get('eligibility_factors', {}),
            "reasoning_steps": len(reasoning_trace.reasoning_steps)
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
    test_workflow_with_mock_data()