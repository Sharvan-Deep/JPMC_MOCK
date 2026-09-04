"""
Outreach Drafting Assistant Service for Task 13.

Coordinates:
- Company context aggregation (Lead score, recommendation, freshness, verified disclosures)
- ChromaDB semantic retrieval for project evidence
- Draft generation and conversational editing
- Factual claim validation
- Explicit human approval workflow
- Safe email sending boundary and audit logging
"""

from datetime import datetime, timezone
import os
import uuid
from typing import Any, Dict, List, Optional

from ai_service.copilot.repository import RecommendationRepository
from ai_service.outreach.providers import (
    BaseOutreachDraftProvider,
    GeminiOutreachDraftProvider,
    MockOutreachDraftProvider,
)
from ai_service.outreach.repository import OutreachRepository
from ai_service.outreach.sender import BaseEmailSender, EmailSendResult, MockEmailSender
from ai_service.outreach.validator import ClaimValidator
from ai_service.schemas.copilot import RecommendationAction
from ai_service.schemas.outreach import (
    ApproveDraftRequest,
    ClaimValidationResult,
    CompanyOutreachContext,
    DraftRevision,
    EditDraftRequest,
    GenerateDraftRequest,
    OutreachApprovalStatus,
    OutreachDraft,
    SendAuditRecord,
    SendDraftRequest,
)
from ai_service.schemas.verification import CSREvidenceReference
from ai_service.vector_store.retriever import CSRSemanticSearchService


class CSROutreachAssistantService:
    """Core coordinator service for Task 13 Outreach Assistant."""

    def __init__(
        self,
        repository: Optional[OutreachRepository] = None,
        rec_repository: Optional[RecommendationRepository] = None,
        retriever: Optional[CSRSemanticSearchService] = None,
        draft_provider: Optional[BaseOutreachDraftProvider] = None,
        email_sender: Optional[BaseEmailSender] = None,
    ):
        self.repository = repository or OutreachRepository()
        self.rec_repository = rec_repository or RecommendationRepository()
        self.retriever = retriever or CSRSemanticSearchService()
        if draft_provider:
            self.draft_provider = draft_provider
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            self.draft_provider = GeminiOutreachDraftProvider(api_key=api_key) if api_key else MockOutreachDraftProvider()
        self.email_sender = email_sender or MockEmailSender()

    def build_company_context(self, company: str) -> CompanyOutreachContext:
        """
        Builds aggregated verified company context from Task 11 lead scoring,
        Task 12 recommendation, Task 10 freshness, and Task 7 ChromaDB evidence.
        """
        rec = self.rec_repository.get_latest(company)

        lead_score = rec.metadata.get("lead_score") if rec else None
        priority = rec.metadata.get("priority_band") if rec else None
        freshness = rec.metadata.get("freshness_status") if rec else None
        wash_direction = rec.metadata.get("wash_direction") if rec else None
        recommended_action = rec.recommended_action if rec else RecommendationAction.PRIORITIZE_OUTREACH
        evidence = list(rec.supporting_evidence) if rec else []

        # Query ChromaDB for recent company projects
        projects: List[Dict[str, Any]] = []
        geography: List[str] = []
        try:
            search_res = self.retriever.search(query=f"{company} water sanitation CSR projects", filters={"company_name": company}, top_k=3)
            for hit in search_res.results:
                projects.append({"project_name": hit.text[:100], "location": hit.metadata.get("location", "India")})
                if hit.metadata.get("state"):
                    geography.append(str(hit.metadata["state"]))
                evidence.append(CSREvidenceReference(
                    company=company,
                    financial_year=str(hit.metadata.get("financial_year", "2023-24")),
                    page=hit.metadata.get("page_number"),
                    relevant_source_text=hit.text,
                    document_hash=hit.metadata.get("sha256"),
                ))
        except Exception:
            pass

        return CompanyOutreachContext(
            company=company,
            lead_score=lead_score,
            priority=priority,
            freshness=freshness,
            wash_direction=wash_direction,
            recommended_action=recommended_action,
            projects=projects,
            geography=list(set(geography)),
            commitments=["Multi-year drinking water commitment"] if rec and rec.metadata.get("has_multi_year_commitment") else [],
            evidence=evidence,
        )

    def generate_draft(self, request: GenerateDraftRequest) -> OutreachDraft:
        """Generates a new initial outreach draft for a company."""
        context = self.build_company_context(request.company)
        tone = request.tone or "professional"
        role = request.recipient_role or "CSR Head"

        subject, body, subject_options, personalization, evidence_used = self.draft_provider.generate_initial_draft(
            context=context,
            tone=tone,
            recipient_role=role,
            custom_instructions=request.custom_instructions,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        draft_id = f"draft_{uuid.uuid4().hex[:12]}"

        initial_revision = DraftRevision(
            revision_id=1,
            instruction="Initial generation",
            subject=subject,
            body=body,
            evidence_used=evidence_used,
            timestamp=now_iso,
        )

        draft = OutreachDraft(
            draft_id=draft_id,
            company=request.company,
            subject=subject,
            body=body,
            tone=tone,
            purpose="partnership_inquiry",
            subject_options=subject_options,
            evidence_used=evidence_used,
            personalization_points=personalization,
            unsupported_claims=[],
            warnings=[],
            draft_version=1,
            created_at=now_iso,
            updated_at=now_iso,
            approval_status=OutreachApprovalStatus.DRAFT,
            recommendation_version="v1",
            revision_history=[initial_revision],
        )

        return self.repository.save_draft(draft)

    def edit_draft(self, request: EditDraftRequest) -> OutreachDraft:
        """
        Revises an existing draft in response to a conversational staff instruction.
        Maintains complete revision history and updates approval status to EDITED.
        """
        current_draft = self.repository.get_draft(request.draft_id)
        if not current_draft:
            raise ValueError(f"Draft with ID '{request.draft_id}' not found.")

        context = self.build_company_context(current_draft.company)

        # Retrieve evidence if instruction references projects or topics
        retrieved_evidence: List[CSREvidenceReference] = []
        try:
            search_res = self.retriever.search(
                query=f"{current_draft.company} {request.instruction}",
                filters={"company_name": current_draft.company},
                top_k=3,
            )
            for hit in search_res.results:
                retrieved_evidence.append(CSREvidenceReference(
                    company=current_draft.company,
                    financial_year=str(hit.metadata.get("financial_year", "2023-24")),
                    page=hit.metadata.get("page_number"),
                    relevant_source_text=hit.text,
                    document_hash=hit.metadata.get("sha256"),
                ))
        except Exception:
            pass

        subject, body, subject_opts, personalization, evidence_used, unsupported, warnings = self.draft_provider.revise_draft(
            current_draft=current_draft,
            context=context,
            instruction=request.instruction,
            retrieved_evidence=retrieved_evidence,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        new_version = current_draft.draft_version + 1

        new_revision = DraftRevision(
            revision_id=new_version,
            instruction=request.instruction,
            subject=subject,
            body=body,
            evidence_used=evidence_used,
            timestamp=now_iso,
        )

        current_draft.subject = subject
        current_draft.body = body
        current_draft.subject_options = subject_opts
        current_draft.personalization_points = list(set(current_draft.personalization_points + personalization))
        current_draft.evidence_used = evidence_used
        current_draft.unsupported_claims = unsupported
        current_draft.warnings = warnings
        current_draft.draft_version = new_version
        current_draft.updated_at = now_iso
        current_draft.approval_status = OutreachApprovalStatus.EDITED
        current_draft.revision_history.append(new_revision)

        return self.repository.save_draft(current_draft)

    def validate_claims(self, draft_id: str) -> ClaimValidationResult:
        """Validates all factual statements in a draft against verified evidence."""
        draft = self.repository.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft with ID '{draft_id}' not found.")
        context = self.build_company_context(draft.company)
        return ClaimValidator.validate(draft, context)

    def approve_draft(self, request: ApproveDraftRequest) -> OutreachDraft:
        """
        Explicit human approval step.
        Validates claims, ensures no unverified blocking claims exist, and sets status to APPROVED.
        """
        draft = self.repository.get_draft(request.draft_id)
        if not draft:
            raise ValueError(f"Draft with ID '{request.draft_id}' not found.")

        # Validate claims prior to approval
        validation = self.validate_claims(request.draft_id)
        if not validation.is_valid_for_approval:
            draft.warnings.extend([f"Blocking validation issue: {c}" for c in validation.unsupported_claims])
            self.repository.save_draft(draft)
            raise ValueError(
                f"Cannot approve draft due to unverified claims: {'; '.join(validation.unsupported_claims)}. "
                "Please edit or provide corroborating evidence before approval."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        draft.approval_status = OutreachApprovalStatus.APPROVED
        draft.updated_at = now_iso
        draft.warnings.append(f"Approved by {request.approved_by} at {now_iso}.")

        return self.repository.save_draft(draft)

    def send_draft(self, request: SendDraftRequest) -> SendAuditRecord:
        """
        Transmits an approved outreach draft.
        STRICT BOUNDARY: Only APPROVED drafts can be sent.
        Records permanent SendAuditRecord.
        """
        draft = self.repository.get_draft(request.draft_id)
        if not draft:
            raise ValueError(f"Draft with ID '{request.draft_id}' not found.")

        if draft.approval_status != OutreachApprovalStatus.APPROVED:
            raise ValueError(
                f"Cannot send draft with status '{draft.approval_status.value}'. "
                "Explicit human approval (status APPROVED) is strictly required before sending."
            )

        send_res: EmailSendResult = self.email_sender.send_email(
            draft=draft,
            recipient_email=request.recipient_email,
            sender_email=request.sender_email,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        send_id = f"snd_{uuid.uuid4().hex[:12]}"

        audit = SendAuditRecord(
            send_id=send_id,
            draft_id=draft.draft_id,
            company=draft.company,
            approved_at=draft.updated_at,
            approved_by="Staff Member",
            sent_at=now_iso,
            recipient=request.recipient_email,
            sender=request.sender_email or "partnerships@jaldhaara.org",
            subject=draft.subject,
            final_body=draft.body,
            evidence_used=list(draft.evidence_used),
            recommendation_version=draft.recommendation_version,
            draft_version=draft.draft_version,
            send_status=send_res.status if send_res.success else "FAILED",
            error_message=send_res.error,
        )

        self.repository.record_send_audit(audit)

        if send_res.success:
            draft.approval_status = OutreachApprovalStatus.SENT
            draft.updated_at = now_iso
            self.repository.save_draft(draft)
        else:
            raise RuntimeError(f"Email delivery failed: {send_res.message} ({send_res.error})")

        return audit
