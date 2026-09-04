"""
FastAPI Routes for Task 11: CSR Donor Lead Scoring.

Endpoints:
- POST /api/v1/scoring/score
- POST /api/v1/scoring/score-batch
- GET  /api/v1/scoring/candidates/top
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from ai_service.schemas.scoring import (
    BatchScoringRequest,
    BatchScoringResponse,
    CandidateScoringInput,
    LeadScore,
)
from ai_service.scoring.service import CSRLeadScoringService

router = APIRouter(prefix="/api/v1/scoring", tags=["Lead Scoring"])

_scoring_service = CSRLeadScoringService()


def get_scoring_service() -> CSRLeadScoringService:
    return _scoring_service


@router.post(
    "/score",
    response_model=LeadScore,
    summary="Calculate transparent 0–100 donor lead score for a candidate (Task 11)",
    description=(
        "Evaluates candidate across 7 orthogonal dimensions (WASH relevance, spending signal, "
        "freshness, commitment, historical record, geography, trend). "
        "Provides positive/limiting factors and evidence coverage."
    ),
)
async def score_company_endpoint(
    candidate: CandidateScoringInput,
    service: CSRLeadScoringService = Depends(get_scoring_service),
):
    """Calculates lead score for a single company."""
    return service.score_company(candidate)


@router.post(
    "/score-batch",
    response_model=BatchScoringResponse,
    summary="Batch score and deterministically rank candidate companies (Task 11)",
    description=(
        "Scores all candidate companies and returns them sorted by multi-criteria ranking: "
        "total_score -> wash_relevance -> freshness -> historical_track_record -> company name."
    ),
)
async def score_batch_endpoint(
    request: BatchScoringRequest,
    service: CSRLeadScoringService = Depends(get_scoring_service),
):
    """Scores a batch of companies and returns ranked results."""
    ranked = service.score_companies(request.candidates, target_states=request.target_states)
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return BatchScoringResponse(
        total_candidates=len(ranked),
        scored_candidates=ranked,
        scoring_version=service.scoring_version,
        scored_at=now_iso,
    )


@router.get(
    "/candidates/top",
    response_model=List[LeadScore],
    summary="Score and rank top MCA candidates (Task 11)",
    description="Retrieves and scores top corporate candidates directly from the historical MCA dataset.",
)
async def get_top_candidates_endpoint(
    limit: int = Query(default=10, ge=1, le=50, description="Number of candidates to evaluate"),
    service: CSRLeadScoringService = Depends(get_scoring_service),
):
    """Scores and ranks top candidate companies from MCA data."""
    return service.score_top_mca_candidates(limit=limit)
