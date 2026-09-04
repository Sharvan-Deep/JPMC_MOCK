"""
Comprehensive Test Suite for Task 10: CSR Freshness System.

Covers all 16 required test scenarios:
1. current verified WASH information -> GREEN
2. older information without newer verification -> YELLOW
3. verified LOST_FOCUS -> RED
4. missing current document -> YELLOW
5. insufficient evidence -> not RED
6. stable WASH focus -> GREEN when current verification succeeds
7. multiple sources
8. different document dates
9. missing publication date (never invent dates)
10. historical freshness records
11. status transition: YELLOW -> GREEN
12. status transition: GREEN -> RED
13. status transition: RED -> GREEN
14. verification cycle tracking (distinguish retrieval vs verification)
15. evidence traceability
16. no historical overwrite
Plus FastAPI endpoint integration tests.
"""

import pytest
from fastapi.testclient import TestClient
from ai_service.freshness.cycle import get_current_verification_cycle
from ai_service.freshness.repository import FreshnessRepository
from ai_service.freshness.rules import FreshnessRulesEngine
from ai_service.freshness.service import CSRFreshnessService
from ai_service.main import app
from ai_service.schemas.freshness import (
    FreshnessAssessment,
    FreshnessStatus,
    SourceFreshnessRecord,
    SourceType,
)
from ai_service.schemas.verification import (
    CSRChangeDetectionResult,
    CSRChangeItem,
    CSRDimensionsComparison,
    CSRDocumentProfile,
    CSREvidenceReference,
    CSRProjectSnapshot,
    DocumentSummaryHeader,
    GeographyComparison,
    PolicyComparison,
    ProjectComparison,
    SpendingComparison,
    VerificationConfidence,
    WASHDirection,
    WASHFocusComparison,
)


@pytest.fixture
def clean_repo(tmp_path) -> FreshnessRepository:
    """Provides a fresh, isolated repository for each test."""
    temp_file = str(tmp_path / "freshness_test_history.json")
    repo = FreshnessRepository(storage_path=temp_file)
    repo.clear()
    return repo


@pytest.fixture
def freshness_service(clean_repo: FreshnessRepository) -> CSRFreshnessService:
    return CSRFreshnessService(repository=clean_repo)


@pytest.fixture
def mock_evidence() -> CSREvidenceReference:
    return CSREvidenceReference(
        company="Tata Chemicals Limited",
        financial_year="2024-25",
        document_type="CSR_ANNUAL_REPORT",
        document_version=2,
        page=18,
        source_url="https://example.com/csr_2024_25.pdf",
        relevant_source_text="Drinking water RO filtration units established in 45 villages.",
        document_hash="hash_2024_25_abc123",
    )


# ==============================================================================
# 16 Core Requirements Tests
# ==============================================================================

def test_1_current_verified_wash_info_green(freshness_service: CSRFreshnessService, mock_evidence: CSREvidenceReference):
    """Test 1: Current information verified against latest available disclosure + WASH active -> GREEN."""
    assessment = freshness_service.calculate_freshness(
        company="Tata Chemicals Limited",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.INCREASED,
        primary_document_metadata={"document_type": "CSR_ANNUAL_REPORT", "publication_date": "2025-06-30"},
    )

    assert assessment.status == FreshnessStatus.GREEN
    assert "verified in current cycle" in assessment.reason.lower()
    assert assessment.verification_cycle == "2026-09"


def test_2_older_info_without_newer_verification_yellow(freshness_service: CSRFreshnessService):
    """Test 2: Information based on an older FY without new verification -> YELLOW (NEVER RED)."""
    assessment = freshness_service.calculate_freshness(
        company="Tata Chemicals Limited",
        verification_cycle="2026-09",
        financial_year="2022-23",
        is_current_reporting_cycle=False,  # Older financial year
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )

    assert assessment.status == FreshnessStatus.YELLOW
    assert assessment.status != FreshnessStatus.RED
    assert "older financial year" in assessment.reason.lower()


def test_3_verified_lost_focus_red(freshness_service: CSRFreshnessService, mock_evidence: CSREvidenceReference):
    """Test 3: Current verification provides evidence that WASH focus was discontinued/lost -> RED."""
    assessment = freshness_service.calculate_freshness(
        company="Tech Innovators Ltd",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.LOST_FOCUS,
    )

    assert assessment.status == FreshnessStatus.RED
    assert "discontinued/lost wash focus" in assessment.reason.lower()


def test_4_missing_current_document_yellow(freshness_service: CSRFreshnessService):
    """Test 4: Current year document is unavailable -> YELLOW (NEVER RED)."""
    assessment = freshness_service.calculate_freshness(
        company="Rural Water Corp",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        document_available=False,
        wash_direction=None,
    )

    assert assessment.status == FreshnessStatus.YELLOW
    assert assessment.status != FreshnessStatus.RED
    assert "unavailable" in assessment.reason.lower()


def test_5_insufficient_evidence_not_red(freshness_service: CSRFreshnessService):
    """Test 5: Insufficient evidence must NOT be marked RED (remains YELLOW)."""
    assessment = freshness_service.calculate_freshness(
        company="Obscure Enterprises",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.INSUFFICIENT_EVIDENCE,
    )

    assert assessment.status == FreshnessStatus.YELLOW
    assert assessment.status != FreshnessStatus.RED
    assert "insufficient evidence" in assessment.reason.lower()


def test_6_stable_wash_focus_green(freshness_service: CSRFreshnessService):
    """Test 6: Verified stable WASH focus in current cycle -> GREEN."""
    assessment = freshness_service.calculate_freshness(
        company="Clean Water India",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )

    assert assessment.status == FreshnessStatus.GREEN
    assert assessment.wash_direction == WASHDirection.STABLE


def test_7_multiple_sources(freshness_service: CSRFreshnessService):
    """Test 7: Evaluation across multiple sources (Annual Report, BRSR, CSR Policy)."""
    sources = [
        SourceFreshnessRecord(
            source_name="Annual Report FY25",
            document_type="CSR_ANNUAL_REPORT",
            financial_year="2024-25",
            publication_date="2025-07-15",
            status=FreshnessStatus.GREEN,
            reason="Primary verified disclosure",
        ),
        SourceFreshnessRecord(
            source_name="BRSR FY25",
            document_type="BRSR",
            financial_year="2024-25",
            publication_date="2025-07-20",
            status=FreshnessStatus.GREEN,
            reason="Secondary verified disclosure",
        ),
        SourceFreshnessRecord(
            source_name="CSR Policy",
            document_type="CSR_POLICY",
            publication_date="2021-04-01",
            status=FreshnessStatus.YELLOW,
            reason="Standing governance policy",
        ),
    ]

    assessment = freshness_service.calculate_freshness(
        company="MultiSource Corp",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.INCREASED,
        sources=sources,
    )

    assert assessment.status == FreshnessStatus.GREEN
    assert len(assessment.sources) == 3
    # Check that highest precedence source (CSR_ANNUAL_REPORT) drove the primary assessment
    assert assessment.document_type in ("CSR_ANNUAL_REPORT", "CSR_ANNUAL_REPORT")


def test_8_different_document_dates(freshness_service: CSRFreshnessService):
    """Test 8: Sources with different publication dates preserve individual dates without averaging."""
    sources = [
        SourceFreshnessRecord(
            source_name="CSR Policy",
            document_type="CSR_POLICY",
            publication_date="2020-01-10",
            status=FreshnessStatus.YELLOW,
        ),
        SourceFreshnessRecord(
            source_name="Annual Report 2024-25",
            document_type="CSR_ANNUAL_REPORT",
            publication_date="2025-06-30",
            status=FreshnessStatus.GREEN,
        ),
    ]

    assessment = freshness_service.calculate_freshness(
        company="Diverse Dates Ltd",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        wash_direction=WASHDirection.STABLE,
        sources=sources,
        publication_date="2025-06-30",
    )

    assert assessment.publication_date == "2025-06-30"
    policy_src = next(s for s in assessment.sources if s.document_type == "CSR_POLICY")
    assert policy_src.publication_date == "2020-01-10"


def test_9_missing_publication_date(freshness_service: CSRFreshnessService):
    """Test 9: Missing publication date is preserved as None without inventing dates."""
    assessment = freshness_service.calculate_freshness(
        company="Undated Sources Ltd",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T12:00:00Z",
        retrieved_at="2026-09-01T10:00:00Z",
        wash_direction=WASHDirection.STABLE,
        publication_date=None,  # No publication date available
    )

    assert assessment.publication_date is None
    assert assessment.retrieved_at == "2026-09-01T10:00:00Z"
    assert assessment.verified_at == "2026-09-04T12:00:00Z"
    assert assessment.financial_year == "2024-25"


def test_10_historical_freshness_records(freshness_service: CSRFreshnessService):
    """Test 10: Multiple assessments are stored historically and queryable in chronological order."""
    # Month 1: 2026-07 (Older report -> YELLOW)
    freshness_service.calculate_freshness(
        company="Historical Corp",
        verification_cycle="2026-07",
        financial_year="2023-24",
        is_current_reporting_cycle=False,
    )

    # Month 2: 2026-08 (New report verified -> GREEN)
    freshness_service.calculate_freshness(
        company="Historical Corp",
        verification_cycle="2026-08",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-08-15T10:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )

    history_resp = freshness_service.get_history("Historical Corp")
    assert len(history_resp.history) == 2
    assert history_resp.history[0].verification_cycle == "2026-07"
    assert history_resp.history[0].status == FreshnessStatus.YELLOW
    assert history_resp.history[1].verification_cycle == "2026-08"
    assert history_resp.history[1].status == FreshnessStatus.GREEN
    assert history_resp.current_status == FreshnessStatus.GREEN


def test_11_status_transition_yellow_to_green(freshness_service: CSRFreshnessService):
    """Test 11: Status transition from YELLOW to GREEN preserves previous status."""
    # Step 1: Initial state is YELLOW (awaiting new report)
    a1 = freshness_service.calculate_freshness(
        company="Transition Corp",
        verification_cycle="2026-08",
        financial_year="2023-24",
        is_current_reporting_cycle=False,
    )
    assert a1.status == FreshnessStatus.YELLOW
    assert a1.previous_status is None

    # Step 2: New FY25 report arrives and is verified -> GREEN
    a2 = freshness_service.calculate_freshness(
        company="Transition Corp",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T10:00:00Z",
        wash_direction=WASHDirection.INCREASED,
    )
    assert a2.status == FreshnessStatus.GREEN
    assert a2.previous_status == FreshnessStatus.YELLOW


def test_12_status_transition_green_to_red(freshness_service: CSRFreshnessService):
    """Test 12: Status transition from GREEN to RED when company abandons WASH."""
    # Step 1: Company is GREEN
    a1 = freshness_service.calculate_freshness(
        company="GreenToRed Corp",
        verification_cycle="2026-08",
        financial_year="2023-24",
        is_current_reporting_cycle=True,
        verified_at="2026-08-10T10:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )
    assert a1.status == FreshnessStatus.GREEN

    # Step 2: New report verified with LOST_FOCUS -> RED
    a2 = freshness_service.calculate_freshness(
        company="GreenToRed Corp",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T10:00:00Z",
        wash_direction=WASHDirection.LOST_FOCUS,
    )
    assert a2.status == FreshnessStatus.RED
    assert a2.previous_status == FreshnessStatus.GREEN


def test_13_status_transition_red_to_green(freshness_service: CSRFreshnessService):
    """Test 13: Status transition from RED back to GREEN when company restarts WASH."""
    # Step 1: Company was RED
    a1 = freshness_service.calculate_freshness(
        company="RedToGreen Corp",
        verification_cycle="2026-08",
        financial_year="2023-24",
        is_current_reporting_cycle=True,
        verified_at="2026-08-01T10:00:00Z",
        wash_direction=WASHDirection.LOST_FOCUS,
    )
    assert a1.status == FreshnessStatus.RED

    # Step 2: Company introduces new drinking water program in FY25 -> GREEN
    a2 = freshness_service.calculate_freshness(
        company="RedToGreen Corp",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T10:00:00Z",
        wash_direction=WASHDirection.NEW_FOCUS,
    )
    assert a2.status == FreshnessStatus.GREEN
    assert a2.previous_status == FreshnessStatus.RED


def test_14_verification_cycle_tracking(freshness_service: CSRFreshnessService):
    """Test 14: Distinguishes 'document retrieved' from 'document actually verified'."""
    # Document retrieved only (NOT verified yet) -> Cannot be GREEN
    unverified_assessment = freshness_service.calculate_freshness(
        company="Cycle Tracking Ltd",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        retrieved_at="2026-09-01T08:00:00Z",
        verified_at=None,  # Not verified yet!
        wash_direction=None,
    )
    assert unverified_assessment.status == FreshnessStatus.YELLOW
    assert "has not yet completed current-cycle verification" in unverified_assessment.reason

    # Later verified in cycle -> GREEN
    verified_assessment = freshness_service.calculate_freshness(
        company="Cycle Tracking Ltd",
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        retrieved_at="2026-09-01T08:00:00Z",
        verified_at="2026-09-04T15:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )
    assert verified_assessment.status == FreshnessStatus.GREEN
    assert verified_assessment.verified_at == "2026-09-04T15:00:00Z"


def test_15_evidence_traceability(freshness_service: CSRFreshnessService, mock_evidence: CSREvidenceReference):
    """Test 15: Freshness assessments retain full audit trail of evidence references."""
    # Create fake Task 9 result with evidence
    mock_result = CSRChangeDetectionResult(
        company="Tata Chemicals Limited",
        comparison_period="2023-24 -> 2024-25",
        overall_wash_direction=WASHDirection.INCREASED,
        dimensions=CSRDimensionsComparison(
            wash_focus=WASHFocusComparison(direction=WASHDirection.INCREASED),
            projects=ProjectComparison(change_type="CONTINUED"),
            spending=SpendingComparison(overall_change_type="INCREASED"),
            geography=GeographyComparison(direction="EXPANDED"),
            beneficiaries={"change_type": "UNCHANGED"},
            commitments={"change_type": "CONTINUED"},
            csr_policy={"wash_priority_status": "Maintained", "change_type": "UNCHANGED"},
        ),
        evidence=[mock_evidence],
    )

    assessment = freshness_service.calculate_freshness(
        company="Tata Chemicals Limited",
        verification_result=mock_result,
        verification_cycle="2026-09",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-09-04T10:00:00Z",
    )

    assert len(assessment.evidence) == 1
    ev = assessment.evidence[0]
    assert ev.page == 18
    assert ev.document_hash == "hash_2024_25_abc123"
    assert ev.source_url == "https://example.com/csr_2024_25.pdf"


def test_16_no_historical_overwrite(freshness_service: CSRFreshnessService):
    """Test 16: Adding new assessments does not mutate or overwrite previous records."""
    # Assessment 1
    a1 = freshness_service.calculate_freshness(
        company="Immutable Corp",
        verification_cycle="2026-07",
        financial_year="2023-24",
        is_current_reporting_cycle=False,
    )
    a1_id = a1.assessment_id

    # Assessment 2
    a2 = freshness_service.calculate_freshness(
        company="Immutable Corp",
        verification_cycle="2026-08",
        financial_year="2024-25",
        is_current_reporting_cycle=True,
        verified_at="2026-08-01T10:00:00Z",
        wash_direction=WASHDirection.STABLE,
    )
    a2_id = a2.assessment_id

    # Query full history
    history = freshness_service.repository.get_history("Immutable Corp")
    assert len(history) == 2
    assert history[0].assessment_id == a1_id
    assert history[0].status == FreshnessStatus.YELLOW
    assert history[1].assessment_id == a2_id
    assert history[1].status == FreshnessStatus.GREEN


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================

def test_17_freshness_api_endpoints():
    """Test 17: End-to-end FastAPI endpoint integration for freshness routes."""
    client = TestClient(app)

    # 1. POST /api/v1/freshness/calculate
    payload = {
        "company": "API Test Corp",
        "verification_cycle": "2026-09",
        "financial_year": "2024-25",
        "is_current_reporting_cycle": True,
        "wash_direction": "INCREASED",
        "has_wash_evidence": True,
        "primary_document": {
            "document_type": "CSR_ANNUAL_REPORT",
            "publication_date": "2025-07-01",
        },
    }
    calc_resp = client.post("/api/v1/freshness/calculate", json=payload)
    assert calc_resp.status_code == 200
    calc_data = calc_resp.json()
    assert calc_data["company"] == "API Test Corp"
    assert calc_data["status"] == "GREEN"

    # 2. GET /api/v1/freshness/{company}/current
    curr_resp = client.get("/api/v1/freshness/API Test Corp/current")
    assert curr_resp.status_code == 200
    curr_data = curr_resp.json()
    assert curr_data["status"] == "GREEN"

    # 3. GET /api/v1/freshness/{company}/history
    hist_resp = client.get("/api/v1/freshness/API Test Corp/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["current_status"] == "GREEN"
    assert len(hist_data["history"]) >= 1

    # 4. GET /api/v1/freshness/{company}/last-verified
    lv_resp = client.get("/api/v1/freshness/API Test Corp/last-verified")
    assert lv_resp.status_code == 200
    lv_data = lv_resp.json()
    assert lv_data["company"] == "API Test Corp"
