"""
Unit & Integration Tests for Task 6: AI/NLP CSR + WASH Classification.
Verifies context-aware classification:
- Safe drinking water, sanitation, and hygiene detection (WASH_RELEVANT)
- Industrial operational water exclusion (NOT_WASH_RELEVANT)
- Ambiguous rural watershed initiatives (PARTIALLY_RELEVANT)
- Non-WASH CSR activities (NOT_WASH_RELEVANT)
- Insufficient evidence handling (INSUFFICIENT_EVIDENCE)
- Provider abstraction, evidence snippet & page number preservation, and API endpoint
"""

import pytest
from fastapi.testclient import TestClient

from ai_service.classification.providers.factory import get_llm_provider
from ai_service.classification.providers.mock_provider import MockRuleBasedProvider
from ai_service.classification.service import CSRClassificationService
from ai_service.extraction.service import CSRExtractorService
from ai_service.main import app
from ai_service.preprocessing.service import CSRPreprocessingService
from ai_service.schemas.classification import (
    WASHClassificationEnum,
    WASHClassificationResult,
)
from ai_service.schemas.preprocessing import (
    CleanedCSRData,
    CleanedCSRRecord,
    CSRPreprocessingResult,
)


@pytest.fixture
def drinking_water_preprocessed() -> CSRPreprocessingResult:
    """Preprocessed fixture with strong safe drinking water CSR activity."""
    return CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "ABC INFRA", "financial_year": "2023-24"},
        cleaned_data=CleanedCSRData(
            canonical_company_name="ABC Infra",
            normalized_financial_year="2023-24",
            normalized_total_csr_amount_crore=15.50,
            records=[
                CleanedCSRRecord(
                    project_name="Jaldhaara Water Kiosk Initiative",
                    category="Safe Drinking Water",
                    location="Maharashtra (Palghar)",
                    raw_amount_spent="Rs. 4.20 Crores",
                    normalized_amount_spent_crore=4.20,
                    page_number=3,
                )
            ],
        ),
        cleaned_text_by_page={
            3: "The company installed 50 community reverse osmosis (RO) plants and safe drinking water kiosks."
        },
    )


@pytest.fixture
def sanitation_hygiene_preprocessed() -> CSRPreprocessingResult:
    """Preprocessed fixture with community sanitation and hygiene programs."""
    return CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "XYZ ENTERPRISE", "financial_year": "2023-24"},
        cleaned_data=CleanedCSRData(
            canonical_company_name="XYZ Enterprise",
            normalized_financial_year="2023-24",
            records=[
                CleanedCSRRecord(
                    project_name="Swachh Vidyalaya Toilet Blocks",
                    category="Sanitation",
                    location="Gujarat",
                    raw_amount_spent="Rs. 2.50 Crores",
                    normalized_amount_spent_crore=2.50,
                    page_number=5,
                ),
                CleanedCSRRecord(
                    project_name="Menstrual Hygiene Awareness & Handwashing Campaign",
                    category="Hygiene",
                    location="Rajasthan",
                    raw_amount_spent="Rs. 1.20 Crores",
                    normalized_amount_spent_crore=1.20,
                    page_number=7,
                ),
            ],
        ),
        cleaned_text_by_page={
            5: "Constructed separate sanitation facilities and community toilets for girls in 40 schools.",
            7: "Conducted menstrual hygiene management workshops and distributed hygiene supplies.",
        },
    )


@pytest.fixture
def industrial_water_preprocessed() -> CSRPreprocessingResult:
    """Preprocessed fixture with internal manufacturing water efficiency (NOT community WASH)."""
    return CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "STEEL METALS LTD", "financial_year": "2023-24"},
        cleaned_data=CleanedCSRData(
            canonical_company_name="Steel Metals",
            normalized_financial_year="2023-24",
            records=[
                CleanedCSRRecord(
                    project_name="Zero Liquid Discharge and Effluent Treatment Plant Upgrade",
                    category="Environmental Sustainability",
                    location="Plant Site",
                    raw_amount_spent="Rs. 18.00 Crores",
                    normalized_amount_spent_crore=18.00,
                    page_number=12,
                )
            ],
        ),
        cleaned_text_by_page={
            12: (
                "The factory achieved zero liquid discharge (ZLD) by upgrading our internal effluent treatment plant (ETP) "
                "and cooling water recycling circuit, reducing specific water consumption per ton of steel."
            )
        },
    )


@pytest.fixture
def non_wash_preprocessed() -> CSRPreprocessingResult:
    """Preprocessed fixture focusing on education, health, and sports (No WASH)."""
    return CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "TECH SERVE LIMITED", "financial_year": "2023-24"},
        cleaned_data=CleanedCSRData(
            canonical_company_name="Tech Serve",
            normalized_financial_year="2023-24",
            records=[
                CleanedCSRRecord(
                    project_name="Digital Literacy Centers in Rural High Schools",
                    category="Education",
                    location="Karnataka",
                    raw_amount_spent="Rs. 5.00 Crores",
                    normalized_amount_spent_crore=5.00,
                    page_number=2,
                )
            ],
        ),
        cleaned_text_by_page={
            2: "CSR expenditure focused on scholarships, smart classrooms, and mobile library buses."
        },
    )


# 1. Safe drinking water classification
def test_classify_drinking_water_csr(drinking_water_preprocessed):
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(drinking_water_preprocessed)

    assert res.classification == WASHClassificationEnum.WASH_RELEVANT.value
    assert res.confidence >= 0.85
    assert res.water_relevance is True
    assert len(res.evidence) > 0
    assert 3 in res.evidence_pages
    assert "Safe Drinking Water" in res.reasoning


# 2. Sanitation & Hygiene classification
def test_classify_sanitation_and_hygiene_csr(sanitation_hygiene_preprocessed):
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(sanitation_hygiene_preprocessed)

    assert res.classification == WASHClassificationEnum.WASH_RELEVANT.value
    assert res.confidence >= 0.85
    assert res.sanitation_relevance is True
    assert res.hygiene_relevance is True
    assert 5 in res.evidence_pages
    assert 7 in res.evidence_pages


# 3. Context-Aware Industrial Water Exclusion
def test_classify_industrial_water_exclusion(industrial_water_preprocessed):
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(industrial_water_preprocessed)

    # Must be NOT_WASH_RELEVANT because ETP/cooling water is operational plant compliance, NOT community WASH
    assert res.classification == WASHClassificationEnum.NOT_WASH_RELEVANT.value
    assert res.water_relevance is False
    assert res.confidence >= 0.80
    assert "industrial" in res.reasoning.lower() or "effluent" in res.reasoning.lower()

    # Evidence should record negative category
    neg_evidence = [e for e in res.evidence if e.category == "negative_industrial"]
    assert len(neg_evidence) > 0
    assert neg_evidence[0].strength == "NEGATIVE"


# 4. Non-WASH CSR Classification
def test_classify_non_wash_csr(non_wash_preprocessed):
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(non_wash_preprocessed)

    assert res.classification == WASHClassificationEnum.NOT_WASH_RELEVANT.value
    assert res.water_relevance is False
    assert res.sanitation_relevance is False
    assert res.confidence >= 0.80


# 5. Ambiguous rural watershed development (Partially relevant)
def test_classify_ambiguous_watershed_csr():
    prep = CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "AGRI CORP", "financial_year": "2023-24"},
        cleaned_data=CleanedCSRData(
            canonical_company_name="Agri Corp",
            records=[
                CleanedCSRRecord(
                    project_name="Rural Check Dam and Watershed Development",
                    category="Environment",
                    location="Madhya Pradesh",
                    raw_amount_spent="Rs. 3.00 Crores",
                    page_number=4,
                )
            ],
        ),
        cleaned_text_by_page={
            4: "Constructed village check dams and contour trenches for watershed development."
        },
    )
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(prep)

    assert res.classification == WASHClassificationEnum.PARTIALLY_RELEVANT.value
    assert 0.50 <= res.confidence <= 0.75
    assert "watershed" in res.reasoning.lower()


# 6. Insufficient evidence handling
def test_classify_insufficient_evidence():
    empty_prep = CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={},
        cleaned_data=CleanedCSRData(),
        cleaned_text_by_page={1: "   \n\n"},
    )
    service = CSRClassificationService(provider=MockRuleBasedProvider())
    res = service.classify_preprocessed_document(empty_prep)

    assert res.classification == WASHClassificationEnum.INSUFFICIENT_EVIDENCE.value
    assert res.confidence <= 0.20


# 7. Provider abstraction and factory
def test_provider_factory():
    provider = get_llm_provider()
    assert provider is not None
    assert hasattr(provider, "classify_csr_data")


# 8. Full End-to-End Pipeline: Task 4 -> Task 5 -> Task 6
def test_full_pipeline_task4_to_task6():
    # Step 1: Task 4 Extraction
    extractor = CSRExtractorService()
    extract_res = extractor.extract_from_file_path(
        "tests/fixtures/sample_csr_report.pdf",
        company_name="ABC INFRA LIMITED",
        financial_year="2023-24",
    )
    assert extract_res.status == "SUCCESS"

    # Step 2: Task 5 Preprocessing
    preprocessor = CSRPreprocessingService()
    prep_res = preprocessor.preprocess(extract_res)
    assert prep_res.status == "SUCCESS"
    assert prep_res.cleaned_data.canonical_company_name == "ABC Infra"
    assert len(prep_res.cleaned_data.records) == 2

    # Step 3: Task 6 Classification
    classifier = CSRClassificationService(provider=MockRuleBasedProvider())
    class_res = classifier.classify_preprocessed_document(prep_res)

    assert class_res.classification == WASHClassificationEnum.WASH_RELEVANT.value
    assert class_res.water_relevance is True
    assert class_res.sanitation_relevance is True
    assert class_res.confidence >= 0.85
    assert len(class_res.evidence) >= 2


# 9. API endpoint POST /api/v1/documents/classify
def test_api_classify_endpoint(drinking_water_preprocessed):
    client = TestClient(app)
    payload = drinking_water_preprocessed.model_dump()

    response = client.post("/api/v1/documents/classify", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["classification"] == "WASH_RELEVANT"
    assert data["water_relevance"] is True
    assert data["confidence"] >= 0.85
    assert len(data["evidence"]) > 0
