"""Tests for nse_annual_report_search service and tool."""

import asyncio
from mcp_server.services.nse_search import search_nse_annual_reports
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource


def test_nse_search_found():
    res = asyncio.run(search_nse_annual_reports(company_name="GAIL (INDIA) LIMITED"))
    assert res["source"] == DocumentSource.NSE.value
    assert len(res["documents"]) > 0
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.FOUND.value
    assert doc["document_type"] == DocumentType.ANNUAL_REPORT.value
    assert "gail" in doc["url"].lower() or "nseindia" in doc["url"].lower()
    assert doc["company_name"] == "GAIL (INDIA) LIMITED"


def test_nse_search_by_financial_year():
    res = asyncio.run(search_nse_annual_reports(company_name="INDIAN OIL CORPORATION LIMITED", financial_year="2023-24"))
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["financial_year"] == "2023-24"
    assert doc["status"] == DocumentStatus.FOUND.value


def test_nse_search_unlisted_company():
    res = asyncio.run(search_nse_annual_reports(company_name="CENTRAL COALFIELDS LIMITED"))
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.NOT_FOUND.value
    assert "not listed on nse" in doc["not_found_reason"].lower()


def test_nse_search_unknown_company():
    res = asyncio.run(search_nse_annual_reports(company_name="UNKNOWN CORP 12345"))
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.NOT_FOUND.value
    assert "not found in verified registry" in doc["not_found_reason"].lower()


def test_nse_search_empty_input():
    res = asyncio.run(search_nse_annual_reports())
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.ERROR.value
    assert "must be provided" in doc["error_message"].lower()
