"""
BSE Corporate Disclosure Search Service.
Searches BSE corporate disclosures and regulatory filings for candidate companies.
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


async def search_bse_disclosures(
    company_name: Optional[str] = None,
    financial_year: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search BSE corporate disclosures for a company.
    Supports keywords like CSR, annual report, BRSR, sustainability.
    """
    if not company_name or not company_name.strip():
        return {
            "company_name": "UNKNOWN",
            "source": DocumentSource.BSE.value,
            "documents": [
                create_error_document(
                    company_name="UNKNOWN",
                    document_type=DocumentType.DISCLOSURE.value,
                    source=DocumentSource.BSE.value,
                    error_message="company_name is required",
                )
            ],
        }

    target_name = company_name.strip()
    match = find_in_registry(company_name=target_name)
    if not match:
        return {
            "company_name": target_name,
            "source": DocumentSource.BSE.value,
            "documents": [
                create_not_found_document(
                    company_name=target_name,
                    document_type=DocumentType.DISCLOSURE.value,
                    source=DocumentSource.BSE.value,
                    financial_year=financial_year,
                    reason=f"Company '{target_name}' not found in verified registry or BSE listings",
                )
            ],
        }

    company, confidence, match_type = match

    if not company.get("is_listed") or not company.get("bse_scrip"):
        return {
            "company_name": company["company_name"],
            "source": DocumentSource.BSE.value,
            "documents": [
                create_not_found_document(
                    company_name=company["company_name"],
                    document_type=DocumentType.DISCLOSURE.value,
                    source=DocumentSource.BSE.value,
                    financial_year=financial_year,
                    reason=f"{company['company_name']} is not listed on BSE ({company.get('notes', 'Unlisted entity')})",
                )
            ],
        }

    matched_docs: List[Dict[str, Any]] = []
    disclosures = company.get("disclosures", [])

    for disc in disclosures:
        # Filter by financial_year
        if financial_year:
            clean_fy = financial_year.replace("FY", "").replace("fy", "").strip()
            disc_fy = (disc.get("financial_year") or "").replace("FY", "").replace("fy", "").strip()
            if disc_fy and disc_fy.lower() != clean_fy.lower() and disc.get("financial_year") != financial_year:
                continue

        # Filter by keyword
        if keyword:
            kw = keyword.lower().strip()
            title = disc.get("title", "").lower()
            category = (disc.get("category") or "").lower()
            if kw not in title and kw not in category:
                continue

        matched_docs.append(
            create_normalized_document(
                company_name=company["company_name"],
                document_type=DocumentType.DISCLOSURE.value,
                financial_year=disc.get("financial_year") or financial_year,
                title=disc.get("title"),
                source=DocumentSource.BSE.value,
                url=disc.get("url"),
                published_date=disc.get("date"),
                status=DocumentStatus.FOUND.value,
                metadata={
                    "bse_scrip": company.get("bse_scrip"),
                    "category": disc.get("category"),
                    "exchange": "BSE",
                },
            )
        )

    if not matched_docs:
        reason_msg = f"No corporate disclosures found on BSE for '{company['company_name']}'"
        if keyword:
            reason_msg += f" matching keyword '{keyword}'"
        if financial_year:
            reason_msg += f" for FY {financial_year}"
        return {
            "company_name": company["company_name"],
            "source": DocumentSource.BSE.value,
            "documents": [
                create_not_found_document(
                    company_name=company["company_name"],
                    document_type=DocumentType.DISCLOSURE.value,
                    source=DocumentSource.BSE.value,
                    financial_year=financial_year,
                    reason=reason_msg,
                )
            ],
        }

    return {
        "company_name": company["company_name"],
        "source": DocumentSource.BSE.value,
        "documents": matched_docs,
    }
