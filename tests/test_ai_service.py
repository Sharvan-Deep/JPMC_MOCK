"""
Unit and API integration tests for Task 3: Python AI/Data Service Foundation.
Tests configuration, schemas, health endpoint, document contract intake, and error handling.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from ai_service.config import Settings
from ai_service.main import app, create_app
from ai_service.schemas.document import DocumentInputSchema

client = TestClient(app)

SAMPLE_VALID_DOCUMENT = {
    "company_name": "INDIAN OIL CORPORATION LIMITED",
    "company_identifier": "IOC",
    "document_type": "annual_report",
    "financial_year": "2023-24",
    "title": "Indian Oil Annual Report 2023-24",
    "source": "NSE",
    "source_url": "https://archives.nseindia.com/corporate/annual/IOC_2023_2024.pdf",
    "local_file_path": "data/documents/annual_reports/INDIAN_OIL_annual_report_2023_24_v1_c3343c3d.pdf",
    "file_name": "INDIAN_OIL_annual_report_2023_24_v1_c3343c3d.pdf",
    "file_size": 15000000,
    "content_type": "application/pdf",
    "sha256": "c3343c3de9dd14ab0123456789abcdef0123456789abcdef0123456789abcdef",
    "version": 1,
    "is_latest": True,
    "published_date": "2024-07-26",
    "retrieved_at": "2026-09-04T14:30:00Z",
    "status": "FOUND",
}


# 1. Configuration Loading
def test_config_loading():
    settings = Settings(
        AI_SERVICE_HOST="127.0.0.1",
        AI_SERVICE_PORT=8080,
        AI_SERVICE_ENV="testing",
        DOCUMENTS_STORAGE_PATH="custom/docs",
    )
    assert settings.AI_SERVICE_HOST == "127.0.0.1"
    assert settings.AI_SERVICE_PORT == 8080
    assert settings.AI_SERVICE_ENV == "testing"
    assert settings.DOCUMENTS_STORAGE_PATH == "custom/docs"
    assert settings.SERVICE_NAME == "jaldhaara-ai-data-service"


# 2. Configuration Validation
def test_config_validation_invalid_port():
    with pytest.raises(ValueError):
        Settings(AI_SERVICE_PORT=99999)  # Port out of range


def test_config_validation_invalid_env():
    with pytest.raises(ValueError):
        Settings(AI_SERVICE_ENV="invalid_environment")


# 3. Service Startup Lifespan
def test_service_startup():
    test_app = create_app()
    with TestClient(test_app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# 4. GET /health and GET /api/v1/health
def test_health_endpoints():
    for endpoint in ["/health", "/api/v1/health"]:
        resp = client.get(endpoint)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "jaldhaara-ai-data-service"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data


# 5. Valid Document Metadata
def test_valid_document_metadata():
    doc = DocumentInputSchema(**SAMPLE_VALID_DOCUMENT)
    assert doc.company_name == "INDIAN OIL CORPORATION LIMITED"
    assert doc.document_type == "annual_report"
    assert doc.financial_year == "2023-24"
    assert doc.version == 1
    assert doc.sha256 == SAMPLE_VALID_DOCUMENT["sha256"]
    assert doc.status == "FOUND"


# 6. Invalid Document Metadata (missing required field)
def test_invalid_document_metadata_missing_company():
    invalid_data = dict(SAMPLE_VALID_DOCUMENT)
    del invalid_data["company_name"]
    with pytest.raises(ValueError):
        DocumentInputSchema(**invalid_data)


# 7. Invalid SHA-256 (length != 64 or non-hex)
def test_invalid_sha256_format():
    # Too short
    short_hash = dict(SAMPLE_VALID_DOCUMENT)
    short_hash["sha256"] = "abc1234"
    with pytest.raises(ValueError) as exc:
        DocumentInputSchema(**short_hash)
    assert "SHA-256" in str(exc.value)

    # Non-hex characters
    non_hex = dict(SAMPLE_VALID_DOCUMENT)
    non_hex["sha256"] = "z" * 64
    with pytest.raises(ValueError) as exc2:
        DocumentInputSchema(**non_hex)
    assert "SHA-256" in str(exc2.value)


# 8. Unsupported Document Type
def test_unsupported_document_type():
    bad_type = dict(SAMPLE_VALID_DOCUMENT)
    bad_type["document_type"] = "investor_presentation"
    with pytest.raises(ValueError) as exc:
        DocumentInputSchema(**bad_type)
    assert "Unsupported document_type" in str(exc.value)


# 9. Invalid Financial Year Format
def test_invalid_financial_year_format():
    bad_fy = dict(SAMPLE_VALID_DOCUMENT)
    bad_fy["financial_year"] = "invalid-year-12345"
    with pytest.raises(ValueError) as exc:
        DocumentInputSchema(**bad_fy)
    assert "Invalid financial_year format" in str(exc.value)


# 10. API Document Validation Success (POST /api/v1/documents/validate)
def test_api_document_validation_success():
    resp = client.post("/api/v1/documents/validate", json=SAMPLE_VALID_DOCUMENT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["company_name"] == "INDIAN OIL CORPORATION LIMITED"
    assert data["document_type"] == "annual_report"
    assert data["version"] == 1


# 11. API Document Validation Failure (HTTP 422 with structured error response)
def test_api_document_validation_failure():
    bad_payload = dict(SAMPLE_VALID_DOCUMENT)
    bad_payload["document_type"] = "invalid_type"
    resp = client.post("/api/v1/documents/validate", json=bad_payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"] == "Validation Error"
    assert "failed schema validation" in data["message"]
    assert len(data["details"]) > 0


# 12. API Error Handling (500 internal error masking without stack trace)
def test_api_error_handling_unhandled():
    test_client = TestClient(app, raise_server_exceptions=False)
    with patch(
        "ai_service.routes.documents.DocumentService.validate_document_contract",
        side_effect=Exception("Database or internal crash simulation"),
    ):
        resp = test_client.post("/api/v1/documents/validate", json=SAMPLE_VALID_DOCUMENT)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "Internal Server Error"
        # Ensure raw exception message and stack traces are NOT exposed in API response
        assert "Database or internal crash simulation" not in data["message"]
        assert "Traceback" not in str(data)
