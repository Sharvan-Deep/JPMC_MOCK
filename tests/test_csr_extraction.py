"""
Unit & Integration Tests for Task 4: CSR Data Extraction.
Tests raw text and table extraction, CSR entity identification, raw data preservation,
OCR detection on scanned pages, validation gate enforcement, and error handling.
"""

from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF

from ai_service.extraction.pdf_extractor import PDFExtractor
from ai_service.extraction.csr_parser import CSRParser
from ai_service.extraction.service import CSRExtractorService
from ai_service.main import app
from ai_service.schemas.document import DocumentInputSchema
from mcp_server.retrieval.hasher import compute_sha256


@pytest.fixture(scope="session")
def sample_csr_pdf(tmp_path_factory) -> Path:
    """Generates a realistic valid CSR report PDF containing text and project tables."""
    tmp_dir = tmp_path_factory.mktemp("csr_data")
    pdf_path = tmp_dir / "sample_csr_report.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(text="Annual Report on CSR Activities of BHARAT INFRASTRUCTURE LIMITED", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(text="Financial Year: 2023-24", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Total CSR expenditure for the financial year: Rs. 24.50 Crores", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Brief Outline: Focus on Safe Drinking Water, Hygiene, and Sanitation across rural clusters.", new_x="LMARGIN", new_y="NEXT")

    # Table with standard Indian CSR Schedule VII reporting columns
    with pdf.table() as table:
        header_row = table.row()
        header_row.cell("Project Name")
        header_row.cell("Schedule VII Sector")
        header_row.cell("Location")
        header_row.cell("Amount Spent")
        header_row.cell("Mode of Implementation")

        row1 = table.row()
        row1.cell("Jaldhaara Clean Drinking Water Kiosks")
        row1.cell("Safe Drinking Water")
        row1.cell("Maharashtra (Palghar, Thane)")
        row1.cell("Rs. 8.50 Crores")
        row1.cell("Through Implementing Agency")

        row2 = table.row()
        row2.cell("Swachh Bharat School Sanitation Blocks")
        row2.cell("Sanitation & Hygiene")
        row2.cell("Gujarat (Navsari, Surat)")
        row2.cell("Rs. 6.20 Crores")
        row2.cell("Direct")

        row3 = table.row()
        row3.cell("Mobile Community Healthcare Units")
        row3.cell("Healthcare")
        row3.cell("Rajasthan (Barmer)")
        row3.cell("Rs. 4.00 Crores")
        row3.cell("Direct")

    pdf.output(str(pdf_path))
    return pdf_path


@pytest.fixture(scope="session")
def scanned_image_pdf(tmp_path_factory) -> Path:
    """Generates a scanned/image-only PDF with zero digital text layer to test OCR flagging."""
    tmp_dir = tmp_path_factory.mktemp("scanned_data")
    img_path = tmp_dir / "scanned_page.png"
    pdf_path = tmp_dir / "scanned_csr_report.pdf"

    # Create dummy white image
    img = Image.new("RGB", (300, 400), color="white")
    img.save(str(img_path))

    pdf = FPDF()
    pdf.add_page()
    pdf.image(str(img_path), x=10, y=10, w=180)
    pdf.output(str(pdf_path))
    return pdf_path


# 1. Successful extraction of text and tables from valid CSR PDF
def test_successful_csr_extraction(sample_csr_pdf):
    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(
        file_path=sample_csr_pdf,
        company_name="BHARAT INFRASTRUCTURE LIMITED",
        financial_year="2023-24",
    )

    assert res.status == "SUCCESS"
    assert res.ocr_required is False
    assert res.errors == []

    # Verify identified CSR fields
    identified = res.identified_csr_data
    assert identified.donor_name == "BHARAT INFRASTRUCTURE LIMITED"
    assert identified.financial_year == "2023-24"
    assert identified.total_csr_amount == "24.50 Crores"

    # Verify extracted projects from table
    assert len(identified.projects) == 3
    p1 = identified.projects[0]
    assert "Jaldhaara Clean" in p1.project_name and "Water" in p1.project_name
    assert p1.category == "Safe Drinking Water"
    assert "Maharashtra" in p1.location
    assert p1.amount_spent == "Rs. 8.50 Crores"
    assert p1.implementation_mode is not None and "Agency" in p1.implementation_mode


# 2. Raw table preservation and row/column structure integrity
def test_raw_table_preservation(sample_csr_pdf):
    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(sample_csr_pdf)

    raw_tables = res.raw_extracted_data.get("tables", [])
    assert len(raw_tables) == 1
    table = raw_tables[0]
    assert table["page_number"] == 1
    assert any("Project Name" in h for h in table["headers"])
    assert any("Schedule VII" in h for h in table["headers"])
    assert any("Amount Spent" in h for h in table["headers"])

    # Matrix rows preserved
    assert len(table["rows"]) == 3
    # Check that raw row dictionary is also preserved in project object
    proj1 = res.identified_csr_data.projects[0]
    assert proj1.raw_row_data is not None
    assert "Project Name" in proj1.raw_row_data
    assert "Amount Spent" in proj1.raw_row_data


# 3. Raw data preservation (No normalization or cleaning performed in Task 4)
def test_raw_values_not_normalized(sample_csr_pdf):
    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(sample_csr_pdf)

    # Monetary values must remain as raw strings, NOT normalized floats or ints
    assert isinstance(res.identified_csr_data.total_csr_amount, str)
    assert res.identified_csr_data.total_csr_amount == "24.50 Crores"

    for proj in res.identified_csr_data.projects:
        assert isinstance(proj.amount_spent, str)
        assert "Rs." in proj.amount_spent

    # Raw text by page preserved intact
    raw_text = res.raw_extracted_data["text_by_page"][1]
    assert "Annual Report on CSR Activities" in raw_text


# 4. Scanned/image-based PDF detection and OCR flagging
def test_scanned_image_pdf_detection(scanned_image_pdf):
    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(scanned_image_pdf, company_name="SCANNED CORP")

    assert res.status == "OCR_REQUIRED"
    assert res.ocr_required is True
    assert 1 in res.metadata.ocr_pages
    assert "OCR processing is required" in res.ocr_details
    assert len(res.identified_csr_data.projects) == 0


# 5. Missing PDF error handling
def test_missing_pdf_handling(tmp_path):
    missing_path = tmp_path / "non_existent.pdf"
    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(missing_path)

    assert res.status == "FAILED"
    assert any("not found" in err.lower() for err in res.errors)


# 6. Empty (0-byte) PDF error handling
def test_empty_pdf_handling(tmp_path):
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")

    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(empty_file)

    assert res.status == "FAILED"
    assert any("0 bytes" in err or "empty" in err for err in res.errors)


# 7. Invalid binary content (not a valid PDF)
def test_invalid_pdf_content(tmp_path):
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"<html><body>500 Internal Server Error</body></html>" * 5)

    extractor = CSRExtractorService()
    res = extractor.extract_from_file_path(fake_pdf)

    assert res.status == "FAILED"
    assert any("validation failed" in err.lower() for err in res.errors)


# 8. Task 3 Validation gate enforcement (invalid contract blocks extraction)
def test_validation_gate_blocked():
    extractor = CSRExtractorService()
    # Invalid document payload (empty company_name and invalid status)
    invalid_doc = {
        "company_name": "",
        "document_type": "annual_report",
        "financial_year": "2023-24",
        "source": "NSE",
    }
    res = extractor.extract_from_document(invalid_doc)
    assert res.status == "FAILED"
    assert any("schema validation" in err.lower() for err in res.errors)


# 9. API endpoint POST /api/v1/documents/extract
def test_api_extract_endpoint(sample_csr_pdf):
    client = TestClient(app)
    content = sample_csr_pdf.read_bytes()
    file_sha256 = compute_sha256(content)

    payload = {
        "company_name": "BHARAT INFRASTRUCTURE LIMITED",
        "document_type": "annual_report",
        "financial_year": "2023-24",
        "source": "LOCAL_FILE",
        "local_file_path": str(sample_csr_pdf),
        "file_name": sample_csr_pdf.name,
        "file_size": len(content),
        "sha256": file_sha256,
        "version": 1,
        "status": "FOUND",
    }

    response = client.post("/api/v1/documents/extract", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["ocr_required"] is False
    assert data["identified_csr_data"]["donor_name"] == "BHARAT INFRASTRUCTURE LIMITED"
    assert len(data["identified_csr_data"]["projects"]) == 3
    assert len(data["raw_extracted_data"]["tables"]) == 1


# 10. API endpoint rejects invalid document payload (HTTP 422)
def test_api_extract_endpoint_invalid_payload():
    client = TestClient(app)
    response = client.post("/api/v1/documents/extract", json={"invalid": "payload"})
    assert response.status_code == 422
