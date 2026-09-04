"""Tests for brsr_search service and tool."""

import asyncio
from mcp_server.services.brsr_search import search_brsr
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource


def test_brsr_search_latest_available():
    res = asyncio.run(search_brsr(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert res["status"] == DocumentStatus.FOUND.value
    assert res["document_type"] == DocumentType.BRSR.value
    assert res["financial_year"] == "2023-24"
    assert "brsr" in res["url"].lower()


def test_brsr_search_tata_steel():
    res = asyncio.run(search_brsr(company_name="TATA STEEL LIMITED"))
    assert res["status"] == DocumentStatus.FOUND.value
    assert res["document_type"] == DocumentType.BRSR.value
    assert res["company_name"] == "TATA STEEL LIMITED"


def test_brsr_search_unlisted_company_not_found():
    res = asyncio.run(search_brsr(company_name="CENTRAL COALFIELDS LIMITED"))
    assert res["status"] == DocumentStatus.NOT_FOUND.value
    assert "not listed" in res["not_found_reason"].lower()


def test_brsr_search_empty_input():
    res = asyncio.run(search_brsr(company_name=""))
    assert res["status"] == DocumentStatus.ERROR.value
