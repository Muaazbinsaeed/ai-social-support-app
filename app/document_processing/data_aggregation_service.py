"""
Data Aggregation Service for Social Security AI System
Combines all 5 data sources for comprehensive decision making
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

from app.document_processing.document_models import Document, DocumentProcessingLog
from app.application_flow.application_models import Application
from app.shared.logging_config import get_logger
from app.shared.exceptions import DataProcessingError

logger = get_logger(__name__)


class DataAggregationService:
    """Service for aggregating all data sources for decision making"""

    def __init__(self):
        pass

    def aggregate_application_data(self, db: Session, application_id: str) -> Dict[str, Any]:
        """Aggregate all 5 data sources for an application"""
        try:
            start_time = time.time()

            logger.info("Starting data aggregation", application_id=application_id)

            # Get application data (Source 1)
            application_data = self._get_application_form_data(db, application_id)

            # Get documents for this application
            documents = db.query(Document).filter(
                Document.application_id == application_id
            ).all()

            # Initialize data sources
            aggregated_data = {
                "application_id": application_id,
                "aggregation_timestamp": datetime.utcnow().isoformat(),
                "data_sources": {
                    "1_application_form": application_data,
                    "2_ocr_emirates_id": {},
                    "3_ocr_bank_statement": {},
                    "4_multimodal_emirates_id": {},
                    "5_multimodal_bank_statement": {}
                },
                "data_quality": {
                    "sources_available": 1,  # At minimum we have application form
                    "total_confidence": 0.0,
                    "missing_sources": [],
                    "quality_score": 0.0
                },
                "processing_metadata": {
                    "aggregation_time": 0.0,
                    "documents_processed": len(documents),
                    "processing_errors": []
                }
            }

            # Process each document
            for document in documents:
                doc_type = document.document_type

                # Get OCR data (Sources 2 & 3)
                ocr_data = self._get_ocr_data(db, document)
                if ocr_data:
                    if doc_type == "emirates_id":
                        aggregated_data["data_sources"]["2_ocr_emirates_id"] = ocr_data
                        aggregated_data["data_quality"]["sources_available"] += 1
                    elif doc_type == "bank_statement":
                        aggregated_data["data_sources"]["3_ocr_bank_statement"] = ocr_data
                        aggregated_data["data_quality"]["sources_available"] += 1
                else:
                    aggregated_data["data_quality"]["missing_sources"].append(f"ocr_{doc_type}")

                # Get multimodal analysis data (Sources 4 & 5)
                multimodal_data = self._get_multimodal_data(db, document)
                if multimodal_data:
                    if doc_type == "emirates_id":
                        aggregated_data["data_sources"]["4_multimodal_emirates_id"] = multimodal_data
                        aggregated_data["data_quality"]["sources_available"] += 1
                    elif doc_type == "bank_statement":
                        aggregated_data["data_sources"]["5_multimodal_bank_statement"] = multimodal_data
                        aggregated_data["data_quality"]["sources_available"] += 1
                else:
                    aggregated_data["data_quality"]["missing_sources"].append(f"multimodal_{doc_type}")

            # Create unified data view
            unified_data = self._create_unified_data_view(aggregated_data)
            aggregated_data["unified_data"] = unified_data

            # Calculate quality metrics
            self._calculate_quality_metrics(aggregated_data)

            processing_time = time.time() - start_time
            aggregated_data["processing_metadata"]["aggregation_time"] = processing_time

            logger.info(
                "Data aggregation completed",
                application_id=application_id,
                sources_available=aggregated_data["data_quality"]["sources_available"],
                quality_score=aggregated_data["data_quality"]["quality_score"],
                processing_time=processing_time
            )

            return aggregated_data

        except Exception as e:
            logger.error("Data aggregation failed", error=str(e), application_id=application_id)
            raise DataProcessingError(f"Data aggregation failed: {str(e)}", "AGGREGATION_ERROR")

    def _get_application_form_data(self, db: Session, application_id: str) -> Dict[str, Any]:
        """Get application form data (Source 1)"""
        try:
            application = db.query(Application).filter(
                Application.id == application_id
            ).first()

            if not application:
                raise DataProcessingError(f"Application {application_id} not found", "APPLICATION_NOT_FOUND")

            return {
                "source_type": "application_form",
                "confidence": 1.0,  # Form data is always reliable
                "data": {
                    "full_name": application.full_name,
                    "emirates_id": application.emirates_id,
                    "phone": application.phone,
                    "email": application.email,
                    "submission_date": application.created_at.isoformat() if application.created_at else None,
                    "current_status": application.status
                },
                "metadata": {
                    "source": "user_input",
                    "validation": "form_validated"
                }
            }

        except Exception as e:
            logger.error("Failed to get application form data", error=str(e))
            return {
                "source_type": "application_form",
                "confidence": 0.0,
                "data": {},
                "error": str(e)
            }

    def _get_ocr_data(self, db: Session, document: Document) -> Optional[Dict[str, Any]]:
        """Get OCR extraction data (Sources 2 & 3)"""
        try:
            if not document.extracted_text:
                return None

            return {
                "source_type": f"ocr_{document.document_type}",
                "confidence": float(document.ocr_confidence) if document.ocr_confidence else 0.0,
                "data": {
                    "extracted_text": document.extracted_text,
                    "document_type": document.document_type,
                    "processing_time_ms": document.ocr_processing_time_ms,
                    "text_length": len(document.extracted_text) if document.extracted_text else 0
                },
                "metadata": {
                    "document_id": str(document.id),
                    "file_name": document.original_filename,
                    "processing_method": "tesseract_ocr",
                    "processed_at": document.processed_at.isoformat() if document.processed_at else None
                }
            }

        except Exception as e:
            logger.error("Failed to get OCR data", error=str(e), document_id=str(document.id))
            return None

    def _get_multimodal_data(self, db: Session, document: Document) -> Optional[Dict[str, Any]]:
        """Get multimodal analysis data (Sources 4 & 5)"""
        try:
            # Get the latest multimodal analysis result from processing logs
            multimodal_log = db.query(DocumentProcessingLog).filter(
                DocumentProcessingLog.document_id == document.id,
                DocumentProcessingLog.processing_step == "multimodal_analysis",
                DocumentProcessingLog.step_status == "completed"
            ).order_by(DocumentProcessingLog.completed_at.desc()).first()

            if not multimodal_log or not multimodal_log.step_result:
                return None

            return {
                "source_type": f"multimodal_{document.document_type}",
                "confidence": float(multimodal_log.confidence_score) if multimodal_log.confidence_score else 0.0,
                "data": multimodal_log.step_result,
                "metadata": {
                    "document_id": str(document.id),
                    "file_name": document.original_filename,
                    "processing_method": "ollama_multimodal",
                    "processed_at": multimodal_log.completed_at.isoformat() if multimodal_log.completed_at else None,
                    "processing_time_ms": multimodal_log.processing_time_ms
                }
            }

        except Exception as e:
            logger.error("Failed to get multimodal data", error=str(e), document_id=str(document.id))
            return None

    def _create_unified_data_view(self, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a unified view combining all data sources"""
        try:
            unified = {
                "personal_information": {},
                "financial_information": {},
                "document_verification": {},
                "data_consistency": {},
                "decision_factors": {}
            }

            data_sources = aggregated_data["data_sources"]

            # Personal Information (from application form and Emirates ID)
            app_data = data_sources.get("1_application_form", {}).get("data", {})
            emirates_ocr = data_sources.get("2_ocr_emirates_id", {}).get("data", {})
            emirates_ai = data_sources.get("4_multimodal_emirates_id", {}).get("data", {})

            unified["personal_information"] = {
                "name_from_application": app_data.get("full_name"),
                "name_from_emirates_id": emirates_ai.get("full_name") if emirates_ai else None,
                "emirates_id_from_application": app_data.get("emirates_id"),
                "emirates_id_from_document": emirates_ai.get("emirates_id_number") if emirates_ai else None,
                "nationality": emirates_ai.get("nationality") if emirates_ai else None,
                "date_of_birth": emirates_ai.get("date_of_birth") if emirates_ai else None,
                "gender": emirates_ai.get("gender") if emirates_ai else None,
                "phone": app_data.get("phone"),
                "email": app_data.get("email")
            }

            # Financial Information (from bank statement)
            bank_ocr = data_sources.get("3_ocr_bank_statement", {}).get("data", {})
            bank_ai = data_sources.get("5_multimodal_bank_statement", {}).get("data", {})

            unified["financial_information"] = {
                "monthly_income": bank_ai.get("monthly_income") if bank_ai else None,
                "account_balance": bank_ai.get("account_balance") if bank_ai else None,
                "account_number": bank_ai.get("account_number") if bank_ai else None,
                "account_holder_name": bank_ai.get("account_holder_name") if bank_ai else None,
                "bank_name": bank_ai.get("bank_name") if bank_ai else None,
                "statement_period": bank_ai.get("statement_period") if bank_ai else None,
                "currency": bank_ai.get("currency", "AED") if bank_ai else "AED",
                "transactions_analyzed": bank_ai.get("transactions_analyzed") if bank_ai else 0,
                "salary_deposits_found": bank_ai.get("salary_deposits_found") if bank_ai else 0
            }

            # Document Verification
            unified["document_verification"] = {
                "emirates_id_confidence": data_sources.get("4_multimodal_emirates_id", {}).get("confidence", 0),
                "bank_statement_confidence": data_sources.get("5_multimodal_bank_statement", {}).get("confidence", 0),
                "ocr_emirates_confidence": data_sources.get("2_ocr_emirates_id", {}).get("confidence", 0),
                "ocr_bank_confidence": data_sources.get("3_ocr_bank_statement", {}).get("confidence", 0),
                "documents_provided": len([k for k in data_sources.keys() if data_sources[k]]),
                "verification_status": "verified" if all(
                    data_sources.get(k, {}).get("confidence", 0) > 0.5
                    for k in ["2_ocr_emirates_id", "3_ocr_bank_statement"]
                ) else "partial"
            }

            # Data Consistency Checks
            name_matches = self._check_name_consistency(
                app_data.get("full_name"),
                emirates_ai.get("full_name") if emirates_ai else None,
                bank_ai.get("account_holder_name") if bank_ai else None
            )

            emirates_id_matches = self._check_emirates_id_consistency(
                app_data.get("emirates_id"),
                emirates_ai.get("emirates_id_number") if emirates_ai else None
            )

            unified["data_consistency"] = {
                "name_consistency": name_matches,
                "emirates_id_consistency": emirates_id_matches,
                "overall_consistency": (name_matches + emirates_id_matches) / 2
            }

            # Decision Factors
            monthly_income = unified["financial_information"]["monthly_income"] or 0
            account_balance = unified["financial_information"]["account_balance"] or 0

            unified["decision_factors"] = {
                "income_threshold_met": monthly_income >= 4000,  # AED threshold
                "balance_threshold_met": account_balance >= 1500,  # AED threshold
                "identity_verified": unified["data_consistency"]["overall_consistency"] > 0.7,
                "documents_complete": len([k for k in data_sources.keys() if data_sources[k]]) >= 3,
                "recommendation": self._generate_preliminary_recommendation(
                    monthly_income, account_balance, unified["data_consistency"]["overall_consistency"]
                )
            }

            return unified

        except Exception as e:
            logger.error("Failed to create unified data view", error=str(e))
            return {"error": str(e)}

    def _check_name_consistency(self, app_name: str, id_name: str, bank_name: str) -> float:
        """Check consistency between names from different sources"""
        try:
            if not app_name:
                return 0.0

            names = [n for n in [app_name, id_name, bank_name] if n]
            if len(names) < 2:
                return 0.5  # Only one source available

            # Normalize names (uppercase, remove extra spaces)
            normalized_names = [name.upper().strip() for name in names]

            # Simple consistency check - more sophisticated matching could be added
            matches = 0
            comparisons = 0

            for i in range(len(normalized_names)):
                for j in range(i + 1, len(normalized_names)):
                    comparisons += 1
                    # Check if names are similar (allow for minor differences)
                    similarity = self._calculate_string_similarity(normalized_names[i], normalized_names[j])
                    if similarity > 0.7:
                        matches += 1

            return matches / comparisons if comparisons > 0 else 0.0

        except Exception as e:
            logger.warning("Name consistency check failed", error=str(e))
            return 0.0

    def _check_emirates_id_consistency(self, app_id: str, doc_id: str) -> float:
        """Check consistency between Emirates IDs from different sources"""
        try:
            if not app_id:
                return 0.0

            if not doc_id:
                return 0.5  # Only application source available

            # Normalize IDs (remove spaces, dashes)
            app_normalized = app_id.replace("-", "").replace(" ", "")
            doc_normalized = doc_id.replace("-", "").replace(" ", "")

            # Check exact match
            if app_normalized == doc_normalized:
                return 1.0

            # Check partial match (allowing for OCR errors in digits)
            similarity = self._calculate_string_similarity(app_normalized, doc_normalized)
            return similarity

        except Exception as e:
            logger.warning("Emirates ID consistency check failed", error=str(e))
            return 0.0

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        try:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, str1, str2).ratio()
        except Exception:
            # Fallback to simple character match
            if str1 == str2:
                return 1.0
            return 0.0

    def _generate_preliminary_recommendation(self, income: float, balance: float, consistency: float) -> str:
        """Generate preliminary recommendation based on key factors"""
        try:
            if income >= 4000 and balance >= 1500 and consistency > 0.7:
                return "approve"
            elif income < 2000 or balance < 500 or consistency < 0.3:
                return "reject"
            else:
                return "review"
        except Exception:
            return "review"

    def _calculate_quality_metrics(self, aggregated_data: Dict[str, Any]) -> None:
        """Calculate overall data quality metrics"""
        try:
            quality = aggregated_data["data_quality"]
            sources = aggregated_data["data_sources"]

            # Calculate total confidence
            confidences = []
            for source_data in sources.values():
                if source_data and isinstance(source_data, dict):
                    conf = source_data.get("confidence", 0.0)
                    if conf > 0:
                        confidences.append(conf)

            quality["total_confidence"] = sum(confidences) / len(confidences) if confidences else 0.0

            # Calculate quality score (0-1)
            sources_weight = quality["sources_available"] / 5.0  # Max 5 sources
            confidence_weight = quality["total_confidence"]
            consistency_weight = aggregated_data.get("unified_data", {}).get("data_consistency", {}).get("overall_consistency", 0.0)

            quality["quality_score"] = (sources_weight * 0.4 + confidence_weight * 0.4 + consistency_weight * 0.2)

            logger.debug(
                "Quality metrics calculated",
                sources_available=quality["sources_available"],
                total_confidence=quality["total_confidence"],
                quality_score=quality["quality_score"]
            )

        except Exception as e:
            logger.error("Failed to calculate quality metrics", error=str(e))
            aggregated_data["data_quality"]["quality_score"] = 0.0

    def prepare_decision_input(self, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare formatted input for the decision engine"""
        try:
            unified = aggregated_data.get("unified_data", {})

            decision_input = {
                "application_id": aggregated_data["application_id"],
                "personal_info": unified.get("personal_information", {}),
                "financial_info": unified.get("financial_information", {}),
                "verification_info": unified.get("document_verification", {}),
                "consistency_info": unified.get("data_consistency", {}),
                "preliminary_factors": unified.get("decision_factors", {}),
                "data_quality": aggregated_data.get("data_quality", {}),
                "processing_metadata": aggregated_data.get("processing_metadata", {}),
                "timestamp": aggregated_data["aggregation_timestamp"],
                "sources_summary": {
                    "total_sources": aggregated_data["data_quality"]["sources_available"],
                    "missing_sources": aggregated_data["data_quality"]["missing_sources"],
                    "average_confidence": aggregated_data["data_quality"]["total_confidence"],
                    "quality_score": aggregated_data["data_quality"]["quality_score"]
                }
            }

            logger.info(
                "Decision input prepared",
                application_id=aggregated_data["application_id"],
                total_sources=decision_input["sources_summary"]["total_sources"],
                quality_score=decision_input["sources_summary"]["quality_score"]
            )

            return decision_input

        except Exception as e:
            logger.error("Failed to prepare decision input", error=str(e))
            raise DataProcessingError(f"Decision input preparation failed: {str(e)}", "DECISION_INPUT_ERROR")