"""
Comprehensive Test Suite for Task 9: CSR Verification & Change Detection.

Tests all 18 required scenarios:
1. unchanged WASH focus
2. new WASH focus
3. lost WASH focus
4. increased spending
5. decreased spending
6. new project
7. discontinued project
8. continuing project
9. geographic expansion
10. geographic contraction
11. continued multi-year commitment
12. semantic project similarity
13. insufficient evidence
14. missing previous document
15. missing current document
16. deterministic percentage calculation
17. evidence traceability
18. document version separation
"""

import pytest
from ai_service.schemas.verification import (
    ChangeCategory,
    CSRDocumentProfile,
    CSREvidenceReference,
    CSRProjectSnapshot,
    ProjectSemanticMatch,
    VerificationConfidence,
    WASHDirection,
)
from ai_service.verification.comparator import DeterministicComparator
from ai_service.verification.providers import MockChangeDetectionProvider
from ai_service.verification.service import CSRChangeDetectionService


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def comparator() -> DeterministicComparator:
    return DeterministicComparator()


@pytest.fixture
def verification_service() -> CSRChangeDetectionService:
    return CSRChangeDetectionService(semantic_provider=MockChangeDetectionProvider())


@pytest.fixture
def base_prev_profile() -> CSRDocumentProfile:
    return CSRDocumentProfile(
        company="Tata Chemicals Limited",
        financial_year="2023-24",
        document_version=1,
        document_type="CSR_REPORT",
        source_url="https://example.com/csr_2023_24.pdf",
        document_hash="a1b2c3d4e5f67890",
        total_csr_spend_crore=25.0,
        wash_spend_crore=10.0,
        water_spend_crore=6.0,
        sanitation_spend_crore=4.0,
        wash_focus_areas=["drinking_water", "sanitation"],
        has_wash_activity=True,
        projects=[
            CSRProjectSnapshot(
                project_name="Swachh Jal Drinking Water Initiative",
                description="Installation of water purification plants in rural areas",
                sector="Safe Drinking Water",
                is_wash=True,
                wash_subcategories=["drinking_water"],
                amount_spent_inr_crore=6.0,
                state="Gujarat",
                district="Devbhumi Dwarka",
                is_multi_year=True,
                page_number=12,
            ),
            CSRProjectSnapshot(
                project_name="Nirmal Gram Sanitation Project",
                description="Construction of household and community sanitation blocks",
                sector="Sanitation",
                is_wash=True,
                wash_subcategories=["sanitation"],
                amount_spent_inr_crore=4.0,
                state="Gujarat",
                district="Devbhumi Dwarka",
                is_multi_year=False,
                page_number=14,
            ),
        ],
        states=["Gujarat"],
        districts=["Devbhumi Dwarka"],
        beneficiary_groups=["Rural households", "School children"],
        beneficiary_count=50000,
        multi_year_commitments=["Swachh Jal Drinking Water Initiative"],
        ongoing_projects=["Swachh Jal Drinking Water Initiative"],
        policy_priorities=["Promoting healthcare and safe drinking water", "Sanitation"],
        raw_evidence_pages={
            "spending": 10,
            "wash": 11,
            "projects": 12,
            "geography": 10,
            "beneficiaries": 15,
            "commitments": 16,
            "policy": 5,
        },
    )


# ==============================================================================
# Tests
# ==============================================================================

def test_1_unchanged_wash_focus(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 1: Unchanged WASH focus remains STABLE across periods."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    curr_profile.document_version = 2

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert result.overall_wash_direction == WASHDirection.STABLE
    assert result.dimensions.wash_focus.direction == WASHDirection.STABLE
    assert result.dimensions.wash_focus.retained_focus == ["drinking_water", "sanitation"]
    assert result.dimensions.wash_focus.added_focus == []
    assert result.dimensions.wash_focus.removed_focus == []


def test_2_new_wash_focus(verification_service: CSRChangeDetectionService):
    """Test 2: Previous has no WASH focus; current introduces multiple WASH projects -> NEW_FOCUS."""
    prev_no_wash = CSRDocumentProfile(
        company="Tech Innovators Ltd",
        financial_year="2023-24",
        document_version=1,
        total_csr_spend_crore=10.0,
        wash_spend_crore=0.0,
        wash_focus_areas=[],
        has_wash_activity=False,
        projects=[
            CSRProjectSnapshot(
                project_name="Digital Literacy Drive",
                is_wash=False,
                amount_spent_inr_crore=10.0,
                page_number=4,
            )
        ],
    )

    curr_with_wash = CSRDocumentProfile(
        company="Tech Innovators Ltd",
        financial_year="2024-25",
        document_version=2,
        total_csr_spend_crore=15.0,
        wash_spend_crore=5.0,
        water_spend_crore=5.0,
        wash_focus_areas=["drinking_water"],
        has_wash_activity=True,
        projects=[
            CSRProjectSnapshot(
                project_name="Rural Clean Drinking Water Stations",
                is_wash=True,
                wash_subcategories=["drinking_water"],
                amount_spent_inr_crore=5.0,
                page_number=8,
            )
        ],
    )

    result = verification_service.verify_changes(prev_no_wash, curr_with_wash)

    assert result.overall_wash_direction == WASHDirection.NEW_FOCUS
    assert result.dimensions.wash_focus.direction == WASHDirection.NEW_FOCUS
    assert "drinking_water" in result.dimensions.wash_focus.added_focus


def test_3_lost_wash_focus(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 3: Previous had strong WASH focus; current reports zero WASH projects -> LOST_FOCUS."""
    curr_lost_wash = CSRDocumentProfile(
        company=base_prev_profile.company,
        financial_year="2024-25",
        document_version=2,
        total_csr_spend_crore=20.0,
        wash_spend_crore=0.0,
        wash_focus_areas=[],
        has_wash_activity=False,
        projects=[
            CSRProjectSnapshot(
                project_name="Solar Power Installation",
                is_wash=False,
                amount_spent_inr_crore=20.0,
                page_number=5,
            )
        ],
    )

    result = verification_service.verify_changes(base_prev_profile, curr_lost_wash)

    assert result.overall_wash_direction == WASHDirection.LOST_FOCUS
    assert result.dimensions.wash_focus.direction == WASHDirection.LOST_FOCUS
    assert len(result.dimensions.wash_focus.removed_focus) > 0


def test_4_increased_spending(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 4: Deterministic spending increase calculation (+50%, +5 Cr)."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    # prev wash spend = 10.0 cr, curr = 15.0 cr (+5 cr, +50%)
    curr_profile.wash_spend_crore = 15.0
    curr_profile.total_csr_spend_crore = 35.0

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    wash_spend = next(
        m for m in result.dimensions.spending.metrics if m.metric == "wash_expenditure"
    )
    assert wash_spend.previous_value == 10.0
    assert wash_spend.current_value == 15.0
    assert wash_spend.absolute_change == 5.0
    assert wash_spend.percentage_change == 50.0
    assert wash_spend.change_type == ChangeCategory.INCREASED


def test_5_decreased_spending(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 5: Deterministic spending decrease calculation (-25%, -2.5 Cr)."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    # prev wash spend = 10.0 cr, curr = 7.5 cr (-2.5 cr, -25%)
    curr_profile.wash_spend_crore = 7.5
    curr_profile.total_csr_spend_crore = 20.0

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    wash_spend = next(
        m for m in result.dimensions.spending.metrics if m.metric == "wash_expenditure"
    )
    assert wash_spend.previous_value == 10.0
    assert wash_spend.current_value == 7.5
    assert wash_spend.absolute_change == -2.5
    assert wash_spend.percentage_change == -25.0
    assert wash_spend.change_type == ChangeCategory.DECREASED


def test_6_new_project(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 6: Detection of newly introduced CSR project in current year."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    new_proj = CSRProjectSnapshot(
        project_name="Jal Jeevan Rainwater Harvesting",
        is_wash=True,
        amount_spent_inr_crore=3.0,
        page_number=18,
    )
    curr_profile.projects.append(new_proj)

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert "Jal Jeevan Rainwater Harvesting" in result.dimensions.projects.new_projects
    new_proj_change = next(
        (c for c in result.changes if c.current_value == "Jal Jeevan Rainwater Harvesting"), None
    )
    assert new_proj_change is not None
    assert new_proj_change.change_type == ChangeCategory.NEW


def test_7_discontinued_project(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 7: Detection of project dropped in current year."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    # Remove Nirmal Gram Sanitation Project
    curr_profile.projects = [
        p for p in curr_profile.projects if "Nirmal Gram" not in p.project_name
    ]

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert "Nirmal Gram Sanitation Project" in result.dimensions.projects.discontinued_projects
    disc_change = next(
        (c for c in result.changes if c.previous_value == "Nirmal Gram Sanitation Project"), None
    )
    assert disc_change is not None
    assert disc_change.change_type == ChangeCategory.DISCONTINUED


def test_8_continuing_project(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 8: Exact name match identifies continuing project across periods."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert "Swachh Jal Drinking Water Initiative" in result.dimensions.projects.continuing_projects
    assert "Nirmal Gram Sanitation Project" in result.dimensions.projects.continuing_projects


def test_9_geographic_expansion(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 9: Geographic expansion to new states and districts is identified as EXPANDED."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    curr_profile.states = ["Gujarat", "Maharashtra", "Rajasthan"]
    curr_profile.districts = ["Devbhumi Dwarka", "Nagpur", "Barmer"]

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert result.dimensions.geography.direction == ChangeCategory.EXPANDED
    assert "Maharashtra" in result.dimensions.geography.new_locations
    assert "Rajasthan" in result.dimensions.geography.new_locations
    assert "Nagpur" in result.dimensions.geography.new_districts
    assert result.dimensions.geography.removed_locations == []


def test_10_geographic_contraction(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 10: Geographic exit from states/districts is identified as CONTRACTED."""
    # Prev has Gujarat and Maharashtra
    prev = base_prev_profile.model_copy(deep=True)
    prev.states = ["Gujarat", "Maharashtra"]
    prev.districts = ["Devbhumi Dwarka", "Pune"]

    # Current only has Gujarat
    curr = base_prev_profile.model_copy(deep=True)
    curr.financial_year = "2024-25"
    curr.states = ["Gujarat"]
    curr.districts = ["Devbhumi Dwarka"]

    result = verification_service.verify_changes(prev, curr)

    assert result.dimensions.geography.direction == ChangeCategory.CONTRACTED
    assert "Maharashtra" in result.dimensions.geography.removed_locations
    assert "Pune" in result.dimensions.geography.removed_districts
    assert result.dimensions.geography.new_locations == []


def test_11_continued_multi_year_commitment(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 11: Multi-year commitment continuity across years is detected."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert result.dimensions.commitments.change_type == ChangeCategory.CONTINUED
    assert len(result.dimensions.commitments.continued_commitments) > 0
    assert "swachh jal drinking water initiative" in [
        c.lower() for c in result.dimensions.commitments.continued_commitments
    ]


def test_12_semantic_project_similarity(base_prev_profile: CSRDocumentProfile):
    """
    Test 12: Projects describing substantially similar activity with different phrasing
    are matched semantically rather than reported as discontinued + new.
    """
    prev = base_prev_profile.model_copy(deep=True)
    prev.projects = [
        CSRProjectSnapshot(
            project_name="providing potable water to rural communities",
            description="installing drinking water reverse osmosis units in rural areas",
            is_wash=True,
            page_number=12,
        )
    ]

    curr = base_prev_profile.model_copy(deep=True)
    curr.financial_year = "2024-25"
    curr.projects = [
        CSRProjectSnapshot(
            project_name="improving access to safe drinking water in villages",
            description="delivering clean potable drinking water filtration to rural villages",
            is_wash=True,
            page_number=15,
        )
    ]

    service = CSRChangeDetectionService(semantic_provider=MockChangeDetectionProvider())
    result = service.verify_changes(prev, curr)

    assert len(result.dimensions.projects.semantic_matches) == 1
    match = result.dimensions.projects.semantic_matches[0]
    assert match.previous_project == "providing potable water to rural communities"
    assert match.current_project == "improving access to safe drinking water in villages"
    assert match.similarity_score >= 0.35
    # Project is in continuing, NOT discontinued
    assert "improving access to safe drinking water in villages" in result.dimensions.projects.continuing_projects
    assert result.dimensions.projects.discontinued_projects == []
    assert result.confidence == VerificationConfidence.MEDIUM


def test_13_insufficient_evidence():
    """Test 13: When documents lack CSR/WASH data, returns INSUFFICIENT_EVIDENCE without guessing."""
    empty_prev = CSRDocumentProfile(
        company="Unknown Corp",
        financial_year="2022-23",
        document_version=1,
    )
    empty_curr = CSRDocumentProfile(
        company="Unknown Corp",
        financial_year="2023-24",
        document_version=1,
    )

    service = CSRChangeDetectionService()
    result = service.verify_changes(empty_prev, empty_curr)

    assert result.overall_wash_direction == WASHDirection.INSUFFICIENT_EVIDENCE
    assert result.dimensions.wash_focus.direction == WASHDirection.INSUFFICIENT_EVIDENCE
    assert result.confidence == VerificationConfidence.LOW


def test_14_missing_previous_document(base_prev_profile: CSRDocumentProfile, verification_service: CSRChangeDetectionService):
    """Test 14: Clear error handling when previous profile is missing."""
    with pytest.raises(ValueError, match="Missing previous document profile"):
        verification_service.verify_changes(None, base_prev_profile)


def test_15_missing_current_document(base_prev_profile: CSRDocumentProfile, verification_service: CSRChangeDetectionService):
    """Test 15: Clear error handling when current profile is missing."""
    with pytest.raises(ValueError, match="Missing current document profile"):
        verification_service.verify_changes(base_prev_profile, None)


def test_16_deterministic_percentage_calculation(comparator: DeterministicComparator):
    """Test 16: Verify deterministic percentage calculation edge cases (zero base, nulls, precision)."""
    # 1. Normal increase: 10 -> 15 (+50.0%)
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(10.0, 15.0)
    assert abs_chg == 5.0
    assert pct_chg == 50.0
    assert chg == ChangeCategory.INCREASED

    # 2. Normal decrease: 10 -> 7.5 (-25.0%)
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(10.0, 7.5)
    assert abs_chg == -2.5
    assert pct_chg == -25.0
    assert chg == ChangeCategory.DECREASED

    # 3. Zero base increase: 0.0 -> 5.0
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(0.0, 5.0)
    assert abs_chg == 5.0
    assert pct_chg == 100.0
    assert chg == ChangeCategory.INCREASED

    # 4. Unchanged: 10.0 -> 10.0
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(10.0, 10.0)
    assert abs_chg == 0.0
    assert pct_chg == 0.0
    assert chg == ChangeCategory.UNCHANGED

    # 5. Missing previous: None -> 10.0
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(None, 10.0)
    assert abs_chg == 10.0
    assert pct_chg is None
    assert chg == ChangeCategory.NEW

    # 6. Missing current: 10.0 -> None
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(10.0, None)
    assert abs_chg is None
    assert pct_chg is None
    assert chg == ChangeCategory.DISCONTINUED

    # 7. Both None
    abs_chg, pct_chg, chg = comparator.calculate_numeric_change(None, None)
    assert abs_chg is None
    assert pct_chg is None
    assert chg == ChangeCategory.INSUFFICIENT_EVIDENCE


def test_17_evidence_traceability(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 17: All detected changes retain source document page, year, version, hash, and source."""
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    curr_profile.document_version = 2
    curr_profile.document_hash = "f9e8d7c6b5a43210"
    curr_profile.wash_spend_crore = 18.0

    result = verification_service.verify_changes(base_prev_profile, curr_profile)

    assert len(result.evidence) > 0
    for ev in result.evidence:
        assert ev.company == base_prev_profile.company
        assert ev.financial_year in ("2023-24", "2024-25")
        assert ev.document_version in (1, 2)
        if ev.financial_year == "2023-24":
            assert ev.document_hash == "a1b2c3d4e5f67890"
        elif ev.financial_year == "2024-25":
            assert ev.document_hash == "f9e8d7c6b5a43210"


def test_18_document_version_separation(verification_service: CSRChangeDetectionService, base_prev_profile: CSRDocumentProfile):
    """Test 18: Comparing v1 and v2 of same year preserves both headers without overwriting."""
    v1_profile = base_prev_profile.model_copy(deep=True)
    v1_profile.document_version = 1
    v1_profile.wash_spend_crore = 8.0

    v2_profile = base_prev_profile.model_copy(deep=True)
    v2_profile.document_version = 2
    v2_profile.wash_spend_crore = 10.0
    v2_profile.document_hash = "version2hash12345"

    result = verification_service.verify_changes(v1_profile, v2_profile)

    assert result.previous_document.document_version == 1
    assert result.current_document.document_version == 2
    assert result.previous_document.document_hash == "a1b2c3d4e5f67890"
    assert result.current_document.document_hash == "version2hash12345"
    assert result.comparison_period == "2023-24 -> 2023-24"
    assert result.verification_metadata["version_separation_preserved"] is True


def test_19_api_endpoint_verify_changes(base_prev_profile: CSRDocumentProfile):
    """Test 19: REST API endpoint POST /api/v1/documents/verify-changes returns 200 with complete results."""
    from fastapi.testclient import TestClient
    from ai_service.main import app

    client = TestClient(app)
    curr_profile = base_prev_profile.model_copy(deep=True)
    curr_profile.financial_year = "2024-25"
    curr_profile.wash_spend_crore = 15.0

    payload = {
        "previous_profile": base_prev_profile.model_dump(),
        "current_profile": curr_profile.model_dump(),
        "query_chromadb_if_needed": False,
    }

    response = client.post("/api/v1/documents/verify-changes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == base_prev_profile.company
    assert data["comparison_period"] == "2023-24 -> 2024-25"
    assert data["overall_wash_direction"] == "INCREASED"
    assert len(data["changes"]) > 0

