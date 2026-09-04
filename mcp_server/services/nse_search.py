"""
NSE Annual Report Search Service.
Finds corporate annual reports filed on National Stock Exchange of India (NSE).
"""

from typing import Any, Dict, List, Optional
from mcp_server.contracts.document_contract import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    create_error_document,
    create_normalized_document,
    create_not_found_document,
)
from mcp_server.data.company_registry import find_in_registry


async def search_nse_annual_reports(
    company_name: Optional[str] = None,
    symbol: Optional[str] = None,
    financial_year: Optional[str] = None,
    from_year: Optional[str] = None,
    to_year: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Finds annual reports for a company on NSE.
    Returns normalized document metadata adhering to the standard contract.
    """
    target_name = (company_name or symbol or "UNKNOWN").strip()
    if not company_name and not symbol:
        return {
            "company_name": "UNKNOWN",
            "source": DocumentSource.NSE.value,
            "documents": [
                create_error_document(
                    company_name="UNKNOWN",
                    document_type=DocumentType.ANNUAL_REPORT.value,
                    source=DocumentSource.NSE.value,
                    error_message="Either company_name or symbol must be provided",
                )
            ],
        }

    match = find_in_registry(company_name=company_name, symbol=symbol)
    if not match:
        return {
            "company_name": target_name,
            "source": DocumentSource.NSE.value,
            "documents": [
                create_not_found_document(
                    company_name=target_name,
                    document_type=DocumentType.ANNUAL_REPORT.value,
                    source=DocumentSource.NSE.value,
                    financial_year=financial_year,
                    reason=f"Company '{target_name}' not found in verified registry or NSE listings",
                )
            ],
        }

    company, confidence, match_type = match

    if not company.get("is_listed") or not company.get("symbol"):
        return {
            "company_name": company["company_name"],
            "source": DocumentSource.NSE.value,
            "documents": [
                create_not_found_document(
                    company_name=company["company_name"],
                    document_type=DocumentType.ANNUAL_REPORT.value,
                    source=DocumentSource.NSE.value,
                    financial_year=financial_year,
                    reason=f"{company['company_name']} is not listed on NSE ({company.get('notes', 'Unlisted entity')})",
                )
            ],
        }

    available_reports = company.get("annual_reports", {})
    target_years = list(available_reports.keys())

    if financial_year:
        clean_fy = financial_year.replace("FY", "").replace("fy", "").strip()
        target_years = [
            y for y in target_years
            if y.lower() == clean_fy.lower() or y.lower() == financial_year.lower()
        ]

    matched_docs: List[Dict[str, Any]] = []
    for yr in target_years:
        rep = available_reports.get(yr)
        if rep:
            matched_docs.append(
                create_normalized_document(
                    company_name=company["company_name"],
                    document_type=DocumentType.ANNUAL_REPORT.value,
                    financial_year=yr,
                    title=rep.get("title"),
                    source=DocumentSource.NSE.value,
                    url=rep.get("nse_url") or rep.get("url"),
                    published_date=rep.get("published_date"),
                    status=DocumentStatus.FOUND.value,
                    metadata={"symbol": company.get("symbol"), "exchange": "NSE"},
                )
            )

    if not matched_docs:
        reason_msg = f"No annual report filings found on NSE for '{company['company_name']}'"
        if financial_year:
            reason_msg += f" for FY {financial_year}"
        return {
            "company_name": company["company_name"],
            "source": DocumentSource.NSE.value,
            "documents": [
                create_not_found_document(
                    company_name=company["company_name"],
                    document_type=DocumentType.ANNUAL_REPORT.value,
                    source=DocumentSource.NSE.value,
                    financial_year=financial_year,
                    reason=reason_msg,
                )
            ],
        }

    return {
        "company_name": company["company_name"],
        "source": DocumentSource.NSE.value,
        "documents": matched_docs,
    }
