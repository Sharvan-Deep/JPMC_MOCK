"""
CSR Policy Search Service.
Finds the company's official Corporate Social Responsibility (CSR) policy.
Search priority:
1. Official company website
2. Official company investor/CSR section
3. NSE/BSE corporate disclosure if applicable
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


async def search_csr_policy(company_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for the verified CSR policy document for a company.
    Distinguishes FOUND, NOT_FOUND, and ERROR strictly.
    """
    if not company_name or not company_name.strip():
        return create_error_document(
            company_name="UNKNOWN",
            document_type=DocumentType.CSR_POLICY.value,
            source=DocumentSource.COMPANY.value,
            error_message="company_name is required",
        )

    target_name = company_name.strip()
    match = find_in_registry(company_name=target_name)
    if not match:
        return create_not_found_document(
            company_name=target_name,
            document_type=DocumentType.CSR_POLICY.value,
            source=DocumentSource.COMPANY.value,
            reason=f"Company '{target_name}' not found in verified registry or official directory",
        )

    company, confidence, match_type = match

    # 1. Primary: Official company website CSR policy
    if company.get("csr_policy_url"):
        return create_normalized_document(
            company_name=company["company_name"],
            document_type=DocumentType.CSR_POLICY.value,
            title=company.get("csr_policy_title") or f"{company['company_name']} Corporate Social Responsibility Policy",
            source=DocumentSource.COMPANY.value,
            url=company["csr_policy_url"],
            status=DocumentStatus.FOUND.value,
            metadata={
                "official_website": company.get("website"),
                "cin": company.get("cin"),
            },
        )

    # 2. Secondary: Exchange disclosures
    for disc in company.get("disclosures", []):
        if disc.get("category") == "CSR" or "csr policy" in disc.get("title", "").lower():
            return create_normalized_document(
                company_name=company["company_name"],
                document_type=DocumentType.CSR_POLICY.value,
                financial_year=disc.get("financial_year"),
                title=disc.get("title"),
                source=DocumentSource.BSE.value,
                url=disc.get("url"),
                published_date=disc.get("date"),
                status=DocumentStatus.FOUND.value,
                metadata={"source_type": "exchange_disclosure"},
            )

    return create_not_found_document(
        company_name=company["company_name"],
        document_type=DocumentType.CSR_POLICY.value,
        source=DocumentSource.COMPANY.value,
        reason=f"No verified official CSR policy document found for '{company['company_name']}'",
    )
