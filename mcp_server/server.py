"""
Jaldhaara Foundation AI CSR Donor Identification & Outreach System
MCP Server: Source Access & Document Retrieval Foundation

This server provides 6 structured MCP tools for researching candidate companies
and discovering their public CSR documents (annual reports, policies, BRSR, disclosures).
"""

import asyncio
import os
import sys
from typing import Any, Dict, Optional

from mcp.server.mcpserver import MCPServer

from mcp_server.services.company_search import search_company
from mcp_server.services.nse_search import search_nse_annual_reports
from mcp_server.services.bse_search import search_bse_disclosures
from mcp_server.services.csr_policy_search import search_csr_policy
from mcp_server.services.brsr_search import search_brsr
from mcp_server.services.document_metadata import get_document_metadata

# Initialize MCPServer
mcp = MCPServer(name="jaldhaara-csr-mcp", version="1.0.0")


@mcp.tool(
    name="company_search",
    description=(
        "Find an Indian company and return identifying information needed for "
        "subsequent document searches (NSE/BSE symbol, scrip code, official website, listing status)."
    ),
)
async def tool_company_search(
    company_name: Optional[str] = None,
    symbol: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for a company by name or exchange symbol.

    Args:
        company_name: Legal or commercial name of the company (e.g. 'INDIAN OIL CORPORATION LIMITED')
        symbol: Exchange ticker symbol (e.g. 'IOC', 'TATASTEEL')
        source: Optional source override
    """
    return await search_company(company_name=company_name, symbol=symbol, source=source)


@mcp.tool(
    name="nse_annual_report_search",
    description=(
        "Find corporate annual reports for a company filed on National Stock Exchange (NSE). "
        "Returns normalized document metadata adhering to the standard document contract."
    ),
)
async def tool_nse_annual_report_search(
    company_name: Optional[str] = None,
    symbol: Optional[str] = None,
    financial_year: Optional[str] = None,
    from_year: Optional[str] = None,
    to_year: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search NSE annual reports for a company.

    Args:
        company_name: Company name to search
        symbol: NSE ticker symbol if known
        financial_year: Target financial year, e.g. '2023-24' or 'FY2023-24'
        from_year: Starting financial year
        to_year: Ending financial year
    """
    return await search_nse_annual_reports(
        company_name=company_name,
        symbol=symbol,
        financial_year=financial_year,
        from_year=from_year,
        to_year=to_year,
    )


@mcp.tool(
    name="bse_disclosure_search",
    description=(
        "Search BSE corporate disclosures for a company (e.g., CSR announcements, "
        "annual reports, BRSR, sustainability filings). Returns structured disclosure metadata."
    ),
)
async def tool_bse_disclosure_search(
    company_name: str,
    financial_year: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search BSE corporate disclosures.

    Args:
        company_name: Company name to search (required)
        financial_year: Filter by financial year (e.g. '2023-24')
        keyword: Keyword filter (e.g. 'CSR', 'BRSR', 'annual report', 'sustainability')
    """
    return await search_bse_disclosures(
        company_name=company_name,
        financial_year=financial_year,
        keyword=keyword,
    )


@mcp.tool(
    name="csr_policy_search",
    description=(
        "Find the company's official CSR policy document. Search priority: "
        "1. Official company website 2. Investor/CSR section 3. Exchange disclosure. "
        "Distinguishes FOUND, NOT_FOUND, and ERROR strictly. Does not fabricate URLs."
    ),
)
async def tool_csr_policy_search(company_name: str) -> Dict[str, Any]:
    """
    Find official CSR policy for a company.

    Args:
        company_name: Company name to search (required)
    """
    return await search_csr_policy(company_name=company_name)


@mcp.tool(
    name="brsr_search",
    description=(
        "Find the company's latest available Business Responsibility and Sustainability Report (BRSR). "
        "Search priority: 1. NSE BRSR filing 2. BSE filing 3. Company official website."
    ),
)
async def tool_brsr_search(
    company_name: str,
    financial_year: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find latest available BRSR report.

    Args:
        company_name: Company name to search (required)
        financial_year: Optional target financial year (e.g. '2023-24')
    """
    return await search_brsr(company_name=company_name, financial_year=financial_year)


@mcp.tool(
    name="document_metadata",
    description=(
        "Return normalized metadata for a retrieved document. Validates and standardizes "
        "company, document type, financial year, source, URL, and status (FOUND, NOT_FOUND, ERROR)."
    ),
)
async def tool_document_metadata(
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    source: Optional[str] = None,
    financial_year: Optional[str] = None,
    title: Optional[str] = None,
    url: Optional[str] = None,
    published_date: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    not_found_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normalize document metadata for downstream processing.

    Args:
        company_name: Company name
        document_type: 'annual_report' | 'csr_policy' | 'brsr' | 'disclosure'
        source: 'NSE' | 'BSE' | 'COMPANY'
        financial_year: Financial year (e.g. '2023-24')
        title: Document title
        url: Public document URL
        published_date: Date of publication
        status: 'FOUND' | 'NOT_FOUND' | 'ERROR'
        error_message: Error explanation if status is ERROR
        not_found_reason: Explanation if status is NOT_FOUND
    """
    return get_document_metadata(
        company_name=company_name,
        document_type=document_type,
        source=source,
        financial_year=financial_year,
        title=title,
        url=url,
        published_date=published_date,
        status=status,
        error_message=error_message,
        not_found_reason=not_found_reason,
    )


def main():
    """Starts the MCP server on stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
