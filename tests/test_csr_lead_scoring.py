"""
Comprehensive Test Suite for Task 11: CSR Donor Lead Scoring.

Covers all 20 required scenarios:
1. perfect high-relevance company
2. large CSR company with poor WASH relevance (budget alone does not win)
3. strong WASH but old information
4. strong WASH + GREEN freshness
5. RED company
6. multi-year commitment
7. single-year project
8. historical multi-year track record
9. geographic match
10. missing geography
11. increased WASH trend
12. decreased WASH trend
13. insufficient evidence
14. deterministic score calculation
15. priority-band thresholds
16. ranking
17. tie-breaking
18. score versioning
19. evidence coverage
20. no-double-counting behavior
Plus REST API endpoint integration tests.
"""

import pytest
from fastapi.testclient import TestClient
from ai_service.main import app
from ai_service.schemas.scoring import (
    CandidateScoringInput,
    PriorityBand,
)
from ai_service.scoring.components import ComponentScorers
from ai_service.scoring.ranker import LeadRanker
from ai_service.scoring.service import CSRLeadScoringService


@pytest.fixture
def scoring_service() -> CSRLeadScoringService:
    return CSRLeadScoringService()


# ==============================================================================
# 20 Required Test Scenarios
# ==============================================================================

def test_1_perfect_high_relevance_company(scoring_service: CSRLeadScoringService):
    """Test 1: Company with strong WASH across all dimensions achieves HIGH_PRIORITY (>= 80)."""
    candidate = CandidateScoringInput(
        company="Jal Samriddhi Foundation",
        wash_classification="WASH_RELEVANT",
        wash_subcategories=["safe_drinking_water", "sanitation"],
        total_csr_spend_crore=25.0,
        wash_spend_crore=12.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
        mca_active_years_count=6,
        company_states=["Gujarat", "Maharashtra", "Rajasthan"],
        wash_direction="INCREASED",
    )
    score = scoring_service.score_company(candidate)

    assert score.total_score >= 80.0
    assert score.priority_band == PriorityBand.HIGH_PRIORITY
    assert score.components.wash_relevance.points_awarded == 30.0
    assert score.components.wash_spending.points_awarded == 20.0
    assert score.components.freshness.points_awarded == 15.0
    assert score.components.multi_year_commitment.points_awarded == 10.0
    assert score.components.historical_track_record.points_awarded == 10.0
    assert score.components.geographic_alignment.points_awarded == 10.0
    assert score.components.recent_trend.points_awarded == 5.0
    assert score.total_score == 100.0


def test_2_large_csr_company_poor_wash_relevance(scoring_service: CSRLeadScoringService):
    """
    Test 2: A massive corporate with a huge CSR budget (500 Cr) but NO WASH relevance
    receives a low score (budget alone does NOT dictate ranking).
    """
    candidate = CandidateScoringInput(
        company="Mega Energy Conglomerate Ltd",
        wash_classification="NOT_WASH_RELEVANT",
        total_csr_spend_crore=500.0,
        wash_spend_crore=0.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
        mca_active_years_count=0,
        company_states=["Gujarat", "Maharashtra"],
        wash_direction="STABLE",
    )
    score = scoring_service.score_company(candidate)

    # Even with huge total CSR spend, WASH relevance is 0 and WASH spend is 0
    assert score.components.wash_relevance.points_awarded == 0.0
    assert score.components.wash_spending.points_awarded == 0.0
    assert score.total_score < 40.0
    assert score.priority_band == PriorityBand.VERY_LOW_PRIORITY


def test_3_strong_wash_but_old_information(scoring_service: CSRLeadScoringService):
    """Test 3: Strong WASH company with YELLOW freshness receives moderate score without artificial penalty."""
    candidate = CandidateScoringInput(
        company="Rural Waterworks Ltd",
        wash_classification="WASH_RELEVANT",
        total_csr_spend_crore=20.0,
        wash_spend_crore=5.0,
        freshness_status="YELLOW",  # Prior FY or awaiting verification
        has_multi_year_commitment=False,
        mca_active_years_count=3,
        company_states=["Gujarat"],
        wash_direction="STABLE",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.wash_relevance.points_awarded == 30.0
    assert score.components.freshness.points_awarded == 7.0  # YELLOW = 7 pts
    assert score.priority_band in (PriorityBand.MEDIUM_PRIORITY, PriorityBand.HIGH_PRIORITY)


def test_4_strong_wash_green_freshness(scoring_service: CSRLeadScoringService):
    """Test 4: Strong WASH relevance combined with GREEN freshness yields high synergy."""
    candidate = CandidateScoringInput(
        company="Pani Vikas Ltd",
        wash_classification="WASH_RELEVANT",
        wash_spend_crore=6.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
        mca_active_years_count=4,
        company_states=["Rajasthan", "Gujarat"],
        wash_direction="STABLE",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.wash_relevance.points_awarded == 30.0
    assert score.components.freshness.points_awarded == 15.0
    assert score.total_score >= 80.0
    assert score.priority_band == PriorityBand.HIGH_PRIORITY


def test_5_red_company(scoring_service: CSRLeadScoringService):
    """Test 5: Verified RED company receives 0 on freshness and 0 on trend (LOST_FOCUS)."""
    candidate = CandidateScoringInput(
        company="Abandoned Water Initiatives Ltd",
        wash_classification="NOT_WASH_RELEVANT",
        freshness_status="RED",
        wash_direction="LOST_FOCUS",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.freshness.points_awarded == 0.0
    assert score.components.recent_trend.points_awarded == 0.0
    assert score.priority_band == PriorityBand.VERY_LOW_PRIORITY


def test_6_multi_year_commitment(scoring_service: CSRLeadScoringService):
    """Test 6: Verified multi-year commitment receives maximum 10 points."""
    candidate = CandidateScoringInput(
        company="Long Term Partner Ltd",
        has_multi_year_commitment=True,
    )
    score = scoring_service.score_company(candidate)

    assert score.components.multi_year_commitment.points_awarded == 10.0
    assert score.components.multi_year_commitment.is_insufficient_evidence is False


def test_7_single_year_project(scoring_service: CSRLeadScoringService):
    """Test 7: Single-year project activity receives partial 3 points."""
    candidate = CandidateScoringInput(
        company="Single Year Project Ltd",
        has_multi_year_commitment=False,
    )
    score = scoring_service.score_company(candidate)

    assert score.components.multi_year_commitment.points_awarded == 3.0


def test_8_historical_multi_year_track_record(scoring_service: CSRLeadScoringService):
    """Test 8: 5+ active years in MCA data receives full 10 points."""
    candidate = CandidateScoringInput(
        company="Decade Long Donor Ltd",
        mca_active_years_count=7,
    )
    score = scoring_service.score_company(candidate)

    assert score.components.historical_track_record.points_awarded == 10.0


def test_9_geographic_match(scoring_service: CSRLeadScoringService):
    """Test 9: Geographic presence in target states receives high alignment score."""
    candidate = CandidateScoringInput(
        company="State Partner Ltd",
        company_states=["Gujarat", "Rajasthan", "Maharashtra", "Karnataka"],
    )
    score = scoring_service.score_company(candidate)

    assert score.components.geographic_alignment.points_awarded == 10.0


def test_10_missing_geography(scoring_service: CSRLeadScoringService):
    """Test 10: Missing location data yields 0 points marked as insufficient evidence."""
    candidate = CandidateScoringInput(
        company="No Location Data Ltd",
        company_states=[],
    )
    score = scoring_service.score_company(candidate)

    assert score.components.geographic_alignment.points_awarded == 0.0
    assert score.components.geographic_alignment.is_insufficient_evidence is True


def test_11_increased_wash_trend(scoring_service: CSRLeadScoringService):
    """Test 11: INCREASED trend receives maximum 5 points."""
    candidate = CandidateScoringInput(
        company="Expanding Water Ltd",
        wash_direction="INCREASED",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.recent_trend.points_awarded == 5.0


def test_12_decreased_wash_trend(scoring_service: CSRLeadScoringService):
    """Test 12: DECREASED trend receives 1 point."""
    candidate = CandidateScoringInput(
        company="Declining Water Ltd",
        wash_direction="DECREASED",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.recent_trend.points_awarded == 1.0


def test_13_insufficient_evidence(scoring_service: CSRLeadScoringService):
    """Test 13: Insufficient evidence is recorded in missing_information and not treated as negative fact."""
    candidate = CandidateScoringInput(
        company="Sparse Profile Corp",
        wash_classification="INSUFFICIENT_EVIDENCE",
    )
    score = scoring_service.score_company(candidate)

    assert score.components.wash_relevance.is_insufficient_evidence is True
    assert len(score.missing_information) > 0


def test_14_deterministic_score_calculation(scoring_service: CSRLeadScoringService):
    """Test 14: Total score exactly equals the sum of all 7 components."""
    candidate = CandidateScoringInput(
        company="Math Check Corp",
        wash_classification="PARTIALLY_RELEVANT",  # 15
        wash_spend_crore=3.0,                     # 10
        freshness_status="YELLOW",                # 7
        has_multi_year_commitment=False,          # 3
        mca_active_years_count=3,                 # 7
        company_states=["Gujarat"],               # 6
        wash_direction="STABLE",                  # 3
    )
    score = scoring_service.score_company(candidate)

    expected_sum = 15.0 + 10.0 + 7.0 + 3.0 + 7.0 + 6.0 + 3.0
    assert score.total_score == expected_sum
    assert score.total_score == 51.0
    assert score.priority_band == PriorityBand.LOW_PRIORITY


def test_15_priority_band_thresholds(scoring_service: CSRLeadScoringService):
    """Test 15: Priority band boundaries (80, 60, 40)."""
    assert scoring_service._determine_priority_band(85.0) == PriorityBand.HIGH_PRIORITY
    assert scoring_service._determine_priority_band(80.0) == PriorityBand.HIGH_PRIORITY
    assert scoring_service._determine_priority_band(79.9) == PriorityBand.MEDIUM_PRIORITY
    assert scoring_service._determine_priority_band(60.0) == PriorityBand.MEDIUM_PRIORITY
    assert scoring_service._determine_priority_band(59.9) == PriorityBand.LOW_PRIORITY
    assert scoring_service._determine_priority_band(40.0) == PriorityBand.LOW_PRIORITY
    assert scoring_service._determine_priority_band(39.9) == PriorityBand.VERY_LOW_PRIORITY


def test_16_ranking(scoring_service: CSRLeadScoringService):
    """Test 16: Multiple candidates are deterministically ranked by total score."""
    c1 = CandidateScoringInput(company="Alpha Ltd", wash_classification="NOT_WASH_RELEVANT") # ~0 pts
    c2 = CandidateScoringInput(company="Beta Ltd", wash_classification="WASH_RELEVANT", wash_spend_crore=10.0, freshness_status="GREEN") # ~65+ pts
    c3 = CandidateScoringInput(company="Gamma Ltd", wash_classification="PARTIALLY_RELEVANT", wash_spend_crore=2.0) # ~25 pts

    ranked = scoring_service.score_companies([c1, c2, c3])
    assert ranked[0].company == "Beta Ltd"
    assert ranked[1].company == "Gamma Ltd"
    assert ranked[2].company == "Alpha Ltd"


def test_17_tie_breaking(scoring_service: CSRLeadScoringService):
    """Test 17: Score ties broken by wash_relevance -> freshness -> history -> company name."""
    # Both achieve identical total score (30 pts each), but different sub-distributions:
    # Candidate A: 30 wash_relevance + 0 freshness
    # Candidate B: 15 wash_relevance + 15 freshness
    c_a = CandidateScoringInput(company="Zeta Water Ltd", wash_classification="WASH_RELEVANT") # 30 relevance
    c_b = CandidateScoringInput(company="Apex Water Ltd", wash_classification="PARTIALLY_RELEVANT", freshness_status="GREEN") # 15 rel + 15 fresh = 30 pts

    ranked = scoring_service.score_companies([c_b, c_a])
    # c_a has higher wash_relevance (30 > 15), so it wins the tie-breaker
    assert ranked[0].company == "Zeta Water Ltd"
    assert ranked[1].company == "Apex Water Ltd"


def test_18_score_versioning(scoring_service: CSRLeadScoringService):
    """Test 18: Score output contains algorithm version 'v1' and ISO timestamp."""
    candidate = CandidateScoringInput(company="Version Check Corp")
    score = scoring_service.score_company(candidate)

    assert score.scoring_version == "v1"
    assert "T" in score.scored_at
    assert score.scored_at.endswith("Z")


def test_19_evidence_coverage(scoring_service: CSRLeadScoringService):
    """Test 19: Evidence coverage calculation reflects proportion of provided data."""
    # Complete candidate has 7/7 dimensions covered -> 1.0
    complete = CandidateScoringInput(
        company="Complete Corp",
        wash_classification="WASH_RELEVANT",
        wash_spend_crore=5.0,
        freshness_status="GREEN",
        has_multi_year_commitment=True,
        mca_active_years_count=3,
        company_states=["Gujarat"],
        wash_direction="STABLE",
    )
    score = scoring_service.score_company(complete)
    assert score.evidence_coverage == 1.0

    # Bare candidate with almost everything missing -> low coverage
    bare = CandidateScoringInput(company="Bare Corp")
    bare_score = scoring_service.score_company(bare)
    assert bare_score.evidence_coverage < 0.5


def test_20_no_double_counting_behavior(scoring_service: CSRLeadScoringService):
    """
    Test 20: Ensures historical longevity and current relevance are distinct components.
    A company with high historical track record but discontinued current status does not
    get double-counted in current relevance.
    """
    candidate = CandidateScoringInput(
        company="Old Veteran Corp",
        wash_classification="NOT_WASH_RELEVANT",  # 0 pts current relevance
        mca_active_years_count=8,                # 10 pts historical record
        wash_direction="LOST_FOCUS",             # 0 pts recent trend
    )
    score = scoring_service.score_company(candidate)

    assert score.components.wash_relevance.points_awarded == 0.0
    assert score.components.historical_track_record.points_awarded == 10.0
    assert score.components.recent_trend.points_awarded == 0.0


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================

def test_21_scoring_api_endpoints():
    """Test 21: End-to-end FastAPI endpoint integration for lead scoring routes."""
    client = TestClient(app)

    # 1. POST /api/v1/scoring/score
    payload = {
        "company": "API Test Candidate",
        "wash_classification": "WASH_RELEVANT",
        "wash_spend_crore": 8.5,
        "freshness_status": "GREEN",
        "has_multi_year_commitment": True,
        "company_states": ["Gujarat", "Maharashtra"],
        "wash_direction": "INCREASED",
    }
    score_resp = client.post("/api/v1/scoring/score", json=payload)
    assert score_resp.status_code == 200
    score_data = score_resp.json()
    assert score_data["company"] == "API Test Candidate"
    assert score_data["total_score"] >= 80.0
    assert score_data["priority_band"] == "HIGH_PRIORITY"

    # 2. POST /api/v1/scoring/score-batch
    batch_payload = {
        "candidates": [
            {"company": "Candidate A", "wash_classification": "NOT_WASH_RELEVANT"},
            {"company": "Candidate B", "wash_classification": "WASH_RELEVANT", "wash_spend_crore": 10.0, "freshness_status": "GREEN"},
        ]
    }
    batch_resp = client.post("/api/v1/scoring/score-batch", json=batch_payload)
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_candidates"] == 2
    assert batch_data["scored_candidates"][0]["company"] == "Candidate B"

    # 3. GET /api/v1/scoring/candidates/top
    top_resp = client.get("/api/v1/scoring/candidates/top?limit=5")
    assert top_resp.status_code == 200
    top_candidates = top_resp.json()
    assert len(top_candidates) > 0
    assert top_candidates[0]["total_score"] >= top_candidates[-1]["total_score"]
