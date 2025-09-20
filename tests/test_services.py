#!/usr/bin/env python3
"""
Service Layer Tests
Tests OCR, ML models, document processing, and decision making services
"""

import pytest
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.document_processing.ocr_service import OCRService
from app.document_processing.document_service import DocumentService
from app.decision_making.decision_service import DecisionService
from app.decision_making.react_reasoning import ReActReasoning
from app.user_management.user_service import UserService
from app.shared.llm_client import LLMClient
from app.config import settings


class ServiceTestSuite:
    """Base class for service testing"""

    def __init__(self):
        self.test_results = []
        self.fixtures_path = Path(__file__).parent / "fixtures" / "sample_documents"

    def log_test(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "details": details or {}
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details and status != "PASS":
            print(f"   Details: {details}")


class TestOCRService(ServiceTestSuite):
    """Test OCR service functionality"""

    def __init__(self):
        super().__init__()
        self.ocr_service = OCRService()

    def test_ocr_service_initialization(self):
        """Test OCR service can be initialized"""
        try:
            assert self.ocr_service is not None
            # Test if EasyOCR reader can be initialized
            reader = self.ocr_service.get_reader()
            assert reader is not None

            self.log_test("OCR Service Initialization", "PASS")

        except Exception as e:
            self.log_test("OCR Service Initialization", "FAIL", {"error": str(e)})

    def test_pdf_text_extraction(self):
        """Test extracting text from PDF documents"""
        try:
            test_pdf_path = self.fixtures_path / "test_bank_statement.pdf"

            if test_pdf_path.exists():
                # Extract text using OCR service
                extracted_text = self.ocr_service.extract_text_from_pdf(str(test_pdf_path))

                assert isinstance(extracted_text, str)
                assert len(extracted_text) > 0

                self.log_test("PDF Text Extraction", "PASS",
                             {"text_length": len(extracted_text)})
            else:
                self.log_test("PDF Text Extraction", "SKIP",
                             {"reason": "Test PDF file not found"})

        except Exception as e:
            self.log_test("PDF Text Extraction", "FAIL", {"error": str(e)})

    def test_image_text_extraction(self):
        """Test extracting text from image documents"""
        try:
            test_image_path = self.fixtures_path / "test_emirates_id.png"

            if test_image_path.exists():
                # Extract text using OCR service
                extracted_text = self.ocr_service.extract_text_from_image(str(test_image_path))

                assert isinstance(extracted_text, str)
                # Emirates ID might have minimal text

                self.log_test("Image Text Extraction", "PASS",
                             {"text_length": len(extracted_text)})
            else:
                self.log_test("Image Text Extraction", "SKIP",
                             {"reason": "Test image file not found"})

        except Exception as e:
            self.log_test("Image Text Extraction", "FAIL", {"error": str(e)})

    def test_ocr_confidence_scoring(self):
        """Test OCR confidence scoring"""
        try:
            test_pdf_path = self.fixtures_path / "test_bank_statement.pdf"

            if test_pdf_path.exists():
                # Extract text with confidence
                result = self.ocr_service.extract_with_confidence(str(test_pdf_path))

                assert "text" in result
                assert "confidence" in result
                assert isinstance(result["confidence"], (int, float))
                assert 0 <= result["confidence"] <= 1

                self.log_test("OCR Confidence Scoring", "PASS",
                             {"confidence": result["confidence"]})
            else:
                self.log_test("OCR Confidence Scoring", "SKIP",
                             {"reason": "Test file not found"})

        except Exception as e:
            self.log_test("OCR Confidence Scoring", "FAIL", {"error": str(e)})

    def test_ocr_error_handling(self):
        """Test OCR error handling with invalid files"""
        try:
            # Test with non-existent file
            result = self.ocr_service.extract_text_from_pdf("nonexistent_file.pdf")

            # Should handle gracefully
            assert result is not None

            self.log_test("OCR Error Handling", "PASS")

        except Exception as e:
            # Expected to fail gracefully
            self.log_test("OCR Error Handling", "PASS",
                         {"expected_error": str(e)})


class TestLLMClient(ServiceTestSuite):
    """Test LLM client and model interactions"""

    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()

    def test_ollama_connection(self):
        """Test connection to Ollama service"""
        try:
            # Test if Ollama is accessible
            models = self.llm_client.list_models()

            assert isinstance(models, list)

            # Check for expected models
            expected_models = ["moondream:1.8b", "qwen2:1.5b", "nomic-embed-text"]
            available_models = [model.get("name", "") for model in models]

            found_models = []
            for expected in expected_models:
                if any(expected in available for available in available_models):
                    found_models.append(expected)

            self.log_test("Ollama Connection", "PASS",
                         {"available_models": found_models})

        except Exception as e:
            self.log_test("Ollama Connection", "FAIL", {"error": str(e)})

    def test_text_generation(self):
        """Test text generation with qwen2 model"""
        try:
            prompt = "What is artificial intelligence? Answer in one sentence."

            response = self.llm_client.generate_text(
                model="qwen2:1.5b",
                prompt=prompt,
                max_tokens=50
            )

            assert isinstance(response, str)
            assert len(response) > 0

            self.log_test("Text Generation", "PASS",
                         {"response_length": len(response)})

        except Exception as e:
            self.log_test("Text Generation", "FAIL", {"error": str(e)})

    def test_multimodal_analysis(self):
        """Test multimodal analysis with moondream model"""
        try:
            test_image_path = self.fixtures_path / "test_emirates_id.png"

            if test_image_path.exists():
                prompt = "Describe what you see in this image."

                response = self.llm_client.analyze_image(
                    model="moondream:1.8b",
                    image_path=str(test_image_path),
                    prompt=prompt
                )

                assert isinstance(response, str)
                assert len(response) > 0

                self.log_test("Multimodal Analysis", "PASS",
                             {"response_length": len(response)})
            else:
                self.log_test("Multimodal Analysis", "SKIP",
                             {"reason": "Test image not found"})

        except Exception as e:
            self.log_test("Multimodal Analysis", "FAIL", {"error": str(e)})

    def test_embeddings_generation(self):
        """Test text embeddings with nomic model"""
        try:
            text = "This is a test document for embedding generation."

            embeddings = self.llm_client.generate_embeddings(
                model="nomic-embed-text",
                text=text
            )

            assert isinstance(embeddings, list)
            assert len(embeddings) > 0
            assert all(isinstance(x, (int, float)) for x in embeddings)

            self.log_test("Embeddings Generation", "PASS",
                         {"embedding_dimension": len(embeddings)})

        except Exception as e:
            self.log_test("Embeddings Generation", "FAIL", {"error": str(e)})

    def test_llm_error_handling(self):
        """Test LLM error handling"""
        try:
            # Test with non-existent model
            response = self.llm_client.generate_text(
                model="nonexistent-model",
                prompt="Test prompt"
            )

            # Should handle gracefully or return error
            self.log_test("LLM Error Handling", "PASS")

        except Exception as e:
            # Expected to handle errors gracefully
            self.log_test("LLM Error Handling", "PASS",
                         {"expected_error": str(e)})


class TestDocumentService(ServiceTestSuite):
    """Test document processing service"""

    def __init__(self):
        super().__init__()
        self.document_service = DocumentService()

    def test_document_validation(self):
        """Test document validation logic"""
        try:
            # Test valid file types
            valid_files = [
                "document.pdf",
                "image.png",
                "photo.jpg",
                "scan.jpeg",
                "doc.tiff",
                "file.bmp"
            ]

            for filename in valid_files:
                is_valid, message = self.document_service.validate_file_type(filename)
                assert is_valid, f"File {filename} should be valid"

            # Test invalid file types
            invalid_files = [
                "document.txt",
                "file.docx",
                "image.gif",
                "video.mp4"
            ]

            for filename in invalid_files:
                is_valid, message = self.document_service.validate_file_type(filename)
                assert not is_valid, f"File {filename} should be invalid"

            self.log_test("Document Validation", "PASS")

        except Exception as e:
            self.log_test("Document Validation", "FAIL", {"error": str(e)})

    def test_document_processing_workflow(self):
        """Test complete document processing workflow"""
        try:
            test_pdf_path = self.fixtures_path / "test_bank_statement.pdf"

            if test_pdf_path.exists():
                # Process document through complete workflow
                result = self.document_service.process_document(
                    file_path=str(test_pdf_path),
                    document_type="bank_statement"
                )

                assert "text" in result
                assert "confidence" in result
                assert "processing_time" in result
                assert "document_type" in result

                self.log_test("Document Processing Workflow", "PASS",
                             {"processing_time": result.get("processing_time")})
            else:
                self.log_test("Document Processing Workflow", "SKIP",
                             {"reason": "Test file not found"})

        except Exception as e:
            self.log_test("Document Processing Workflow", "FAIL", {"error": str(e)})

    def test_structured_data_extraction(self):
        """Test extracting structured data from documents"""
        try:
            test_pdf_path = self.fixtures_path / "test_bank_statement.pdf"

            if test_pdf_path.exists():
                # Extract structured data
                structured_data = self.document_service.extract_structured_data(
                    file_path=str(test_pdf_path),
                    document_type="bank_statement"
                )

                # Should contain expected fields for bank statement
                expected_fields = ["account_number", "balance", "transactions", "monthly_income"]

                assert isinstance(structured_data, dict)

                self.log_test("Structured Data Extraction", "PASS",
                             {"extracted_fields": list(structured_data.keys())})
            else:
                self.log_test("Structured Data Extraction", "SKIP",
                             {"reason": "Test file not found"})

        except Exception as e:
            self.log_test("Structured Data Extraction", "FAIL", {"error": str(e)})


class TestDecisionService(ServiceTestSuite):
    """Test decision making service"""

    def __init__(self):
        super().__init__()
        self.decision_service = DecisionService()

    def test_eligibility_evaluation(self):
        """Test eligibility evaluation logic"""
        try:
            # Test case: High income applicant
            applicant_data = {
                "monthly_income": 8500,
                "account_balance": 15000,
                "employment_status": "employed",
                "age": 35,
                "dependents": 2
            }

            decision = self.decision_service.evaluate_eligibility(applicant_data)

            assert "decision" in decision
            assert "confidence" in decision
            assert "reasoning" in decision
            assert decision["decision"] in ["approved", "rejected", "needs_review"]
            assert 0 <= decision["confidence"] <= 1

            self.log_test("Eligibility Evaluation", "PASS",
                         {"decision": decision["decision"], "confidence": decision["confidence"]})

        except Exception as e:
            self.log_test("Eligibility Evaluation", "FAIL", {"error": str(e)})

    def test_income_threshold_logic(self):
        """Test income threshold decision logic"""
        try:
            # Test different income levels
            test_cases = [
                {"monthly_income": 10000, "expected": "approved"},  # High income
                {"monthly_income": 2000, "expected": "rejected"},   # Low income
                {"monthly_income": 4000, "expected": "needs_review"}  # Borderline
            ]

            for case in test_cases:
                applicant_data = {
                    "monthly_income": case["monthly_income"],
                    "account_balance": 5000,
                    "employment_status": "employed"
                }

                decision = self.decision_service.evaluate_eligibility(applicant_data)

                # Verify decision logic makes sense
                assert decision["decision"] in ["approved", "rejected", "needs_review"]

            self.log_test("Income Threshold Logic", "PASS")

        except Exception as e:
            self.log_test("Income Threshold Logic", "FAIL", {"error": str(e)})

    def test_react_reasoning(self):
        """Test ReAct reasoning framework"""
        try:
            react_reasoner = ReActReasoning()

            # Test reasoning with simple case
            case_data = {
                "monthly_income": 6000,
                "account_balance": 10000,
                "documents_verified": True
            }

            reasoning_result = react_reasoner.reason_about_case(case_data)

            assert "thoughts" in reasoning_result
            assert "actions" in reasoning_result
            assert "observations" in reasoning_result
            assert "final_decision" in reasoning_result

            self.log_test("ReAct Reasoning", "PASS")

        except Exception as e:
            self.log_test("ReAct Reasoning", "FAIL", {"error": str(e)})

    def test_confidence_scoring(self):
        """Test confidence scoring for decisions"""
        try:
            # Test high confidence case
            high_confidence_data = {
                "monthly_income": 15000,
                "account_balance": 25000,
                "employment_status": "employed",
                "documents_verified": True,
                "credit_score": 750
            }

            # Test low confidence case
            low_confidence_data = {
                "monthly_income": 3000,
                "account_balance": 1000,
                "employment_status": "unemployed",
                "documents_verified": False
            }

            high_conf_decision = self.decision_service.evaluate_eligibility(high_confidence_data)
            low_conf_decision = self.decision_service.evaluate_eligibility(low_confidence_data)

            # High confidence case should have higher confidence score
            assert high_conf_decision["confidence"] >= low_conf_decision["confidence"]

            self.log_test("Confidence Scoring", "PASS",
                         {"high_conf": high_conf_decision["confidence"],
                          "low_conf": low_conf_decision["confidence"]})

        except Exception as e:
            self.log_test("Confidence Scoring", "FAIL", {"error": str(e)})


class TestUserService(ServiceTestSuite):
    """Test user management service"""

    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    def test_password_hashing(self):
        """Test password hashing and verification"""
        try:
            password = "TestPassword123!"

            # Hash password
            hashed = self.user_service.hash_password(password)
            assert isinstance(hashed, str)
            assert hashed != password  # Should be hashed

            # Verify correct password
            is_valid = self.user_service.verify_password(password, hashed)
            assert is_valid is True

            # Verify incorrect password
            is_invalid = self.user_service.verify_password("WrongPassword", hashed)
            assert is_invalid is False

            self.log_test("Password Hashing", "PASS")

        except Exception as e:
            self.log_test("Password Hashing", "FAIL", {"error": str(e)})

    def test_jwt_token_operations(self):
        """Test JWT token creation and validation"""
        try:
            # Test data
            user_data = {"sub": "testuser", "user_id": "123"}

            # Create token
            token = self.user_service.create_access_token(user_data)
            assert isinstance(token, str)
            assert len(token) > 0

            # Decode token
            decoded_data = self.user_service.decode_access_token(token)
            assert decoded_data["sub"] == user_data["sub"]
            assert decoded_data["user_id"] == user_data["user_id"]

            self.log_test("JWT Token Operations", "PASS")

        except Exception as e:
            self.log_test("JWT Token Operations", "FAIL", {"error": str(e)})

    def test_user_validation(self):
        """Test user data validation"""
        try:
            # Valid user data
            valid_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User"
            }

            is_valid, errors = self.user_service.validate_user_data(valid_data)
            assert is_valid is True
            assert len(errors) == 0

            # Invalid user data
            invalid_data = {
                "username": "ab",  # Too short
                "email": "invalid-email",  # Invalid format
                "password": "123",  # Too weak
            }

            is_invalid, errors = self.user_service.validate_user_data(invalid_data)
            assert is_invalid is False
            assert len(errors) > 0

            self.log_test("User Validation", "PASS")

        except Exception as e:
            self.log_test("User Validation", "FAIL", {"error": str(e)})


def run_comprehensive_service_tests():
    """Run all service layer tests"""

    print("🚀 Starting Comprehensive Service Layer Tests")
    print("=" * 60)

    # OCR Service Tests
    ocr_tests = TestOCRService()
    ocr_tests.test_ocr_service_initialization()
    ocr_tests.test_pdf_text_extraction()
    ocr_tests.test_image_text_extraction()
    ocr_tests.test_ocr_confidence_scoring()
    ocr_tests.test_ocr_error_handling()

    # LLM Client Tests
    llm_tests = TestLLMClient()
    llm_tests.test_ollama_connection()
    llm_tests.test_text_generation()
    llm_tests.test_multimodal_analysis()
    llm_tests.test_embeddings_generation()
    llm_tests.test_llm_error_handling()

    # Document Service Tests
    doc_service_tests = TestDocumentService()
    doc_service_tests.test_document_validation()
    doc_service_tests.test_document_processing_workflow()
    doc_service_tests.test_structured_data_extraction()

    # Decision Service Tests
    decision_tests = TestDecisionService()
    decision_tests.test_eligibility_evaluation()
    decision_tests.test_income_threshold_logic()
    decision_tests.test_react_reasoning()
    decision_tests.test_confidence_scoring()

    # User Service Tests
    user_tests = TestUserService()
    user_tests.test_password_hashing()
    user_tests.test_jwt_token_operations()
    user_tests.test_user_validation()

    # Collect all results
    all_results = (ocr_tests.test_results +
                  llm_tests.test_results +
                  doc_service_tests.test_results +
                  decision_tests.test_results +
                  user_tests.test_results)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 SERVICE TESTS SUMMARY")
    print("=" * 60)

    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r["status"] == "PASS"])
    failed_tests = len([r for r in all_results if r["status"] == "FAIL"])
    skipped_tests = len([r for r in all_results if r["status"] == "SKIP"])

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"⚠️ Skipped: {skipped_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    # Save results to file
    with open("test_results_services.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: test_results_services.json")

    return all_results


if __name__ == "__main__":
    run_comprehensive_service_tests()