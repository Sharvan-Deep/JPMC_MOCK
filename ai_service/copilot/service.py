"""
Next-Best-Action Recommendation & Copilot Service for Task 12.

Coordinates:
- RecommendationRulesEngine (deterministic mapping to controlled actions)
- RecommendationRepository (append-only auditable history)
- CSRSemanticSearchService (Task 7 ChromaDB semantic retrieval for Q&A grounding)
- BaseCopilotProvider / MockCopilotProvider / GeminiCopilotProvider (conversational assistant)
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional

from ai_service.copilot.providers import (
    BaseCopilotProvider,
    GeminiCopilotProvider,
    MockCopilotProvider,
)
from ai_service.copilot.repository import RecommendationRepository
from ai_service.copilot.rules import RecommendationRulesEngine
from ai_service.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    RecommendationAction,
    RecommendationHistoryResponse,
    RecommendationRequest,
    RecommendationResult,
)
from ai_service.vector_store.retriever import CSRSemanticSearchService


class CSRRecommendationService:
    """Core coordinator service for Task 12 recommendations and Copilot chat."""

    def __init__(
        self,
        repository: Optional[RecommendationRepository] = None,
        retriever: Optional[CSRSemanticSearchService] = None,
        copilot_provider: Optional[BaseCopilotProvider] = None,
    ):
        self.repository = repository or RecommendationRepository()
        self.retriever = retriever or CSRSemanticSearchService()
        if copilot_provider:
            self.copilot_provider = copilot_provider
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            self.copilot_provider = GeminiCopilotProvider(api_key=api_key) if api_key else MockCopilotProvider()

    def generate_recommendation(self, request: RecommendationRequest) -> RecommendationResult:
        """
        Generates an evidence-grounded next-best action recommendation using deterministic rules,
        stores the result in the append-only repository, and returns the result.
        """
        (
            action,
            confidence,
            reasons,
            positive_factors,
            limiting_factors,
            missing_information,
            risks,
            next_steps,
        ) = RecommendationRulesEngine.evaluate(request)

        result = RecommendationResult(
            company=request.company,
            recommended_action=action,
            confidence=round(confidence, 2),
            reasons=reasons,
            supporting_evidence=list(request.evidence),
            positive_factors=positive_factors,
            limiting_factors=limiting_factors,
            missing_information=missing_information,
            risks=risks,
            next_steps=next_steps,
            is_advisory=True,
            scoring_version="v1",
            recommendation_version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "lead_score": request.lead_score,
                "priority_band": request.priority_band,
                "freshness_status": request.freshness_status,
                "wash_direction": request.wash_direction,
                "wash_classification": request.wash_classification,
                "has_multi_year_commitment": request.has_multi_year_commitment,
                "evidence_coverage": request.evidence_coverage,
                "wash_spend_crore": request.wash_spend_crore,
                "financial_year": request.financial_year,
            },
        )

        return self.repository.save(result)

    def get_latest_recommendation(self, company: str) -> Optional[RecommendationResult]:
        """Fetches the latest recommendation record for a company."""
        return self.repository.get_latest(company)

    def get_company_history(self, company: str) -> RecommendationHistoryResponse:
        """Fetches complete recommendation history for a company."""
        return self.repository.get_history(company)

    def chat_with_copilot(self, request: CopilotChatRequest) -> CopilotChatResponse:
        """
        Interactive Q&A assistant:
        1. Fetches latest recommendation record for the company.
        2. Queries Task 7 ChromaDB semantic search for top chunks relating to question & company.
        3. Answers staff question using provider with strict evidence grounding.
        """
        latest_rec = self.repository.get_latest(request.company)

        # Retrieve relevant chunks from ChromaDB
        retrieved_contexts: List[str] = []
        try:
            filters = {"company_name": request.company} if request.company else None
            search_res = self.retriever.search(
                query=f"{request.company} {request.question}",
                filters=filters,
                top_k=3,
            )
            for item in search_res.results:
                retrieved_contexts.append(item.text)
        except Exception:
            pass

        return self.copilot_provider.answer_question(
            request=request,
            latest_recommendation=latest_rec,
            retrieved_contexts=retrieved_contexts,
        )
