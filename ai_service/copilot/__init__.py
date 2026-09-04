"""
Copilot module for Task 12: Next-Best-Action Recommendation Copilot.
"""

from ai_service.copilot.providers import (
    BaseCopilotProvider,
    GeminiCopilotProvider,
    MockCopilotProvider,
)
from ai_service.copilot.repository import RecommendationRepository
from ai_service.copilot.rules import RecommendationRulesEngine
from ai_service.copilot.service import CSRRecommendationService

__all__ = [
    "RecommendationRulesEngine",
    "RecommendationRepository",
    "BaseCopilotProvider",
    "MockCopilotProvider",
    "GeminiCopilotProvider",
    "CSRRecommendationService",
]
