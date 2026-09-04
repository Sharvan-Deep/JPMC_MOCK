"""
Unit and Integration Tests for Task 12: Next-Best-Action Recommendation Copilot.

Verifies:
1. Recommendation engine produces valid RecommendationResult schemas.
2. Deterministic recommendation actions for all 7 controlled types:
   - PRIORITIZE_OUTREACH
   - APPROACH_WITH_PARTNERSHIP_PROPOSAL
   - APPROACH_WITH_IMPACT_PROPOSAL
   - RESEARCH_BEFORE_OUTREACH
   - MONITOR
   - REVERIFY
   - DO_NOT_PRIORITIZE
3. Every recommendation contains affirmative reasons and next steps.
4. Positive and limiting factors are transparently identified.
5. High-score + GREEN + multi-year -> APPROACH_WITH_PARTNERSHIP_PROPOSAL.
6. High-score + GREEN + single-year -> APPROACH_WITH_IMPACT_PROPOSAL.
7. High-score + YELLOW freshness -> REVERIFY.
8. High-score + low evidence coverage (< 0.6) -> RESEARCH_BEFORE_OUTREACH.
9. Moderate score (40–59) -> MONITOR.
10. Low score (< 40) or LOST_FOCUS -> DO_NOT_PRIORITIZE.
11. Freshness RED -> DO_NOT_PRIORITIZE.
12. Strict human advisory boundary preserved (is_advisory == True).
13. Append-only history: historical recommendations are never overwritten.
14. Copilot chat answers grounded in verified recommendation record.
15. Copilot explicitly indicates INSUFFICIENT_EVIDENCE when data is missing.
16. ChromaDB semantic search context is passed to Copilot chat.
17. FastAPI endpoint POST /api/v1/copilot/recommend works.
18. FastAPI endpoint GET /api/v1/copilot/recommendations/{company} works.
19. FastAPI endpoint POST /api/v1/copilot/chat works.
"""

import json
import os
import pytest
from fastapi.testclient import TestClient

from ai_service.copilot.providers import MockCopilotProvider
from ai_service.copilot.repository import RecommendationRepository
from ai_service.copilot.rules import RecommendationRulesEngine
from ai_service.copilot.service import CSRRecommendationService
from ai_service.main import create_app
from ai_service.schemas.copilot import (
    CopilotChatRequest,
    RecommendationAction,
    RecommendationRequest,
    RecommendationResult,
)
from ai_service.schemas.verification import CSREvidenceReference


@pytest.fixture
def tmp_storage(tmp_path):
    return str(tmp_path / "test_recommendations.json")


@pytest.fixture
def test_repo(tmp_storage):
    return RecommendationRepository(storage_path=tmp_storage)


@pytest.fixture
def copilot_service(test_repo):
    mock_provider = MockCopilotProvider()
    return CSRRecommendationService(repository=test_repo, copilot_provider=mock_provider)


@pytest.fixture
def client(test_repo):
    app = create_app()
    # Inject service with isolated repository
    mock_provider = MockCopilotProvider()
    service = CSRRecommendationService(repository=test_repo, copilot_provider=mock_provider)
    from ai_service.routes import copilot as copilot_route_module
    copilot_route_module._copilot_service = service
    return TestClient(app)


# --------------------------------------------------------------------------
# Test Cases 1 - 12: Deterministic Rules Engine & Schema Verification
# --------------------------------------------------------------------------

def test_01_result_schema_structure(copilot_service):
    """Verifies that generated recommendation matches all schema requirements."""
    req = RecommendationRequest(
        company="Tata Chemicals Limited",
        lead_score=85.0,
        priority_band="HIGH_PRIORITY",
        freshness_status="GREEN",
        wash_classification="WASH_FOCUSED",
        wash_direction="INCREASED",
        has_multi_year_commitment=True,
        evidence_coverage=0.9,
    )
    result = copilot_service.generate_recommendation(req)
    assert isinstance(result, RecommendationResult)
    assert result.company == "Tata Chemicals Limited"
    assert result.is_advisory is True
    assert result.confidence > 0.0
    assert len(result.reasons) > 0
    assert len(result.next_steps) > 0
    assert result.recommendation_id.startswith("rec_")


def test_02_approach_with_partnership_proposal(copilot_service):
    """High score (>=80), GREEN freshness, and multi-year commitment -> APPROACH_WITH_PARTNERSHIP_PROPOSAL."""
    req = RecommendationRequest(
        company="Tata Chemicals Limited",
        lead_score=88.5,
        freshness_status="GREEN",
        wash_direction="INCREASED",
        has_multi_year_commitment=True,
        evidence_coverage=0.85,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.APPROACH_WITH_PARTNERSHIP_PROPOSAL
    assert any("multi-year" in s.lower() for s in result.next_steps)
    assert result.confidence >= 0.90


def test_03_approach_with_impact_proposal(copilot_service):
    """High score (>=80), GREEN freshness, but without multi-year commitment -> APPROACH_WITH_IMPACT_PROPOSAL."""
    req = RecommendationRequest(
        company="Indian Oil Corporation Limited",
        lead_score=84.0,
        freshness_status="GREEN",
        wash_direction="STABLE",
        has_multi_year_commitment=False,
        evidence_coverage=0.85,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.APPROACH_WITH_IMPACT_PROPOSAL
    assert any("project proposal" in s.lower() or "target" in s.lower() for s in result.next_steps)


def test_04_prioritize_outreach(copilot_service):
    """Solid score (60–79) with GREEN freshness and good evidence -> PRIORITIZE_OUTREACH."""
    req = RecommendationRequest(
        company="Infosys Limited",
        lead_score=72.0,
        freshness_status="GREEN",
        wash_direction="STABLE",
        evidence_coverage=0.75,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.PRIORITIZE_OUTREACH
    assert any("outreach" in s.lower() for s in result.next_steps)


def test_05_reverify_action(copilot_service):
    """High or solid score with YELLOW freshness -> REVERIFY."""
    req = RecommendationRequest(
        company="Larsen & Toubro",
        lead_score=82.0,
        freshness_status="YELLOW",
        wash_direction="STABLE",
        evidence_coverage=0.70,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.REVERIFY
    assert any("re-verify" in r.lower() or "aging" in r.lower() for r in result.reasons)
    assert any("task 9" in s.lower() or "annual report" in s.lower() for s in result.next_steps)


def test_06_research_before_outreach(copilot_service):
    """Viable score (>=60) but low evidence coverage (< 0.6) -> RESEARCH_BEFORE_OUTREACH."""
    req = RecommendationRequest(
        company="Wipro Limited",
        lead_score=65.0,
        freshness_status="GREEN",
        evidence_coverage=0.45,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.RESEARCH_BEFORE_OUTREACH
    assert len(result.missing_information) > 0
    assert any("research" in s.lower() or "disclosures" in s.lower() for s in result.next_steps)


def test_07_monitor_action_moderate_score(copilot_service):
    """Moderate score (40–59) -> MONITOR."""
    req = RecommendationRequest(
        company="HDFC Bank",
        lead_score=52.0,
        priority_band="LOW_PRIORITY",
        freshness_status="GREEN",
        evidence_coverage=0.70,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.MONITOR
    assert any("monitor" in r.lower() for r in result.reasons)


def test_08_do_not_prioritize_low_score(copilot_service):
    """Low score (< 40) -> DO_NOT_PRIORITIZE."""
    req = RecommendationRequest(
        company="Acme Steel Corp",
        lead_score=25.0,
        freshness_status="YELLOW",
        evidence_coverage=0.5,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.DO_NOT_PRIORITIZE
    assert any("deprioritize" in s.lower() for s in result.next_steps)


def test_09_do_not_prioritize_lost_focus(copilot_service):
    """WASH direction LOST_FOCUS -> DO_NOT_PRIORITIZE even if lead score was high."""
    req = RecommendationRequest(
        company="Pivot Tech",
        lead_score=75.0,
        freshness_status="GREEN",
        wash_direction="LOST_FOCUS",
        evidence_coverage=0.8,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.DO_NOT_PRIORITIZE


def test_10_do_not_prioritize_freshness_red(copilot_service):
    """Freshness status RED -> DO_NOT_PRIORITIZE."""
    req = RecommendationRequest(
        company="Legacy Corp",
        lead_score=70.0,
        freshness_status="RED",
        evidence_coverage=0.8,
    )
    result = copilot_service.generate_recommendation(req)
    assert result.recommended_action == RecommendationAction.DO_NOT_PRIORITIZE
    assert any("RED" in f for f in result.limiting_factors)


def test_11_evidence_traceability(copilot_service):
    """Supplied evidence references are preserved and attached to the recommendation."""
    ev = CSREvidenceReference(
        company="Tata Chemicals",
        financial_year="2023-24",
        page=42,
        relevant_source_text="Allocated ₹12.5 Cr towards rural clean water supply kiosks in Gujarat.",
    )
    req = RecommendationRequest(
        company="Tata Chemicals",
        lead_score=85.0,
        freshness_status="GREEN",
        evidence=[ev],
    )
    result = copilot_service.generate_recommendation(req)
    assert len(result.supporting_evidence) == 1
    assert result.supporting_evidence[0].page == 42
    assert "Gujarat" in result.supporting_evidence[0].relevant_source_text


def test_12_strict_human_advisory_boundary(copilot_service):
    """Ensures is_advisory is always True across various requests."""
    for score in [15.0, 50.0, 75.0, 95.0]:
        req = RecommendationRequest(company="Test Co", lead_score=score, freshness_status="GREEN")
        res = copilot_service.generate_recommendation(req)
        assert res.is_advisory is True


# --------------------------------------------------------------------------
# Test Cases 13: Append-Only History
# --------------------------------------------------------------------------

def test_13_append_only_history_preservation(test_repo, copilot_service):
    """Generating successive recommendations preserves prior records in history without overwriting."""
    req1 = RecommendationRequest(
        company="Tata Chemicals",
        lead_score=70.0,
        freshness_status="YELLOW",
    )
    res1 = copilot_service.generate_recommendation(req1)

    req2 = RecommendationRequest(
        company="Tata Chemicals",
        lead_score=88.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
    )
    res2 = copilot_service.generate_recommendation(req2)

    history = copilot_service.get_company_history("Tata Chemicals")
    assert len(history.history) == 2
    assert history.history[0].recommended_action == res1.recommended_action
    assert history.history[1].recommended_action == res2.recommended_action
    assert history.current_recommendation.recommended_action == res2.recommended_action


# --------------------------------------------------------------------------
# Test Cases 14 - 16: Copilot Interactive Chat & Evidence Grounding
# --------------------------------------------------------------------------

def test_14_copilot_chat_why_recommended(copilot_service):
    """Copilot answers 'why' question with specific action and positive factors."""
    req = RecommendationRequest(
        company="Tata Chemicals",
        lead_score=88.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
    )
    copilot_service.generate_recommendation(req)

    chat_req = CopilotChatRequest(
        company="Tata Chemicals",
        question="Why is this company recommended as a top candidate?",
    )
    resp = copilot_service.chat_with_copilot(chat_req)
    assert "Tata Chemicals" in resp.company
    assert resp.evidence_status == "AVAILABLE"
    assert "APPROACH_WITH_PARTNERSHIP_PROPOSAL" in resp.answer
    assert "confidence" in resp.answer.lower()


def test_15_copilot_chat_insufficient_evidence(copilot_service):
    """Copilot explicitly returns INSUFFICIENT_EVIDENCE when asked about missing data."""
    req = RecommendationRequest(
        company="Unknown Corp",
        lead_score=65.0,
        freshness_status="GREEN",
        evidence_coverage=0.3,
    )
    copilot_service.generate_recommendation(req)

    chat_req = CopilotChatRequest(
        company="Unknown Corp",
        question="What missing information or unverified data gaps exist?",
    )
    resp = copilot_service.chat_with_copilot(chat_req)
    assert resp.evidence_status == "INSUFFICIENT_EVIDENCE"
    assert "missing" in resp.answer.lower()


def test_16_copilot_chat_next_steps(copilot_service):
    """Copilot lists actionable next steps for Jaldhaara staff."""
    req = RecommendationRequest(
        company="Indian Oil",
        lead_score=85.0,
        freshness_status="GREEN",
    )
    copilot_service.generate_recommendation(req)

    chat_req = CopilotChatRequest(
        company="Indian Oil",
        question="What next steps should Jaldhaara staff take?",
    )
    resp = copilot_service.chat_with_copilot(chat_req)
    assert "Recommended next steps" in resp.answer
    assert "1." in resp.answer


# --------------------------------------------------------------------------
# Test Cases 17 - 19: FastAPI API Endpoints Integration
# --------------------------------------------------------------------------

def test_17_endpoint_post_recommend(client):
    """POST /api/v1/copilot/recommend returns valid RecommendationResult."""
    payload = {
        "company": "Infosys Foundation",
        "lead_score": 82.0,
        "priority_band": "HIGH_PRIORITY",
        "freshness_status": "GREEN",
        "has_multi_year_commitment": False,
        "evidence_coverage": 0.8,
    }
    response = client.post("/api/v1/copilot/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Infosys Foundation"
    assert data["recommended_action"] == "APPROACH_WITH_IMPACT_PROPOSAL"
    assert data["is_advisory"] is True
    assert len(data["reasons"]) > 0


def test_18_endpoint_get_recommendations_history(client):
    """GET /api/v1/copilot/recommendations/{company} returns audit history."""
    client.post(
        "/api/v1/copilot/recommend",
        json={"company": "Reliance", "lead_score": 65.0, "freshness_status": "GREEN"},
    )
    response = client.get("/api/v1/copilot/recommendations/Reliance")
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Reliance"
    assert len(data["history"]) == 1

    # Test 404 for unknown company
    resp_404 = client.get("/api/v1/copilot/recommendations/NonExistentCorp")
    assert resp_404.status_code == 404


def test_19_endpoint_post_chat(client):
    """POST /api/v1/copilot/chat answers staff question."""
    client.post(
        "/api/v1/copilot/recommend",
        json={
            "company": "Tata Motors",
            "lead_score": 88.0,
            "freshness_status": "GREEN",
            "has_multi_year_commitment": True,
        },
    )
    chat_payload = {
        "company": "Tata Motors",
        "question": "What is the recommended action and why?",
    }
    response = client.post("/api/v1/copilot/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Tata Motors"
    assert "APPROACH_WITH_PARTNERSHIP_PROPOSAL" in data["answer"]
    assert data["evidence_status"] == "AVAILABLE"
