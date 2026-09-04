"""
Company Search Service.
Finds candidate companies and returns identifying exchange and registry information.
"""

from typing import Any, Dict, Optional
from mcp_server.data.company_registry import find_in_registry


async def search_company(
    company_name: Optional[str] = None,
    symbol: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for a company by name or exchange symbol.
    Returns structured company identity information.
    """
    if not company_name and not symbol:
        return {
            "found": False,
            "reason": "Either company_name or symbol must be provided",
        }

    match = find_in_registry(company_name=company_name, symbol=symbol)
    if not match:
        target = company_name or symbol
        return {
            "found": False,
            "reason": f"Company not found in verified exchange or registry for '{target}'",
        }

    company, confidence, match_type = match
    exchange_str = "/".join(company.get("exchanges", [])) if company.get("exchanges") else "UNLISTED"

    source_name = source or ("NSE/BSE" if company.get("is_listed") else "MCA_REGISTRY")
    if company.get("is_listed") and company.get("symbol"):
        source_url = f"https://www.nseindia.com/get-quotes/equity?symbol={company['symbol']}"
    elif company.get("is_listed") and company.get("bse_scrip"):
        source_url = f"https://www.bseindia.com/stock-share-price/x/{company['bse_scrip']}/"
    else:
        source_url = company.get("website")

    return {
        "found": True,
        "company_name": company_name.strip() if company_name else company["company_name"],
        "matched_name": company["company_name"],
        "symbol": company.get("symbol"),
        "bse_scrip": company.get("bse_scrip"),
        "cin": company.get("cin"),
        "is_listed": company.get("is_listed", False),
        "exchange": exchange_str,
        "website": company.get("website"),
        "source": source_name,
        "source_url": source_url,
        "match_confidence": confidence,
    }
