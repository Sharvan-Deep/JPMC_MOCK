"""
Unit & Integration Tests for Task 5: CSR Data Preprocessing & Cleaning.
Verifies text cleaning, whitespace normalization, header/footer artifact removal,
deterministic field normalization (Crores, FY, company name), table cleaning,
duplicate extraction row filtering, and raw value preservation.
"""

import pytest
from fastapi.testclient import TestClient

from ai_service.main import app
from ai_service.preprocessing.cleaner import TextCleaner
from ai_service.preprocessing.normalizer import FieldNormalizer
from ai_service.preprocessing.table_cleaner import TableCleaner
from ai_service.preprocessing.service import CSRPreprocessingService
from ai_service.schemas.extraction import (
    CSRExtractionResult,
    CSRProjectRaw,
    CSRTableRaw,
    IdentifiedCSRData,
)


@pytest.fixture
def sample_raw_extraction() -> CSRExtractionResult:
    """Fixture providing a mock Task 4 CSRExtractionResult."""
    return CSRExtractionResult(
        status="SUCCESS",
        document_metadata={
            "company_name": "BHARAT INFRASTRUCTURE LIMITED",
            "document_type": "annual_report",
            "financial_year": "FY 2023-24",
        },
        identified_csr_data=IdentifiedCSRData(
            donor_name="BHARAT INFRASTRUCTURE LIMITED",
            financial_year="FY 2023-24",
            total_csr_amount="Rs. 24.50 Crores",
            projects=[
                CSRProjectRaw(
                    project_name="Jaldhaara Clean Drinking Water Kiosks",
                    category="Safe Drinking Water",
                    location="Maharashtra (Palghar)",
                    amount_spent="Rs. 8.50 Crores",
                    amount_allocated="1000 Lakhs",
                    beneficiaries="50,000 villagers",
                    implementation_mode="Implementing Agency",
                    page_number=1,
                    raw_row_data={"Project": "Water Kiosks", "Amount": "Rs. 8.50 Crores"},
                ),
                CSRProjectRaw(
                    project_name="Swachh School Sanitation Blocks",
                    category="Sanitation & Hygiene",
                    location="Gujarat (Navsari)",
                    amount_spent="620 Lakhs",
                    amount_allocated="7.00 Cr",
                    beneficiaries="12,000 students",
                    implementation_mode="Direct",
                    page_number=1,
                ),
                # Extraction duplicate of the sanitation project (as often happens across multi-page tables)
                CSRProjectRaw(
                    project_name="Swachh School Sanitation Blocks",
                    category="Sanitation & Hygiene",
                    location="Gujarat (Navsari)",
                    amount_spent="620 Lakhs",
                    page_number=2,
                ),
            ],
        ),
        raw_extracted_data={
            "text_by_page": {
                1: "--- Page 1 ---\nAnnual Report on CSR   Activities\n\n\n\nPage 1 of 12\nTotal spent: Rs. 24.50 Crores",
                2: "--- Page 2 ---\nDetails of projects continued\nPage 2 of 12",
            },
            "tables": [
                {
                    "page_number": 1,
                    "table_index": 0,
                    "headers": ["Project Name", "Category", "Amount Spent", ""],
                    "rows": [
                        ["Water Kiosks", "Safe Drinking Water", "Rs. 8.50 Crores", None],
                        [None, None, None, None],  # Completely empty row
                        ["Sanitation Blocks", "Sanitation", "620 Lakhs", None],
                    ],
                }
            ],
        },
    )


# 1. Text cleaner: whitespace and artifact removal
def test_text_cleaner_whitespace_and_artifacts():
    cleaner = TextCleaner()
    raw = (
        "--- Page 1 ---\n"
        "Annual   Report    on CSR Activities  \n\n\n\n"
        "   Page 1 of 10   \n"
        "Safe  Drinking   Water Program\n"
        "- 1 -\n"
    )
    cleaned = cleaner.clean_page_text(raw)

    assert "--- Page 1 ---" not in cleaned
    assert "Page 1 of 10" not in cleaned
    assert "- 1 -" not in cleaned
    assert "Annual Report on CSR Activities" in cleaned
    assert "Safe Drinking Water Program" in cleaned
    # Check that multiple consecutive blank lines collapsed
    assert "\n\n\n" not in cleaned


# 2. Text cleaner: repeated multi-page header/footer detection
def test_text_cleaner_repeated_headers():
    cleaner = TextCleaner()
    pages = {
        1: "Company Confidential Filing\nContent on page 1\nFooter Notice",
        2: "Company Confidential Filing\nContent on page 2\nFooter Notice",
        3: "Company Confidential Filing\nContent on page 3\nFooter Notice",
    }
    cleaned_pages, warnings = cleaner.clean_text_by_page(pages)

    assert len(cleaned_pages) == 3
    for p in cleaned_pages.values():
        assert "Company Confidential Filing" not in p
        assert "Footer Notice" not in p
        assert "Content on page" in p
    assert len(warnings) > 0


# 3. Normalizer: Currency amounts to INR Crores with raw preservation
def test_amount_normalizer_crores_conversion():
    norm = FieldNormalizer()

    # Crores representations
    val, raw = norm.normalize_amount_to_crores("₹ 12.50 Cr")
    assert val == 12.50
    assert raw == "₹ 12.50 Cr"

    val, raw = norm.normalize_amount_to_crores("Rs. 24.50 Crores")
    assert val == 24.50

    # Lakhs representations (100 Lakhs = 1 Crore)
    val, raw = norm.normalize_amount_to_crores("1250 Lakhs")
    assert val == 12.50

    val, raw = norm.normalize_amount_to_crores("620 Lakhs")
    assert val == 6.20

    val, raw = norm.normalize_amount_to_crores("50 Lacs")
    assert val == 0.50

    # Raw INR numbers (>= 10,000 / 10,000,000)
    val, raw = norm.normalize_amount_to_crores("50,00,000")
    assert val == 0.50

    val, raw = norm.normalize_amount_to_crores("50000")
    assert val == 0.005

    # Nil / N/A / Zero
    val, raw = norm.normalize_amount_to_crores("Nil")
    assert val == 0.0

    # Ambiguous or non-numeric string
    val, raw = norm.normalize_amount_to_crores("To be decided")
    assert val is None
    assert raw == "To be decided"


# 4. Normalizer: Financial year standardization
def test_fy_normalizer():
    norm = FieldNormalizer()

    val, raw = norm.normalize_financial_year("FY 2023-24")
    assert val == "2023-24"
    assert raw == "FY 2023-24"

    val, _ = norm.normalize_financial_year("2023-2024")
    assert val == "2023-24"

    val, _ = norm.normalize_financial_year("FY24-25")
    assert val == "2024-25"

    val, _ = norm.normalize_financial_year("ended 31st March 2024")
    assert val == "2023-24"

    val, _ = norm.normalize_financial_year("general")
    assert val == "general"


# 5. Normalizer: Canonical company representation
def test_company_normalizer():
    norm = FieldNormalizer()

    canonical, raw = norm.normalize_company_name("BHARAT INFRASTRUCTURE LIMITED")
    assert canonical == "Bharat Infrastructure"
    assert raw == "BHARAT INFRASTRUCTURE LIMITED"

    canonical, _ = norm.normalize_company_name("Tata Steel Ltd.")
    assert canonical == "Tata Steel"

    canonical, _ = norm.normalize_company_name("GAIL (INDIA) LIMITED")
    assert canonical == "Gail (India)"

    # Acronyms preserved in uppercase
    canonical, _ = norm.normalize_company_name("TCS LIMITED")
    assert canonical == "TCS"


# 6. Table cleaner: Empty rows and columns pruning
def test_table_cleaner_pruning():
    cleaner = TableCleaner()
    raw_table = CSRTableRaw(
        page_number=1,
        table_index=0,
        headers=["Project", "Category", "Amount", ""],
        rows=[
            ["Water Kiosks", "Water", "Rs. 5 Cr", None],
            [None, None, None, None],  # Empty row
            ["Sanitation", "Sanitation", "Rs. 3 Cr", "   "],
        ],
    )
    cleaned = cleaner.clean_table(raw_table)

    assert len(cleaned.rows) == 2
    # 4th column was completely empty and should be dropped
    assert len(cleaned.headers) == 3
    assert cleaned.headers == ["Project", "Category", "Amount"]
    assert cleaned.rows[0] == ["Water Kiosks", "Water", "Rs. 5 Cr"]


# 7. Duplicate extraction row filtering
def test_duplicate_row_filtering(sample_raw_extraction):
    service = CSRPreprocessingService()
    res = service.preprocess(sample_raw_extraction)

    assert res.status == "SUCCESS"
    # Originally 3 projects in fixture, 1 duplicate
    assert res.metadata.raw_records_count == 3
    assert res.metadata.cleaned_records_count == 2
    assert res.metadata.duplicates_removed == 1


# 8. Complete Preprocessing Service End-to-End
def test_preprocessing_service_end_to_end(sample_raw_extraction):
    service = CSRPreprocessingService()
    res = service.preprocess(sample_raw_extraction)

    assert res.status == "SUCCESS"
    cleaned_data = res.cleaned_data

    # Company and FY
    assert cleaned_data.canonical_company_name == "Bharat Infrastructure"
    assert cleaned_data.raw_company_name == "BHARAT INFRASTRUCTURE LIMITED"
    assert cleaned_data.normalized_financial_year == "2023-24"
    assert cleaned_data.normalized_total_csr_amount_crore == 24.50
    assert cleaned_data.raw_total_csr_amount == "Rs. 24.50 Crores"

    # Records
    rec1 = cleaned_data.records[0]
    assert rec1.project_name == "Jaldhaara Clean Drinking Water Kiosks"
    assert rec1.normalized_amount_spent_crore == 8.50
    assert rec1.raw_amount_spent == "Rs. 8.50 Crores"
    assert rec1.normalized_amount_allocated_crore == 10.00  # 1000 Lakhs = 10 Cr
    assert rec1.page_number == 1
    assert rec1.raw_project is not None

    # Text mapping preserved
    assert 1 in res.cleaned_text_by_page
    assert 2 in res.cleaned_text_by_page
    assert "Annual Report on CSR Activities" in res.cleaned_text_by_page[1]


# 9. Preprocessing malformed input handling
def test_preprocessing_malformed_input():
    service = CSRPreprocessingService()
    malformed_input = {"invalid": "schema", "status": "UNKNOWN"}
    res = service.preprocess(malformed_input)

    assert res.status == "FAILED"
    assert len(res.errors) > 0


# 10. API endpoint POST /api/v1/documents/preprocess
def test_api_preprocess_endpoint(sample_raw_extraction):
    client = TestClient(app)
    payload = sample_raw_extraction.model_dump()

    response = client.post("/api/v1/documents/preprocess", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["cleaned_data"]["canonical_company_name"] == "Bharat Infrastructure"
    assert data["cleaned_data"]["normalized_total_csr_amount_crore"] == 24.50
    assert len(data["cleaned_data"]["records"]) == 2
    assert data["metadata"]["duplicates_removed"] == 1
