"""
Demonstration script executing document retrieval tools on candidate companies
from the Top 500 queue and printing structured, normalized outputs.
"""

import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_server.services.company_search import search_company
from mcp_server.services.nse_search import search_nse_annual_reports
from mcp_server.services.bse_search import search_bse_disclosures
from mcp_server.services.csr_policy_search import search_csr_policy
from mcp_server.services.brsr_search import search_brsr

SAMPLE_COMPANIES = [
    "INDIAN OIL CORPORATION LIMITED",
    "CENTRAL COALFIELDS LIMITED",
    "GAIL (INDIA) LIMITED",
    "TATA STEEL LIMITED",
    "POWER GRID CORPORATION OF INDIA LIMITED",
]


async def run_demonstration():
    print("=" * 70)
    print("JALDHAARA FOUNDATION - CSR DOCUMENT MCP RETRIEVAL RUN")
    print("=" * 70)

    for company in SAMPLE_COMPANIES:
        print(f"\n[{company}]")
        print("-" * 50)

        # 1. Company Search
        c_info = await search_company(company_name=company)
        print(f"  1. Company Search: Found={c_info.get('found')} | Symbol={c_info.get('symbol')} | Listed={c_info.get('is_listed')}")

        # 2. CSR Policy Search
        csr = await search_csr_policy(company_name=company)
        print(f"  2. CSR Policy: Status={csr.get('status')} | Source={csr.get('source')} | URL={csr.get('url')}")

        # 3. NSE Annual Report Search
        nse = await search_nse_annual_reports(company_name=company, financial_year="2023-24")
        doc0 = nse["documents"][0] if nse.get("documents") else {}
        print(f"  3. NSE Annual Report (2023-24): Status={doc0.get('status')} | URL={doc0.get('url') or doc0.get('not_found_reason')}")

        # 4. BSE Disclosure Search
        bse = await search_bse_disclosures(company_name=company, keyword="CSR")
        bse_doc0 = bse["documents"][0] if bse.get("documents") else {}
        print(f"  4. BSE CSR Disclosure: Status={bse_doc0.get('status')} | URL={bse_doc0.get('url') or bse_doc0.get('not_found_reason')}")

        # 5. BRSR Search
        brsr = await search_brsr(company_name=company)
        print(f"  5. BRSR Report: Status={brsr.get('status')} | Source={brsr.get('source')} | URL={brsr.get('url') or brsr.get('not_found_reason')}")

    print("\n" + "=" * 70)
    print("Retrieval demonstration completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demonstration())
