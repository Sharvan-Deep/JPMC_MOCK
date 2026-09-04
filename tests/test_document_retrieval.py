"""
Unit & Integration Tests for Task 2: Document Retrieval & Versioned Storage.
Covers all 15 required validation, hashing, versioning, error, and storage scenarios.
"""

from unittest.mock import MagicMock
import pytest
import requests

from mcp_server.retrieval.document_validator import validate_pdf_content
from mcp_server.retrieval.downloader import download_document_bytes
from mcp_server.retrieval.file_storage import (
    generate_versioned_filename,
    sanitize_filename_part,
    save_document_file,
)
from mcp_server.retrieval.hasher import compute_sha256
from mcp_server.retrieval.retriever_service import DocumentRetrieverService
from mcp_server.retrieval.version_manager import VersionManager

# Minimal valid PDF fixture (with valid %PDF- header and standard EOF trailer)
MINIMAL_VALID_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000118 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
)

# Altered valid PDF (for testing new version detection)
ALTERED_VALID_PDF = MINIMAL_VALID_PDF + b"\n% Additional Revision Data Added For Testing"


# 1. Successful PDF download test
def test_successful_pdf_download():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = MINIMAL_VALID_PDF
    mock_resp.headers = {"Content-Type": "application/pdf"}

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    status, content, ct, err = download_document_bytes(
        "https://example.com/valid_report.pdf", session=mock_session
    )
    assert status == "FOUND"
    assert content == MINIMAL_VALID_PDF
    assert ct == "application/pdf"
    assert err is None


# 2. Invalid HTTP response (404 and 500)
def test_invalid_http_response_404_and_500():
    # 404 -> NOT_FOUND
    mock_404 = MagicMock()
    mock_404.status_code = 404

    session_404 = MagicMock()
    session_404.get.return_value = mock_404

    status_404, content_404, _, err_404 = download_document_bytes(
        "https://example.com/missing.pdf", session=session_404
    )
    assert status_404 == "NOT_FOUND"
    assert content_404 is None
    assert "404" in err_404

    # 500 -> ERROR
    mock_500 = MagicMock()
    mock_500.status_code = 500

    session_500 = MagicMock()
    session_500.get.return_value = mock_500

    status_500, content_500, _, err_500 = download_document_bytes(
        "https://example.com/server_error.pdf", session=session_500
    )
    assert status_500 == "ERROR"
    assert content_500 is None
    assert "500" in err_500


# 3. Timeout handling
def test_timeout_handling():
    session_timeout = MagicMock()
    session_timeout.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    status, content, _, err = download_document_bytes(
        "https://example.com/timeout.pdf", session=session_timeout
    )
    assert status == "ERROR"
    assert content is None
    assert "timed out" in err.lower()


# 4. Empty response handling
def test_empty_response_handling():
    is_valid, err = validate_pdf_content(b"")
    assert is_valid is False
    assert "empty" in err.lower()


# 5. HTML instead of PDF rejection
def test_html_instead_of_pdf_rejection():
    html_content = b"<!DOCTYPE html><html><head><title>Error 404</title></head><body>File not found</body></html>"
    is_valid, err = validate_pdf_content(html_content, content_type="text/html")
    assert is_valid is False
    assert "html" in err.lower()


# 6. Invalid PDF (corrupt header) rejection
def test_invalid_pdf_corrupt_header():
    corrupt_data = b"RANDOM_BYTES_WITHOUT_PDF_HEADER_1234567890" * 5
    is_valid, err = validate_pdf_content(corrupt_data)
    assert is_valid is False
    assert "%pdf-" in err.lower() or "signature" in err.lower()


# 7. Valid PDF acceptance
def test_valid_pdf_acceptance():
    is_valid, err = validate_pdf_content(MINIMAL_VALID_PDF, content_type="application/pdf")
    assert is_valid is True
    assert err is None


# 8. SHA-256 generation accuracy
def test_sha256_generation():
    hash1 = compute_sha256(MINIMAL_VALID_PDF)
    assert isinstance(hash1, str)
    assert len(hash1) == 64
    # Determinism
    assert hash1 == compute_sha256(MINIMAL_VALID_PDF)

    # Different content produces different hash
    hash2 = compute_sha256(ALTERED_VALID_PDF)
    assert hash1 != hash2


# 9. Duplicate-content detection (same hash -> skip duplicate download)
def test_duplicate_content_detection(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "INDIAN OIL CORPORATION LIMITED",
        "document_type": "csr_policy",
        "financial_year": "2023-24",
        "source": "COMPANY",
        "url": "https://iocl.com/csr.pdf",
        "status": "FOUND",
    }

    # First retrieval -> CREATED
    res1 = service.process_document_retrieval(contract, custom_content=MINIMAL_VALID_PDF)
    assert res1["action"] == "CREATED"
    assert res1["version"] == 1

    # Second retrieval with identical content -> DUPLICATE_SKIPPED
    res2 = service.process_document_retrieval(contract, custom_content=MINIMAL_VALID_PDF)
    assert res2["action"] == "DUPLICATE_SKIPPED"
    assert res2["version"] == 1
    assert res2["sha256"] == res1["sha256"]

    # Verify only ONE PDF file exists on disk
    saved_files = list(tmp_path.rglob("*.pdf"))
    assert len(saved_files) == 1


# 10. Changed-content/new-version detection (different hash -> version increment)
def test_changed_content_new_version_detection(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "TATA STEEL LIMITED",
        "document_type": "annual_report",
        "financial_year": "2023-24",
        "source": "NSE",
        "url": "https://archives.nseindia.com/TATASTEEL.pdf",
        "status": "FOUND",
    }

    # Initial version v1
    res1 = service.process_document_retrieval(contract, custom_content=MINIMAL_VALID_PDF)
    assert res1["action"] == "CREATED"
    assert res1["version"] == 1
    assert res1["record"]["is_latest"] is True

    # Updated content for same company & year -> v2
    res2 = service.process_document_retrieval(contract, custom_content=ALTERED_VALID_PDF)
    assert res2["action"] == "NEW_VERSION_CREATED"
    assert res2["version"] == 2
    assert res2["record"]["is_latest"] is True

    # Check both versioned files exist on disk
    saved_files = list(tmp_path.rglob("*.pdf"))
    assert len(saved_files) == 2

    # Check that in the metadata index, v1 has is_latest=False and v2 has is_latest=True
    records = service.version_manager.find_records_for_document(
        company_name="TATA STEEL LIMITED",
        document_type="annual_report",
        financial_year="2023-24",
    )
    assert len(records) == 2
    assert records[0]["version"] == 1
    assert records[0]["is_latest"] is False
    assert records[1]["version"] == 2
    assert records[1]["is_latest"] is True


# 11. Filename sanitization
def test_filename_sanitization():
    dirty_name = "../../Unsafe<Company>:Name*With?Illegal|Chars\0"
    sanitized = sanitize_filename_part(dirty_name)
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "<" not in sanitized
    assert ":" not in sanitized
    assert "|" not in sanitized

    filename = generate_versioned_filename(
        company_name="GAIL (INDIA) LIMITED",
        document_type="annual_report",
        financial_year="2023-24",
        version=1,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    assert filename.endswith(".pdf")
    assert "GAIL" in filename
    assert "v1" in filename
    assert "e3b0c442" in filename


# 12. Metadata persistence & normalization
def test_metadata_persistence_fields(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "POWER GRID CORPORATION OF INDIA LIMITED",
        "document_type": "brsr",
        "financial_year": "2023-24",
        "title": "POWERGRID BRSR 2023-24",
        "source": "NSE",
        "url": "https://archives.nseindia.com/POWERGRID.pdf",
        "published_date": "2024-07-29",
        "status": "FOUND",
        "metadata": {"symbol": "POWERGRID"},
    }

    res = service.process_document_retrieval(contract, custom_content=MINIMAL_VALID_PDF)
    rec = res["record"]

    # Verify all required persistent metadata fields are recorded
    assert rec["company_name"] == "POWER GRID CORPORATION OF INDIA LIMITED"
    assert rec["company_identifier"] == "POWERGRID"
    assert rec["document_type"] == "brsr"
    assert rec["financial_year"] == "2023-24"
    assert rec["title"] == "POWERGRID BRSR 2023-24"
    assert rec["source"] == "NSE"
    assert rec["source_url"] == "https://archives.nseindia.com/POWERGRID.pdf"
    assert rec["file_name"].endswith(".pdf")
    assert rec["file_size"] == len(MINIMAL_VALID_PDF)
    assert rec["content_type"] == "application/pdf"
    assert rec["sha256"] == compute_sha256(MINIMAL_VALID_PDF)
    assert rec["version"] == 1
    assert rec["is_latest"] is True
    assert rec["published_date"] == "2024-07-29"
    assert rec["status"] == "FOUND"
    assert "retrieved_at" in rec
    assert "last_verified_at" in rec


# 13. NOT_FOUND handling
def test_not_found_handling(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "CENTRAL COALFIELDS LIMITED",
        "document_type": "annual_report",
        "source": "NSE",
        "status": "NOT_FOUND",
        "not_found_reason": "Company is unlisted on NSE",
    }

    res = service.process_document_retrieval(contract)
    assert res["status"] == "NOT_FOUND"
    assert res["action"] == "NOT_FOUND_RECORDED"
    assert res["record"]["error_information"] == "Company is unlisted on NSE"
    assert res["record"]["local_file_path"] is None


# 14. ERROR handling
def test_error_handling(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "BROKEN CORP",
        "document_type": "annual_report",
        "source": "NSE",
        "url": "https://broken.example.com/fail.pdf",
        "status": "FOUND",
    }

    # Pass HTML error response to trigger validation error
    html_error = b"<html><body>502 Bad Gateway</body></html>"
    res = service.process_document_retrieval(contract, custom_content=html_error)

    assert res["status"] == "ERROR"
    assert res["action"] == "VALIDATION_FAILED"
    assert "Validation failed" in res["record"]["error_information"]
    assert res["record"]["local_file_path"] is None


# 15. Retrieval timestamp verification
def test_retrieval_timestamp_present(tmp_path):
    service = DocumentRetrieverService(base_dir=tmp_path)
    contract = {
        "company_name": "NESTLE INDIA LIMITED",
        "document_type": "csr_policy",
        "source": "COMPANY",
        "url": "https://nestle.in/csr.pdf",
        "status": "FOUND",
    }

    res = service.process_document_retrieval(contract, custom_content=MINIMAL_VALID_PDF)
    rec = res["record"]
    assert "retrieved_at" in rec
    assert "T" in rec["retrieved_at"]  # Valid ISO string
    assert rec["last_verified_at"] == rec["retrieved_at"]
