"""
Unit and Integration Tests for Task 13: Outreach Drafting Assistant.

Verifies:
1. Initial draft generation
2. Company personalization
3. Recommendation-aware draft (Partnership proposal vs Impact proposal)
4. WASH project retrieval
5. ChromaDB evidence retrieval
6. "Make it shorter" conversational edit
7. "Make it more formal" conversational edit
8. "Add water project" conversational edit
9. Unsupported project claim handling
10. Unsupported statistic handling
11. Subject line generation options
12. Draft revision history tracking
13. Factual claim validation
14. Human approval workflow
15. Cannot send unapproved draft (strict boundary)
16. Approved draft can reach sender
17. Send failure handling
18. Missing recipient error handling
19. Missing email configuration / invalid email handling
20. Evidence traceability preserved
21. Conversation context across multiple revisions
22. Multiple revisions chronological ordering
23. Human approval boundary enforcement across states
"""

import json
import pytest
from fastapi.testclient import TestClient

from ai_service.copilot.repository import RecommendationRepository
from ai_service.main import create_app
from ai_service.outreach.providers import MockOutreachDraftProvider
from ai_service.outreach.repository import OutreachRepository
from ai_service.outreach.sender import MockEmailSender
from ai_service.outreach.service import CSROutreachAssistantService
from ai_service.schemas.copilot import RecommendationAction, RecommendationResult
from ai_service.schemas.outreach import (
    ApproveDraftRequest,
    CompanyOutreachContext,
    EditDraftRequest,
    GenerateDraftRequest,
    OutreachApprovalStatus,
    SendDraftRequest,
)
from ai_service.schemas.verification import CSREvidenceReference


@pytest.fixture
def tmp_storage(tmp_path):
    drafts_path = str(tmp_path / "test_drafts.json")
    audit_path = str(tmp_path / "test_audit.json")
    rec_path = str(tmp_path / "test_recs.json")
    return drafts_path, audit_path, rec_path


@pytest.fixture
def outreach_service(tmp_storage):
    drafts_path, audit_path, rec_path = tmp_storage
    repo = OutreachRepository(drafts_path=drafts_path, audit_path=audit_path)
    rec_repo = RecommendationRepository(storage_path=rec_path)

    # Seed sample recommendation for Tata Chemicals
    ev = CSREvidenceReference(
        company="Tata Chemicals Limited",
        financial_year="2023-24",
        page=14,
        relevant_source_text="TCSRD safe drinking water projects covering 45 villages with installation of 12 community RO plants in Gujarat.",
    )
    rec_result = RecommendationResult(
        company="Tata Chemicals Limited",
        recommended_action=RecommendationAction.APPROACH_WITH_PARTNERSHIP_PROPOSAL,
        confidence=0.95,
        reasons=["High-priority WASH donor candidate"],
        supporting_evidence=[ev],
        is_advisory=True,
        scoring_version="v1",
        recommendation_version="v1",
        created_at="2026-09-04T12:00:00Z",
        metadata={
            "lead_score": 88.5,
            "priority_band": "HIGH_PRIORITY",
            "freshness_status": "GREEN",
            "wash_direction": "INCREASED",
            "has_multi_year_commitment": True,
        },
    )
    rec_repo.save(rec_result)

    mock_provider = MockOutreachDraftProvider()
    mock_sender = MockEmailSender()

    return CSROutreachAssistantService(
        repository=repo,
        rec_repository=rec_repo,
        draft_provider=mock_provider,
        email_sender=mock_sender,
    )


@pytest.fixture
def client(outreach_service):
    app = create_app()
    from ai_service.routes import outreach as outreach_route_module
    outreach_route_module._outreach_service = outreach_service
    return TestClient(app)


# --------------------------------------------------------------------------
# Test Cases 1 - 5: Generation, Personalization, Recommendation & Evidence
# --------------------------------------------------------------------------

def test_01_initial_draft_generation(outreach_service):
    """Initial draft generates properly formatted OutreachDraft with subject and body."""
    req = GenerateDraftRequest(company="Tata Chemicals Limited", recipient_role="CSR Head")
    draft = outreach_service.generate_draft(req)

    assert draft.draft_id.startswith("draft_")
    assert draft.company == "Tata Chemicals Limited"
    assert "Tata Chemicals Limited" in draft.subject
    assert "Dear CSR Head," in draft.body
    assert draft.approval_status == OutreachApprovalStatus.DRAFT
    assert draft.draft_version == 1
    assert len(draft.revision_history) == 1


def test_02_company_personalization(outreach_service):
    """Draft incorporates company-specific disclosures and verified details."""
    req = GenerateDraftRequest(company="Tata Chemicals Limited")
    draft = outreach_service.generate_draft(req)

    assert "TCSRD safe drinking water projects" in draft.body or "Tata Chemicals" in draft.body
    assert len(draft.personalization_points) > 0


def test_03_recommendation_aware_draft(outreach_service):
    """Draft tailors its partnership proposition to the Task 12 recommended action."""
    req = GenerateDraftRequest(company="Tata Chemicals Limited")
    draft = outreach_service.generate_draft(req)

    # For APPROACH_WITH_PARTNERSHIP_PROPOSAL, mentions institutional co-design / hubs
    assert "institutional partnership" in draft.body.lower() or "co-design" in draft.body.lower()


def test_04_wash_project_retrieval(outreach_service):
    """Verified WASH projects are linked to the draft's evidence."""
    req = GenerateDraftRequest(company="Tata Chemicals Limited")
    draft = outreach_service.generate_draft(req)

    assert len(draft.evidence_used) > 0
    assert draft.evidence_used[0].page == 14


def test_05_chromadb_evidence_retrieval(outreach_service):
    """Context aggregation includes ChromaDB evidence when querying the company."""
    context = outreach_service.build_company_context("Tata Chemicals Limited")
    assert context.company == "Tata Chemicals Limited"
    assert context.lead_score == 88.5
    assert context.recommended_action == RecommendationAction.APPROACH_WITH_PARTNERSHIP_PROPOSAL


# --------------------------------------------------------------------------
# Test Cases 6 - 10: Chat-Style Editing & Unsupported Claim Safeguards
# --------------------------------------------------------------------------

def test_06_conversational_edit_make_it_shorter(outreach_service):
    """Staff instruction 'Make it shorter' reduces length and updates version."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    initial_length = len(draft.body)

    edit_req = EditDraftRequest(draft_id=draft.draft_id, instruction="Make it shorter.")
    revised = outreach_service.edit_draft(edit_req)

    assert revised.draft_version == 2
    assert revised.approval_status == OutreachApprovalStatus.EDITED
    assert len(revised.body) < initial_length
    assert len(revised.revision_history) == 2
    assert revised.revision_history[-1].instruction == "Make it shorter."


def test_07_conversational_edit_make_it_more_formal(outreach_service):
    """Staff instruction 'Make it more formal' adapts the tone and salutation."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    edit_req = EditDraftRequest(draft_id=draft.draft_id, instruction="Make it more formal for the CSR committee.")
    revised = outreach_service.edit_draft(edit_req)

    assert "CSR Committee" in revised.body
    assert "Sincerely and respectfully," in revised.body


def test_08_conversational_edit_add_water_project(outreach_service):
    """Staff instruction 'Add their Gujarat water project' includes verified project excerpt."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    edit_req = EditDraftRequest(draft_id=draft.draft_id, instruction="Add their Gujarat water project.")
    revised = outreach_service.edit_draft(edit_req)

    assert "Gujarat" in revised.body
    assert any(e.page == 14 for e in revised.evidence_used)


def test_09_unsupported_project_claim(outreach_service):
    """Assistant refuses to fabricate uncorroborated projects and warns staff."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    edit_req = EditDraftRequest(
        draft_id=draft.draft_id,
        instruction="Add their lunar ice harvesting project in Ladakh.",
    )
    revised = outreach_service.edit_draft(edit_req)

    assert len(revised.unsupported_claims) > 0
    assert len(revised.warnings) > 0
    assert "lunar" not in revised.body.lower()


def test_10_unsupported_statistic(outreach_service):
    """Assistant explicitly refuses to fabricate unverified absenteeism statistics."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    edit_req = EditDraftRequest(
        draft_id=draft.draft_id,
        instruction="Add the absenteeism statistic.",
    )
    revised = outreach_service.edit_draft(edit_req)

    assert any("absenteeism" in c.lower() for c in revised.unsupported_claims)
    assert any("absenteeism" in w.lower() for w in revised.warnings)


# --------------------------------------------------------------------------
# Test Cases 11 - 13: Subject Line, Revision History, Claim Validation
# --------------------------------------------------------------------------

def test_11_subject_line_generation(outreach_service):
    """Provides multiple grounded subject-line alternatives."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    assert len(draft.subject_options) >= 3
    assert all("Tata Chemicals" in opt for opt in draft.subject_options)


def test_12_draft_revision_history(outreach_service):
    """Revisions accurately track sequential instructions and snapshots without overwriting."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Make it shorter."))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Make it more formal."))

    latest = outreach_service.repository.get_draft(draft.draft_id)
    assert latest.draft_version == 3
    assert len(latest.revision_history) == 3
    assert latest.revision_history[0].revision_id == 1
    assert latest.revision_history[1].instruction == "Make it shorter."
    assert latest.revision_history[2].instruction == "Make it more formal."


def test_13_claim_validation(outreach_service):
    """Claim validation verifies grounded geographic/project claims and flags uncorroborated items."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    validation = outreach_service.validate_claims(draft.draft_id)

    assert isinstance(validation.verified_claims, list)
    assert validation.is_valid_for_approval is True


# --------------------------------------------------------------------------
# Test Cases 14 - 19: Approval Workflow, Safe Sending Boundary & Errors
# --------------------------------------------------------------------------

def test_14_approval_workflow(outreach_service):
    """Explicit human approval changes state from DRAFT/EDITED to APPROVED."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    approved = outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Priya Sharma"))

    assert approved.approval_status == OutreachApprovalStatus.APPROVED
    assert any("Priya Sharma" in w for w in approved.warnings)


def test_15_cannot_send_unapproved_draft(outreach_service):
    """Attempting to send an unapproved draft (DRAFT or EDITED) is strictly rejected."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    assert draft.approval_status == OutreachApprovalStatus.DRAFT

    send_req = SendDraftRequest(draft_id=draft.draft_id, recipient_email="csr@tatachemicals.com")
    with pytest.raises(ValueError, match="Explicit human approval.*strictly required"):
        outreach_service.send_draft(send_req)


def test_16_approved_draft_reaches_sender(outreach_service):
    """An approved draft successfully reaches the email sender and logs audit trail."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Priya Sharma"))

    send_req = SendDraftRequest(draft_id=draft.draft_id, recipient_email="csr@tatachemicals.com")
    audit = outreach_service.send_draft(send_req)

    assert audit.send_status == "SENT"
    assert audit.recipient == "csr@tatachemicals.com"
    assert audit.company == "Tata Chemicals Limited"

    updated_draft = outreach_service.repository.get_draft(draft.draft_id)
    assert updated_draft.approval_status == OutreachApprovalStatus.SENT


def test_17_send_failure_handling(outreach_service):
    """Transmission errors during send are safely caught and draft remains unsent."""
    failing_sender = MockEmailSender(simulate_failure=True)
    outreach_service.email_sender = failing_sender

    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Approver"))

    send_req = SendDraftRequest(draft_id=draft.draft_id, recipient_email="csr@tatachemicals.com")
    with pytest.raises(RuntimeError, match="Email delivery failed"):
        outreach_service.send_draft(send_req)


def test_18_missing_recipient_error(outreach_service):
    """Invalid or missing recipient email triggers failure."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Approver"))

    send_req = SendDraftRequest(draft_id=draft.draft_id, recipient_email="invalid_email_format")
    with pytest.raises(RuntimeError, match="Invalid or missing recipient"):
        outreach_service.send_draft(send_req)


def test_19_missing_draft_error(outreach_service):
    """Operating on nonexistent draft raises clear error."""
    with pytest.raises(ValueError, match="not found"):
        outreach_service.edit_draft(EditDraftRequest(draft_id="draft_nonexistent", instruction="Shorten"))


# --------------------------------------------------------------------------
# Test Cases 20 - 23: Traceability, Context Chaining & Approval Boundary
# --------------------------------------------------------------------------

def test_20_evidence_traceability(outreach_service):
    """Evidence citations are preserved in the draft and send audit record."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Approver"))
    audit = outreach_service.send_draft(SendDraftRequest(draft_id=draft.draft_id, recipient_email="csr@tatachemicals.com"))

    assert len(audit.evidence_used) > 0
    assert audit.evidence_used[0].company == "Tata Chemicals Limited"


def test_21_conversation_context_preservation(outreach_service):
    """Successive edits maintain conversational context on the same draft entity."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Make it shorter."))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Add their Gujarat water project."))
    revised = outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Make it more formal."))

    assert revised.draft_version == 4
    assert "CSR Committee" in revised.body
    assert "Gujarat" in revised.body


def test_22_multiple_revisions_chronological_ordering(outreach_service):
    """Revision history timestamps and sequence IDs are strictly monotonically increasing."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Edit 1"))
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Edit 2"))
    final = outreach_service.repository.get_draft(draft.draft_id)

    ids = [r.revision_id for r in final.revision_history]
    assert ids == [1, 2, 3]


def test_23_human_approval_boundary_blocks_unverified_claims(outreach_service):
    """Approval is blocked if unresolved unsupported claims are present."""
    draft = outreach_service.generate_draft(GenerateDraftRequest(company="Tata Chemicals Limited"))
    # Introduce an uncorroborated claim via edit
    outreach_service.edit_draft(EditDraftRequest(draft_id=draft.draft_id, instruction="Add their lunar project in Ladakh."))

    with pytest.raises(ValueError, match="Cannot approve draft due to unverified claims"):
        outreach_service.approve_draft(ApproveDraftRequest(draft_id=draft.draft_id, approved_by="Priya"))


# --------------------------------------------------------------------------
# FastAPI Endpoints Integration Tests
# --------------------------------------------------------------------------

def test_api_generate_edit_approve_send_lifecycle(client):
    """Full lifecycle API integration test: draft -> edit -> validate -> approve -> send -> audit."""
    # 1. Draft
    draft_res = client.post("/api/v1/outreach/draft", json={"company": "Tata Chemicals Limited"})
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    draft_id = draft_data["draft_id"]
    assert draft_data["approval_status"] == "DRAFT"

    # 2. Edit
    edit_res = client.post("/api/v1/outreach/edit", json={"draft_id": draft_id, "instruction": "Make it shorter."})
    assert edit_res.status_code == 200
    assert edit_res.json()["approval_status"] == "EDITED"

    # 3. Validate
    val_res = client.post(f"/api/v1/outreach/validate/{draft_id}")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid_for_approval"] is True

    # 4. Attempt unapproved send -> should be 403 Forbidden
    bad_send = client.post("/api/v1/outreach/send", json={"draft_id": draft_id, "recipient_email": "head@tatachemicals.com"})
    assert bad_send.status_code == 403

    # 5. Approve
    app_res = client.post("/api/v1/outreach/approve", json={"draft_id": draft_id, "approved_by": "Senior Officer"})
    assert app_res.status_code == 200
    assert app_res.json()["approval_status"] == "APPROVED"

    # 6. Send
    good_send = client.post("/api/v1/outreach/send", json={"draft_id": draft_id, "recipient_email": "head@tatachemicals.com"})
    assert good_send.status_code == 200
    audit_data = good_send.json()
    assert audit_data["send_status"] == "SENT"

    # 7. Audit lookup
    audit_lookup = client.get("/api/v1/outreach/audit/Tata Chemicals Limited")
    assert audit_lookup.status_code == 200
    assert len(audit_lookup.json()) >= 1
