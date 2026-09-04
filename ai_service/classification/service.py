"""
CSR WASH Classification Orchestration Service for Task 6.
Consumes Task 5 preprocessed data and executes AI/NLP classification.
Enforces pipeline ordering: strictly consumes cleaned data, never raw PDFs directly.
"""

import time
from typing import Any, Dict, Optional, Union

from ai_service.classification.providers.base import BaseLLMProvider
from ai_service.classification.providers.factory import get_llm_provider
from ai_service.logging_config import logger
from ai_service.schemas.classification import (
    WASHClassificationEnum,
    WASHClassificationResult,
)
from ai_service.schemas.preprocessing import CSRPreprocessingResult


class CSRClassificationService:
    """Orchestrator for classifying preprocessed CSR data for WASH relevance."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def classify_preprocessed_document(
        self,
        preprocessed_data: Union[CSRPreprocessingResult, Dict[str, Any]],
    ) -> WASHClassificationResult:
        """
        Classifies preprocessed CSR data to determine genuine community WASH relevance.

        Strictly guarantees:
        1. Consumes Task 5 cleaned data.
        2. Context-aware distinction: community drinking water/sanitation vs factory ETP/industrial water.
        3. Returns evidence-first output with verbatim snippets and page references.
        4. Calculates calibrated confidence (0.0 to 1.0).
        5. Does NOT calculate donor capacity, lead score, or outreach ranking (reserved for later tasks).
        """
        start_time = time.time()

        # Parse dict into CSRPreprocessingResult if needed
        if isinstance(preprocessed_data, dict):
            try:
                prep_obj = CSRPreprocessingResult(**preprocessed_data)
            except Exception as e:
                err_msg = f"Failed to parse input into CSRPreprocessingResult: {str(e)}"
                logger.error(err_msg)
                return WASHClassificationResult(
                    classification=WASHClassificationEnum.INSUFFICIENT_EVIDENCE.value,
                    confidence=0.0,
                    water_relevance=False,
                    sanitation_relevance=False,
                    hygiene_relevance=False,
                    reasoning=err_msg,
                    evidence=[],
                    evidence_pages=[],
                    model_used="error-handler",
                    document_metadata=preprocessed_data.get("document_metadata", {}),
                    processing_time_seconds=round(time.time() - start_time, 4),
                    errors=[err_msg],
                )
        else:
            prep_obj = preprocessed_data

        doc_meta = prep_obj.document_metadata or {}
        cleaned_data = prep_obj.cleaned_data
        cleaned_text = prep_obj.cleaned_text_by_page or {}

        # Invoke provider
        result = self.provider.classify_csr_data(
            cleaned_data=cleaned_data,
            cleaned_text_by_page=cleaned_text,
        )

        result.document_metadata = doc_meta
        result.processing_time_seconds = round(time.time() - start_time, 4)
        return result
