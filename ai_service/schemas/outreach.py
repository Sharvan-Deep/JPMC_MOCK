"""
Pydantic Schemas for Task 13: Outreach Drafting Assistant.

Defines contracts for:
- Outreach context (company intelligence, score, freshness, recommendation, projects, evidence)
- Outreach draft and revision history
- Conversational chat editing requests/responses
- Explicit claim validation results
- Human approval workflow
- Send audit logging and safe sending boundary
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ai_service.schemas.copilot import RecommendationAction
from ai_service.schemas.verification import CSREvidenceReference


class OutreachApprovalStatus(str, Enum):
    """Enforced lifecycle states for an outreach draft."""

    DRAFT = "DRAFT"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    SENT = "SENT"


class CompanyOutreachContext(BaseModel):
    """Aggregated verified company context for outreach personalization."""

    company: str = Field(..., description="Company name")
    lead_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Task 11 Lead Score (0–100)")
    priority: Optional[str] = Field(None, description="Task 11 Priority Band")
    freshness: Optional[str] = Field(None, description="Task 10 Freshness Status (GREEN/YELLOW/RED)")
    wash_direction: Optional[str] = Field(None, description="Task 9 WASH Direction")
    recommended_action: Optional[RecommendationAction] = Field(
        None, description="Task 12 Recommended Action"
    )
    projects: List[Dict[str, Any]] = Field(
        default_factory=list, description="Verified CSR projects from Task 4/8/9"
    )
    geography: List[str] = Field(
        default_factory=list, description="Verified priority states or operational districts"
    )
    commitments: List[str] = Field(
        default_factory=list, description="Verified multi-year commitments or board priorities"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Traceable evidence references supporting the profile"
    )


class ClaimValidationResult(BaseModel):
    """Validation report checking factual claims against verified evidence."""

    verified_claims: List[str] = Field(
        default_factory=list, description="Company/numerical/geographic claims corroborated by evidence"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Claims lacking verifiable backing in disclosures"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Advisory warnings or flags for reviewing staff"
    )
    is_valid_for_approval: bool = Field(
        ..., description="True if no blocking unsupported claims exist"
    )


class DraftRevision(BaseModel):
    """A snapshot of a draft revision in the draft's history."""

    revision_id: int = Field(..., description="1-indexed revision sequence")
    instruction: str = Field(..., description="Staff instruction or trigger that created this revision")
    subject: str = Field(..., description="Subject line at this revision")
    body: str = Field(..., description="Email body at this revision")
    evidence_used: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references backing this revision"
    )
    timestamp: str = Field(..., description="ISO-8601 creation timestamp")


class OutreachDraft(BaseModel):
    """Structured email draft with revision history, evidence traceability, and approval state."""

    draft_id: str = Field(..., description="Unique draft identifier")
    company: str = Field(..., description="Target corporate candidate")
    subject: str = Field(..., description="Current chosen subject line")
    body: str = Field(..., description="Current email body markdown/text")
    tone: str = Field("professional", description="Current tone (formal, professional, executive, etc.)")
    purpose: str = Field("partnership_inquiry", description="Outreach purpose matching recommended action")
    subject_options: List[str] = Field(
        default_factory=list, description="Grounded subject-line variations"
    )
    evidence_used: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references explicitly cited or backing the draft"
    )
    personalization_points: List[str] = Field(
        default_factory=list, description="Company-specific verified hooks incorporated"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Identified claims needing review or evidence"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Advisory warnings for reviewing staff"
    )
    draft_version: int = Field(1, description="Current revision version number")
    created_at: str = Field(..., description="ISO-8601 timestamp when first drafted")
    updated_at: str = Field(..., description="ISO-8601 timestamp of most recent revision")
    approval_status: OutreachApprovalStatus = Field(
        OutreachApprovalStatus.DRAFT, description="Approval state: DRAFT, EDITED, APPROVED, SENT"
    )
    recommendation_version: str = Field("v1", description="Associated recommendation engine version")
    revision_history: List[DraftRevision] = Field(
        default_factory=list, description="Chronological record of past revisions"
    )


class GenerateDraftRequest(BaseModel):
    """Payload to initiate a new personalized draft for a candidate company."""

    company: str = Field(..., description="Target company name")
    tone: Optional[str] = Field("professional", description="Desired tone (e.g. professional, formal)")
    recipient_role: Optional[str] = Field(
        "CSR Head", description="Target recipient persona (e.g. CSR Committee Head, Sustainability Lead)"
    )
    custom_instructions: Optional[str] = Field(
        None, description="Initial customized guidance for drafting"
    )


class EditDraftRequest(BaseModel):
    """Staff conversational instruction to edit an existing draft."""

    draft_id: str = Field(..., description="Target draft ID to revise")
    instruction: str = Field(..., min_length=1, description="Staff instruction (e.g. 'Make it shorter')")


class ApproveDraftRequest(BaseModel):
    """Explicit human approval action."""

    draft_id: str = Field(..., description="Target draft ID to approve")
    approved_by: str = Field(..., min_length=1, description="Name or identifier of staff approver")
    notes: Optional[str] = Field(None, description="Optional approval notes or sign-off remarks")


class SendDraftRequest(BaseModel):
    """Action to transmit an APPROVED draft via the sending service."""

    draft_id: str = Field(..., description="Target draft ID to send")
    recipient_email: str = Field(..., description="Target corporate recipient email address")
    sender_email: Optional[str] = Field(
        None, description="Optional sending email override (defaults to configured Jaldhaara address)"
    )


class SendAuditRecord(BaseModel):
    """Permanent, auditable record created when an approved email is sent."""

    send_id: str = Field(..., description="Unique send transaction ID")
    draft_id: str = Field(..., description="Associated draft ID")
    company: str = Field(..., description="Recipient company name")
    approved_at: str = Field(..., description="ISO-8601 timestamp when human approval occurred")
    approved_by: str = Field(..., description="Identifier of staff member who approved")
    sent_at: str = Field(..., description="ISO-8601 timestamp when email was transmitted")
    recipient: str = Field(..., description="Recipient email address")
    sender: str = Field(..., description="Sender email address")
    subject: str = Field(..., description="Transmitted email subject")
    final_body: str = Field(..., description="Exact transmitted email body")
    evidence_used: List[CSREvidenceReference] = Field(
        default_factory=list, description="Traceable evidence attached to the sent draft"
    )
    recommendation_version: str = Field("v1", description="Associated recommendation version")
    draft_version: int = Field(..., description="Draft version number at time of send")
    send_status: str = Field("SENT", description="Delivery status (SENT, FAILED, MOCK_SENT)")
    error_message: Optional[str] = Field(None, description="Failure details if send failed")
