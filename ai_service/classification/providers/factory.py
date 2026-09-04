"""
Provider Factory for Task 6 AI/NLP Classification.
Instantiates configured LLM providers (gemini, mock, etc.) based on environment settings.
"""

from typing import Optional
from ai_service.classification.providers.base import BaseLLMProvider
from ai_service.classification.providers.gemini_provider import GeminiProvider
from ai_service.classification.providers.mock_provider import MockRuleBasedProvider
from ai_service.config import Settings, get_settings


def get_llm_provider(settings: Optional[Settings] = None) -> BaseLLMProvider:
    """Returns the configured LLM provider instance."""
    cfg = settings or get_settings()
    provider_name = (cfg.LLM_PROVIDER or "gemini").lower().strip()

    if provider_name in ["mock", "testing", "rulebased"]:
        return MockRuleBasedProvider()

    if provider_name in ["gemini", "google"]:
        return GeminiProvider()

    # Default to mock provider for unknown/unconfigured providers
    return MockRuleBasedProvider(model_name=f"fallback-{provider_name}")
