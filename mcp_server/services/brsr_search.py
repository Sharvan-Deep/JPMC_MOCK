"""
BRSR Search Service.
Finds Business Responsibility and Sustainability Reports (BRSR).
Search priority:
1. NSE BRSR filing
2. BSE filing
3. Company official website
"""

from typing import Any, Dict, Optional
from mcp_server.contracts.document_contract import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    create_error_document,
    create_normalized_document,
    create_not_found_document,
)
from mcp_server.data.company_registry import find_in_registry


async def search_brsr(
    company_name: Optional[str] = None,
    financial_year: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Finds the latest available BRSR report for a company.
    Distinguishes FOUND, NOT_FOUND, and ERROR strictly.
    """
    if not company_name or not company_name.strip():
        return create_error_document(
            company_name="UNKNOWN",
            document_type=DocumentType.BRSR.value,
            source=DocumentSource.NSE.value,
            error_message="company_name is required",
        )

    target_name = company_name.strip()
    match = find_in_registry(company_name=target_name)
    if not match:
        return create_not_found_document(
            company_name=target_name,
            document_type=DocumentType.BRSR.value,
            source=DocumentSource.NSE.value,
            reason=f"Company '{target_name}' not found in verified registry or exchange directories",
        )

    company, confidence, match_type = match

    if not company.get("is_listed"):
        return create_not_found_document(
            company_name=company["company_name"],
            document_type=DocumentType.BRSR.value,
            source=DocumentSource.NSE.value,
            reason=f"{company['company_name']} is not listed on NSE/BSE. BRSR is mandatory under SEBI regulations only for top listed entities.",
        )

    brsr_reports = company.get("brsr_reports", {})
    available_years = sorted(list(brsr_reports.keys()), reverse=True)

    selected_year = None
    if financial_year:
        clean_fy = financial_year.replace("FY", "").replace("fy", "").strip()
        for y in available_years:
            if y.lower() == clean_fy.lower() or y.lower() == financial_year.lower():
                selected_year = y
                break
    elif available_years:
        selected_year = available_years[0]

    if selected_year and selected_year in brsr_reports:
        rep = brsr_reports[selected_year]
        url = rep.get("url") or rep.get("bse_url")
        source = DocumentSource.NSE.value if url and "nseindia" in url else (
            DocumentSource.BSE.value if rep.get("bse_url") else DocumentSource.COMPANY.value
        )
        return create_normalized_document(
            company_name=company["company_name"],
            document_type=DocumentType.BRSR.value,
            financial_year=selected_year,
            title=rep.get("title"),
            source=source,
            url=url,
            published_date=rep.get("published_date"),
            status=DocumentStatus.FOUND.value,
            metadata={
                "symbol": company.get("symbol"),
                "bse_scrip": company.get("bse_scrip"),
            },
        )

    # Fallback to BSE disclosures if marked as BRSR
    for disc in company.get("disclosures", []):
        if (
            disc.get("category") == "BRSR"
            or "brsr" in disc.get("title", "").lower()
            or "business responsibility" in disc.get("title", "").lower()
        ):
            return create_normalized_document(
                company_name=company["company_name"],
                document_type=DocumentType.BRSR.value,
                financial_year=disc.get("financial_year"),
                title=disc.get("title"),
                source=DocumentSource.BSE.value,
                url=disc.get("url"),
                published_date=disc.get("date"),
                status=DocumentStatus.FOUND.value,
                metadata={"bse_scrip": company.get("bse_scrip")},
            )

    reason_msg = f"No BRSR filing found for '{company['company_name']}'"
    if financial_year:
        reason_msg += f" for FY {financial_year}"
    return create_not_found_document(
        company_name=company["company_name"],
        document_type=DocumentType.BRSR.value,
        source=DocumentSource.NSE.value,
        financial_year=financial_year,
        reason=reason_msg,
    )
