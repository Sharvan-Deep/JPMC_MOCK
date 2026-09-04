"""Tests for bse_disclosure_search service and tool."""

import asyncio
from mcp_server.services.bse_search import search_bse_disclosures
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource


def test_bse_search_all_disclosures():
    res = asyncio.run(search_bse_disclosures(company_name="TATA STEEL LIMITED"))
    assert res["source"] == DocumentSource.BSE.value
    assert len(res["documents"]) > 0
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.FOUND.value
    assert doc["document_type"] == DocumentType.DISCLOSURE.value
    assert doc["source"] == DocumentSource.BSE.value


def test_bse_search_with_keyword_filter():
    res = asyncio.run(search_bse_disclosures(company_name="POWER GRID CORPORATION OF INDIA LIMITED", keyword="CSR"))
    assert len(res["documents"]) > 0
    for doc in res["documents"]:
        assert doc["status"] == DocumentStatus.FOUND.value
        title_or_cat = (doc.get("title", "") + " " + str(doc.get("metadata", {}).get("category", ""))).lower()
        assert "csr" in title_or_cat


def test_bse_search_unlisted_company():
    res = asyncio.run(search_bse_disclosures(company_name="CENTRAL COALFIELDS LIMITED"))
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.NOT_FOUND.value
    assert "not listed on bse" in doc["not_found_reason"].lower()


def test_bse_search_empty_input():
    res = asyncio.run(search_bse_disclosures(company_name=""))
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    assert doc["status"] == DocumentStatus.ERROR.value
