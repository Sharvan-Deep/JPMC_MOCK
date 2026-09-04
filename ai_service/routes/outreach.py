"""
FastAPI Routes for Task 13: Outreach Drafting Assistant.

Endpoints:
- POST /api/v1/outreach/draft
- POST /api/v1/outreach/edit
- GET  /api/v1/outreach/drafts/{draft_id}
- POST /api/v1/outreach/validate/{draft_id}
- POST /api/v1/outreach/approve
- POST /api/v1/outreach/send
- GET  /api/v1/outreach/audit/{company}
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from ai_service.outreach.service import CSROutreachAssistantService
from ai_service.schemas.outreach import (
    ApproveDraftRequest,
    ClaimValidationResult,
    EditDraftRequest,
    GenerateDraftRequest,
    OutreachDraft,
    SendAuditRecord,
    SendDraftRequest,
)

router = APIRouter(prefix="/api/v1/outreach", tags=["Outreach Drafting Assistant"])

_outreach_service = CSROutreachAssistantService()


def get_outreach_service() -> CSROutreachAssistantService:
    return _outreach_service


@router.post(
    "/draft",
    response_model=OutreachDraft,
    summary="Generate initial personalized outreach draft (Task 13)",
    description="Builds verified company context and generates a personalized, evidence-grounded outreach email.",
)
async def generate_draft_endpoint(
    request: GenerateDraftRequest,
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> OutreachDraft:
    """Generates initial draft."""
    try:
        return service.generate_draft(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/edit",
    response_model=OutreachDraft,
    summary="Conversational chat editing of an existing draft (Task 13)",
    description="Applies staff revision instructions (e.g. 'Make it shorter', 'Add water project').",
)
async def edit_draft_endpoint(
    request: EditDraftRequest,
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> OutreachDraft:
    """Conversational edit."""
    try:
        return service.edit_draft(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/drafts/{draft_id}",
    response_model=OutreachDraft,
    summary="Get outreach draft by ID with revision history (Task 13)",
)
async def get_draft_endpoint(
    draft_id: str = Path(..., description="Draft identifier"),
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> OutreachDraft:
    """Fetches draft."""
    draft = service.repository.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")
    return draft


@router.post(
    "/validate/{draft_id}",
    response_model=ClaimValidationResult,
    summary="Validate factual claims in an outreach draft (Task 13)",
    description="Analyzes financial, geographic, and programmatic claims against verified disclosures.",
)
async def validate_claims_endpoint(
    draft_id: str = Path(..., description="Draft identifier"),
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> ClaimValidationResult:
    """Validates claims."""
    try:
        return service.validate_claims(draft_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/approve",
    response_model=OutreachDraft,
    summary="Explicit human approval of an outreach draft (Task 13)",
    description="Validates claims, enforces human approval boundary, and sets status to APPROVED.",
)
async def approve_draft_endpoint(
    request: ApproveDraftRequest,
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> OutreachDraft:
    """Approves draft."""
    try:
        return service.approve_draft(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/send",
    response_model=SendAuditRecord,
    summary="Send approved outreach email (Task 13)",
    description="Strictly blocked unless draft is APPROVED. Transmits email and records permanent audit entry.",
)
async def send_draft_endpoint(
    request: SendDraftRequest,
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> SendAuditRecord:
    """Sends draft."""
    try:
        return service.send_draft(request)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/audit/{company}",
    response_model=List[SendAuditRecord],
    summary="Get send audit trail for a company (Task 13)",
)
async def get_audit_trail_endpoint(
    company: str = Path(..., description="Company name"),
    service: CSROutreachAssistantService = Depends(get_outreach_service),
) -> List[SendAuditRecord]:
    """Retrieves send audit history."""
    return service.repository.get_audit_records(company)
