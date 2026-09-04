"""
FastAPI Routes for Task 12: Next-Best-Action Recommendation Copilot.

Endpoints:
- POST /api/v1/copilot/recommend
- GET  /api/v1/copilot/recommendations/{company}
- POST /api/v1/copilot/chat
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path
from ai_service.copilot.service import CSRRecommendationService
from ai_service.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    RecommendationHistoryResponse,
    RecommendationRequest,
    RecommendationResult,
)

router = APIRouter(prefix="/api/v1/copilot", tags=["Recommendation Copilot"])

_copilot_service = CSRRecommendationService()


def get_copilot_service() -> CSRRecommendationService:
    return _copilot_service


@router.post(
    "/recommend",
    response_model=RecommendationResult,
    summary="Generate evidence-grounded next-best action recommendation (Task 12)",
    description=(
        "Evaluates company lead score, freshness, and WASH indicators deterministically against "
        "controlled actions (PRIORITIZE_OUTREACH, MONITOR, REVERIFY, etc.) with explicit human advisory boundary."
    ),
)
async def generate_recommendation_endpoint(
    request: RecommendationRequest,
    service: CSRRecommendationService = Depends(get_copilot_service),
) -> RecommendationResult:
    """Generates and persists a next-best action recommendation."""
    return service.generate_recommendation(request)


@router.get(
    "/recommendations/{company}",
    response_model=RecommendationHistoryResponse,
    summary="Get recommendation history for a company (Task 12)",
    description="Returns chronological audit trail of all generated recommendations for the specified company.",
)
async def get_company_recommendations_endpoint(
    company: str = Path(..., description="Company name"),
    service: CSRRecommendationService = Depends(get_copilot_service),
) -> RecommendationHistoryResponse:
    """Fetches recommendation history for a candidate company."""
    history_resp = service.get_company_history(company)
    if not history_resp.history:
        raise HTTPException(status_code=404, detail=f"No recommendations found for company: {company}")
    return history_resp


@router.post(
    "/chat",
    response_model=CopilotChatResponse,
    summary="Interactive Copilot Q&A for Jaldhaara staff (Task 12)",
    description=(
        "Answers staff queries about candidate recommendations and CSR intelligence "
        "using verified recommendation records and ChromaDB semantic document retrieval."
    ),
)
async def copilot_chat_endpoint(
    request: CopilotChatRequest,
    service: CSRRecommendationService = Depends(get_copilot_service),
) -> CopilotChatResponse:
    """Answers staff natural language questions about candidate companies."""
    return service.chat_with_copilot(request)
