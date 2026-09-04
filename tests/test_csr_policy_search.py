"""Tests for csr_policy_search service and tool."""

import asyncio
from mcp_server.services.csr_policy_search import search_csr_policy
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource


def test_csr_policy_search_official_website():
    res = asyncio.run(search_csr_policy(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert res["status"] == DocumentStatus.FOUND.value
    assert res["document_type"] == DocumentType.CSR_POLICY.value
    assert res["source"] == DocumentSource.COMPANY.value
    assert "iocl.com" in res["url"]


def test_csr_policy_search_unlisted_psu():
    res = asyncio.run(search_csr_policy(company_name="CENTRAL COALFIELDS LIMITED"))
    assert res["status"] == DocumentStatus.FOUND.value
    assert res["document_type"] == DocumentType.CSR_POLICY.value
    assert "centralcoalfields.in" in res["url"]


def test_csr_policy_search_not_found():
    res = asyncio.run(search_csr_policy(company_name="GHOST ENTERPRISES LIMITED"))
    assert res["status"] == DocumentStatus.NOT_FOUND.value
    assert "not found" in res["not_found_reason"].lower()


def test_csr_policy_search_empty_input():
    res = asyncio.run(search_csr_policy(company_name=""))
    assert res["status"] == DocumentStatus.ERROR.value
    assert "company_name is required" in res["error_message"].lower()
