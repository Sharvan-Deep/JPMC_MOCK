"""
Abstract Base LLM Provider Interface for Task 6.
Enables pluggable AI classification models (Gemini, OpenAI, Mock, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict
from ai_service.schemas.classification import WASHClassificationResult
from ai_service.schemas.preprocessing import CleanedCSRData


class BaseLLMProvider(ABC):
    """Abstract interface for CSR WASH classification AI models."""

    @abstractmethod
    def classify_csr_data(
        self,
        cleaned_data: CleanedCSRData,
        cleaned_text_by_page: Dict[int, str],
    ) -> WASHClassificationResult:
        """
        Classifies preprocessed CSR data for genuine WASH relevance.

        Args:
            cleaned_data: Structured preprocessed CSR records and metadata.
            cleaned_text_by_page: Cleaned text organized by page number.

        Returns:
            WASHClassificationResult with classification, confidence, flags, and evidence.
        """
        pass
