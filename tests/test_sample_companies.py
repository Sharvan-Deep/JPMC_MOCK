"""
Integration-style tests verifying source discovery and document retrieval across
sample Top 500 candidate companies (listed and unlisted).
"""

import asyncio
import pytest
from mcp_server.services.company_search import search_company
from mcp_server.services.nse_search import search_nse_annual_reports
from mcp_server.services.bse_search import search_bse_disclosures
from mcp_server.services.csr_policy_search import search_csr_policy
from mcp_server.services.brsr_search import search_brsr
from mcp_server.contracts.document_contract import DocumentStatus, DocumentType, DocumentSource

SAMPLE_COMPANIES = [
    "INDIAN OIL CORPORATION LIMITED",
    "CENTRAL COALFIELDS LIMITED",
    "GAIL (INDIA) LIMITED",
    "TATA STEEL LIMITED",
    "POWER GRID CORPORATION OF INDIA LIMITED",
    "HINDUSTAN ZINC LIMITED",
    "REC LIMITED",
    "NESTLE INDIA LIMITED",
]


@pytest.mark.parametrize("company_name", SAMPLE_COMPANIES)
def test_sample_company_search(company_name):
    res = asyncio.run(search_company(company_name=company_name))
    assert res["found"] is True
    assert res["matched_name"] == company_name
    assert res["match_confidence"] >= 0.90


@pytest.mark.parametrize("company_name", SAMPLE_COMPANIES)
def test_sample_csr_policy_retrieval(company_name):
    res = asyncio.run(search_csr_policy(company_name=company_name))
    assert res["status"] in [DocumentStatus.FOUND.value, DocumentStatus.NOT_FOUND.value]
    assert res["document_type"] == DocumentType.CSR_POLICY.value
    if res["status"] == DocumentStatus.FOUND.value:
        assert res["url"] is not None
        assert res["url"].startswith("http")


def test_unlisted_vs_listed_behavior():
    # Central Coalfields Limited (unlisted PSU subsidiary):
    # - Company search succeeds
    # - CSR policy found on official website
    # - NSE annual report returns NOT_FOUND (graceful handling, not error)
    # - BSE disclosure returns NOT_FOUND (graceful handling, not error)
    # - BRSR returns NOT_FOUND (graceful handling, not error)
    ccl_search = asyncio.run(search_company(company_name="CENTRAL COALFIELDS LIMITED"))
    assert ccl_search["found"] is True
    assert ccl_search["is_listed"] is False

    ccl_csr = asyncio.run(search_csr_policy(company_name="CENTRAL COALFIELDS LIMITED"))
    assert ccl_csr["status"] == DocumentStatus.FOUND.value
    assert "centralcoalfields" in ccl_csr["url"]

    ccl_nse = asyncio.run(search_nse_annual_reports(company_name="CENTRAL COALFIELDS LIMITED"))
    assert ccl_nse["documents"][0]["status"] == DocumentStatus.NOT_FOUND.value
    assert "not listed" in ccl_nse["documents"][0]["not_found_reason"].lower()

    ccl_bse = asyncio.run(search_bse_disclosures(company_name="CENTRAL COALFIELDS LIMITED"))
    assert ccl_bse["documents"][0]["status"] == DocumentStatus.NOT_FOUND.value

    ccl_brsr = asyncio.run(search_brsr(company_name="CENTRAL COALFIELDS LIMITED"))
    assert ccl_brsr["status"] == DocumentStatus.NOT_FOUND.value

    # Indian Oil Corporation Limited (listed Maharatna PSU):
    # - Company search succeeds
    # - NSE annual report found
    # - BSE disclosure found
    # - CSR policy found
    # - BRSR found
    iocl_nse = asyncio.run(search_nse_annual_reports(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert iocl_nse["documents"][0]["status"] == DocumentStatus.FOUND.value

    iocl_bse = asyncio.run(search_bse_disclosures(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert iocl_bse["documents"][0]["status"] == DocumentStatus.FOUND.value

    iocl_csr = asyncio.run(search_csr_policy(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert iocl_csr["status"] == DocumentStatus.FOUND.value

    iocl_brsr = asyncio.run(search_brsr(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert iocl_brsr["status"] == DocumentStatus.FOUND.value
