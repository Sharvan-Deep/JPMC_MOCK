"""Tests for company_search service and tool."""

import asyncio
from mcp_server.services.company_search import search_company


def test_company_search_exact_name():
    res = asyncio.run(search_company(company_name="INDIAN OIL CORPORATION LIMITED"))
    assert res["found"] is True
    assert res["symbol"] == "IOC"
    assert res["bse_scrip"] == "530965"
    assert res["is_listed"] is True
    assert "NSE" in res["exchange"]
    assert res["match_confidence"] == 1.0


def test_company_search_alias():
    res = asyncio.run(search_company(company_name="IOCL"))
    assert res["found"] is True
    assert res["matched_name"] == "INDIAN OIL CORPORATION LIMITED"
    assert res["symbol"] == "IOC"
    assert res["match_confidence"] >= 0.90


def test_company_search_symbol():
    res = asyncio.run(search_company(symbol="TATASTEEL"))
    assert res["found"] is True
    assert res["matched_name"] == "TATA STEEL LIMITED"
    assert res["bse_scrip"] == "500470"


def test_company_search_unlisted_psu():
    res = asyncio.run(search_company(company_name="CENTRAL COALFIELDS LIMITED"))
    assert res["found"] is True
    assert res["is_listed"] is False
    assert res["symbol"] is None
    assert res["exchange"] == "UNLISTED"
    assert res["website"] == "https://www.centralcoalfields.in"


def test_company_search_not_found():
    res = asyncio.run(search_company(company_name="NON_EXISTENT_ENTERPRISE_XYZ"))
    assert res["found"] is False
    assert "not found" in res["reason"].lower()


def test_company_search_missing_input():
    res = asyncio.run(search_company())
    assert res["found"] is False
    assert "either company_name or symbol" in res["reason"].lower()
