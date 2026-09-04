"""Tests for document_metadata service and tool."""

import pytest
from mcp_server.services.document_metadata import get_document_metadata
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource


def test_document_metadata_valid_inputs():
    res = get_document_metadata(
        company_name="GAIL (INDIA) LIMITED",
        document_type="annual_report",
        source="NSE",
        financial_year="2023-24",
        title="GAIL Annual Report 2023-24",
        url="https://archives.nseindia.com/corporate/annual/GAIL_2023_2024.pdf",
        status="FOUND",
    )
    assert res["status"] == DocumentStatus.FOUND.value
    assert res["company_name"] == "GAIL (INDIA) LIMITED"
    assert res["document_type"] == DocumentType.ANNUAL_REPORT.value
    assert res["source"] == DocumentSource.NSE.value
    assert res["financial_year"] == "2023-24"
    assert "retrieved_date" in res


def test_document_metadata_type_normalization():
    # 'Annual Report' should normalize to 'annual_report'
    res = get_document_metadata(
        company_name="TATA STEEL LIMITED",
        document_type="Annual Report 2023-24",
        source="NSE",
        url="https://archives.nseindia.com/corporate/annual/TATASTEEL_2023_2024.pdf",
    )
    assert res["document_type"] == DocumentType.ANNUAL_REPORT.value

    # 'CSR Policy' should normalize to 'csr_policy'
    res_csr = get_document_metadata(
        company_name="TATA STEEL LIMITED",
        document_type="CSR Policy",
        source="Company Website",
        url="https://www.tatasteel.com/csr.pdf",
    )
    assert res_csr["document_type"] == DocumentType.CSR_POLICY.value


def test_document_metadata_error_handling():
    res = get_document_metadata(
        company_name="",
        document_type="annual_report",
    )
    assert res["status"] == DocumentStatus.ERROR.value
    assert "company_name is required" in res["error_message"].lower()


def test_document_metadata_not_found_handling():
    res = get_document_metadata(
        company_name="CENTRAL COALFIELDS LIMITED",
        document_type="brsr",
        source="NSE",
        not_found_reason="Company is unlisted",
    )
    assert res["status"] == DocumentStatus.NOT_FOUND.value
    assert "unlisted" in res["not_found_reason"].lower()
