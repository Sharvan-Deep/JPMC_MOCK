"""
Sample Document Retrieval & Versioned Storage Demonstration Runner (Task 2).
Demonstrates fetching MCP document metadata, validating PDF signatures, calculating SHA-256,
saving to data/documents/, detecting duplicates, and persisting versioned metadata.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_server.retrieval.retriever_service import DocumentRetrieverService
from mcp_server.services.brsr_search import search_brsr
from mcp_server.services.company_search import search_company
from mcp_server.services.csr_policy_search import search_csr_policy
from mcp_server.services.nse_search import search_nse_annual_reports

SAMPLE_COMPANIES = [
    "INDIAN OIL CORPORATION LIMITED",
    "CENTRAL COALFIELDS LIMITED",
    "GAIL (INDIA) LIMITED",
    "TATA STEEL LIMITED",
    "POWER GRID CORPORATION OF INDIA LIMITED",
]

# Minimal valid PDF fixture for demonstration testing
DEMO_PDF_PAYLOAD = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000118 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
)


async def run_retrieval_demonstration():
    print("=" * 75)
    print("TASK 2: JALDHAARA DOCUMENT RETRIEVAL & VERSIONED STORAGE DEMO")
    print("=" * 75)

    base_storage_dir = Path("data") / "documents"
    retriever = DocumentRetrieverService(base_dir=base_storage_dir)

    for company in SAMPLE_COMPANIES:
        print(f"\n=======================================================")
        print(f"Company: {company}")
        print(f"=======================================================")

        # 1. Company Identity via MCP
        comp_info = await search_company(company_name=company)
        print(f"  [MCP] Listed: {comp_info.get('is_listed')} | Symbol: {comp_info.get('symbol')}")

        # 2. CSR Policy Discovery via MCP
        csr_contract = await search_csr_policy(company_name=company)
        print(f"  [MCP] CSR Policy status: {csr_contract.get('status')} | URL: {csr_contract.get('url')}")

        # Retrieve and store CSR Policy
        # Use demo valid PDF payload to guarantee reliable offline demonstration
        csr_result = retriever.process_document_retrieval(
            csr_contract,
            custom_content=DEMO_PDF_PAYLOAD if csr_contract.get("status") == "FOUND" else None,
        )
        print(f"  [Storage] Action: {csr_result.get('action')} | Version: {csr_result.get('version', 'N/A')}")
        if csr_result.get("local_file_path"):
            print(f"            File: {csr_result.get('local_file_path')}")
            print(f"            SHA-256: {csr_result.get('sha256')[:16]}...")

        # 3. NSE Annual Report Discovery via MCP
        nse_reports = await search_nse_annual_reports(company_name=company, financial_year="2023-24")
        for doc in nse_reports.get("documents", []):
            print(f"  [MCP] NSE Report status: {doc.get('status')} | Title: {doc.get('title') or doc.get('not_found_reason')}")
            nse_result = retriever.process_document_retrieval(
                doc,
                custom_content=DEMO_PDF_PAYLOAD if doc.get("status") == "FOUND" else None,
            )
            print(f"  [Storage] Action: {nse_result.get('action')} | Version: {nse_result.get('version', 'N/A')}")
            if nse_result.get("local_file_path"):
                print(f"            File: {nse_result.get('local_file_path')}")

        # 4. BRSR Discovery via MCP
        brsr_contract = await search_brsr(company_name=company)
        print(f"  [MCP] BRSR status: {brsr_contract.get('status')} | Title: {brsr_contract.get('title') or brsr_contract.get('not_found_reason')}")
        brsr_result = retriever.process_document_retrieval(
            brsr_contract,
            custom_content=DEMO_PDF_PAYLOAD if brsr_contract.get("status") == "FOUND" else None,
        )
        print(f"  [Storage] Action: {brsr_result.get('action')} | Version: {brsr_result.get('version', 'N/A')}")

    # Demonstrate Deduplication Rule (Run duplicate pass on first company)
    print("\n" + "=" * 75)
    print("DEDUPLICATION VERIFICATION PASS:")
    print("=" * 75)
    test_company = "INDIAN OIL CORPORATION LIMITED"
    dup_contract = await search_csr_policy(company_name=test_company)
    dup_result = retriever.process_document_retrieval(dup_contract, custom_content=DEMO_PDF_PAYLOAD)
    print(f"  Company: {test_company}")
    print(f"  Duplicate Run Action: {dup_result.get('action')} (Expected: DUPLICATE_SKIPPED)")
    print(f"  Version Maintained: {dup_result.get('version')}")
    print(f"  SHA-256 Match: {dup_result.get('sha256')[:16]}...")

    # Summary of metadata records
    meta_path = base_storage_dir / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            all_records = json.load(f)
        print("\n" + "=" * 75)
        print(f"Total Persistent Metadata Records Stored: {len(all_records)}")
        print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_retrieval_demonstration())
