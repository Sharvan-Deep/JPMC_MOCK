"""
Freshness Assessment API Endpoints for Task 10: CSR Freshness System.

Provides endpoints for:
- POST /api/v1/freshness/calculate
- GET /api/v1/freshness/{company}/current
- GET /api/v1/freshness/{company}/history
- GET /api/v1/freshness/{company}/last-verified
"""

from fastapi import APIRouter, Depends, HTTPException
from ai_service.freshness.service import CSRFreshnessService
from ai_service.schemas.freshness import (
    FreshnessAssessment,
    FreshnessCalculationRequest,
    FreshnessHistoryResponse,
)

router = APIRouter(prefix="/api/v1/freshness", tags=["Freshness"])

# Module-level singleton instance of CSRFreshnessService
_freshness_service = CSRFreshnessService()


def get_freshness_service() -> CSRFreshnessService:
    return _freshness_service


@router.post(
    "/calculate",
    response_model=FreshnessAssessment,
    summary="Calculate and record company CSR/WASH freshness assessment (Task 10)",
    description=(
        "Calculates deterministic GREEN/YELLOW/RED freshness based on current-cycle verification, "
        "financial year recency, and Task 9 WASH direction. Never overwrites past records."
    ),
)
async def calculate_freshness_endpoint(
    request: FreshnessCalculationRequest,
    service: CSRFreshnessService = Depends(get_freshness_service),
):
    """Calculates and stores an append-only freshness assessment for a company."""
    from ai_service.freshness.cycle import format_iso_timestamp

    verified_at = request.verified_at
    if verified_at is None and request.wash_direction is not None:
        verified_at = format_iso_timestamp()

    assessment = service.calculate_freshness(
        company=request.company,
        verification_cycle=request.verification_cycle,
        financial_year=request.financial_year,
        is_current_reporting_cycle=request.is_current_reporting_cycle,
        wash_direction=request.wash_direction,
        sources=request.sources,
        primary_document_metadata=request.primary_document,
        retrieved_at=request.retrieved_at,
        verified_at=verified_at,
    )
    return assessment



@router.get(
    "/{company}/current",
    response_model=FreshnessAssessment,
    summary="Get current freshness status for a company (Task 10)",
    description="Retrieves the most recent verified freshness assessment for the company.",
)
async def get_current_freshness(
    company: str,
    service: CSRFreshnessService = Depends(get_freshness_service),
):
    """Retrieves current freshness status."""
    assessment = service.get_current_status(company)
    if not assessment:
        raise HTTPException(
            status_code=404, detail=f"No freshness assessment found for company '{company}'."
        )
    return assessment


@router.get(
    "/{company}/history",
    response_model=FreshnessHistoryResponse,
    summary="Get freshness history timeline for a company (Task 10)",
    description="Returns complete chronological audit trail of freshness assessments.",
)
async def get_freshness_history(
    company: str,
    service: CSRFreshnessService = Depends(get_freshness_service),
):
    """Retrieves complete historical freshness timeline."""
    return service.get_history(company)


@router.get(
    "/{company}/last-verified",
    response_model=FreshnessAssessment,
    summary="Get last verified assessment for a company (Task 10)",
    description="Retrieves the most recent assessment where actual verification was completed.",
)
async def get_last_verified(
    company: str,
    service: CSRFreshnessService = Depends(get_freshness_service),
):
    """Retrieves the most recent successfully verified record."""
    assessment = service.get_last_verification(company)
    if not assessment:
        raise HTTPException(
            status_code=404, detail=f"No verification record found for company '{company}'."
        )
    return assessment
