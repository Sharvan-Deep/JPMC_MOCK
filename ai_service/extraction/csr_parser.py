"""
CSR Document Information Parser for Task 4.
Extracts structured CSR information (donor name, financial year, amounts,
project tables, beneficiaries, locations) from raw text and tables.
CRITICAL: Preserves verbatim raw values without normalization or cleaning.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ai_service.extraction.pdf_extractor import ExtractedPageData, ExtractedTableData, RawPDFExtraction
from ai_service.logging_config import logger
from ai_service.schemas.extraction import (
    CSRProjectRaw,
    CSRTableRaw,
    IdentifiedCSRData,
)


class CSRParser:
    """Parses raw PDF extraction output into structured CSR entities."""

    # Keywords for detecting CSR project tables
    PROJECT_COL_KEYWORDS = ["project", "program", "activity", "name of project", "name of the project"]
    SECTOR_COL_KEYWORDS = ["schedule vii", "sector", "category", "activity", "thrust area"]
    LOCATION_COL_KEYWORDS = ["location", "state", "district", "local area", "place"]
    SPENT_COL_KEYWORDS = ["amount spent", "expenditure", "actual spent", "spent in fy", "total spent"]
    OUTLAY_COL_KEYWORDS = ["outlay", "allocated", "budget", "amount outlay"]
    MODE_COL_KEYWORDS = ["mode of implementation", "implementing agency", "direct", "agency"]
    BENEFICIARY_COL_KEYWORDS = ["beneficiar", "reach", "impact", "people covered"]

    # Patterns for extracting total CSR amount from text
    CSR_AMOUNT_PATTERNS = [
        re.compile(
            r"(?:total\s+(?:csr\s+)?expenditure|total\s+amount\s+spent|amount\s+spent|total\s+csr\s+spent|"
            r"csr\s+obligation|actual\s+csr\s+spent|prescribed\s+csr\s+expenditure)"
            r"(?:\s+(?:for|during|in)\s+(?:the\s+)?(?:financial\s+year|fy|year|period))?"
            r"[\s\:\-]+(?:is|of)?[\s\:\-]*(?:₹|rs\.?|inr)?\s*([0-9.,]+\s*(?:crores?|lakhs?|cr|lacs|million|billion)?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:spent\s+a\s+sum\s+of|spent\s+an\s+amount\s+of|expenditure\s+of)\s*(?:₹|rs\.?|inr)?\s*"
            r"([0-9.,]+\s*(?:crores?|lakhs?|cr|lacs|million)?)",
            re.IGNORECASE,
        ),
    ]

    # Patterns for financial year
    FY_PATTERNS = [
        re.compile(r"\b(?:FY|Financial\s+Year)\s*[\:\-]?\s*(20\d\d[\-–]\d\d(?:\d\d)?)\b", re.IGNORECASE),
        re.compile(r"\b(20\d\d[\-–]\d\d)\b"),
        re.compile(r"\bended\s+(?:31st\s+)?March\s*\,?\s*(20\d\d)\b", re.IGNORECASE),
    ]

    # Patterns for Company / Donor name in headings
    COMPANY_PATTERNS = [
        re.compile(
            r"(?:annual\s+report\s+on\s+csr\s+activities\s+of|csr\s+report\s+of|csr\s+policy\s+of)\s+([A-Za-z0-9\s\,\.\(\)\&\-]+?)(?:\s+for|\s+limited|\s+ltd|\n|$)",
            re.IGNORECASE,
        ),
    ]

    def parse(
        self,
        raw_extraction: RawPDFExtraction,
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[IdentifiedCSRData, Dict[str, Any]]:
        """
        Parses raw text and extracted tables into structured IdentifiedCSRData.
        Preserves raw table data and raw text verbatim in raw_extracted_data.

        Args:
            raw_extraction: Low-level output from PDFExtractor.
            document_metadata: Optional metadata from Task 2 (e.g., known company name).

        Returns:
            Tuple of (IdentifiedCSRData, raw_extracted_data_dict)
        """
        doc_meta = document_metadata or {}
        donor_name = doc_meta.get("company_name")
        financial_year = doc_meta.get("financial_year")
        total_csr_amount = None
        csr_committee_members: List[str] = []
        identified_projects: List[CSRProjectRaw] = []
        other_fields: Dict[str, Any] = {}

        raw_text_by_page: Dict[int, str] = {}
        raw_tables_list: List[CSRTableRaw] = []

        all_text = ""

        # Step 1: Accumulate raw text and raw tables
        for page in raw_extraction.pages:
            raw_text_by_page[page.page_number] = page.raw_text
            all_text += f"\n--- Page {page.page_number} ---\n" + page.raw_text

            for tbl in page.tables:
                raw_table_schema = CSRTableRaw(
                    page_number=tbl.page_number,
                    table_index=tbl.table_index,
                    headers=tbl.headers,
                    rows=tbl.rows,
                )
                raw_tables_list.append(raw_table_schema)

                # Inspect if this table contains CSR projects
                projects_from_table = self._parse_csr_table(tbl)
                if projects_from_table:
                    identified_projects.extend(projects_from_table)

        # Step 2: Extract or refine donor name if missing
        if not donor_name:
            for pat in self.COMPANY_PATTERNS:
                match = pat.search(all_text)
                if match:
                    donor_name = match.group(1).strip()
                    break

        # Step 3: Extract or refine financial year if missing
        if not financial_year or financial_year.lower() == "general":
            for pat in self.FY_PATTERNS:
                match = pat.search(all_text)
                if match:
                    financial_year = match.group(1).strip()
                    break

        # Step 4: Extract total CSR amount from text if present
        for pat in self.CSR_AMOUNT_PATTERNS:
            match = pat.search(all_text)
            if match:
                total_csr_amount = match.group(1).strip()
                break

        # Step 5: Extract committee members if mentioned
        committee_match = re.search(
            r"composition\s+of\s+(?:the\s+)?csr\s+committee[:\s]+([\s\S]{10,400}?)(?:\n\n|\.\s|\d\.\s)",
            all_text,
            re.IGNORECASE,
        )
        if committee_match:
            lines = [
                line.strip(" -•\t")
                for line in committee_match.group(1).splitlines()
                if len(line.strip(" -•\t")) > 3
            ]
            if lines:
                csr_committee_members = lines[:10]

        # Step 6: Text-based project detection if no projects found in tables
        if not identified_projects:
            identified_projects = self._extract_projects_from_text(raw_extraction.pages)

        identified_data = IdentifiedCSRData(
            donor_name=donor_name,
            financial_year=financial_year,
            total_csr_amount=total_csr_amount,
            csr_committee_members=csr_committee_members if csr_committee_members else None,
            projects=identified_projects,
            other_fields=other_fields,
        )

        raw_extracted_data = {
            "text_by_page": raw_text_by_page,
            "tables": [t.model_dump() for t in raw_tables_list],
        }

        return identified_data, raw_extracted_data

    def _parse_csr_table(self, tbl: ExtractedTableData) -> List[CSRProjectRaw]:
        """Inspects and parses a table if headers resemble CSR project schedules."""
        if not tbl.headers or not tbl.rows:
            return []

        # Find column indices for standard fields
        proj_col = self._find_col(tbl.headers, self.PROJECT_COL_KEYWORDS)
        sec_col = self._find_col(tbl.headers, self.SECTOR_COL_KEYWORDS)
        loc_col = self._find_col(tbl.headers, self.LOCATION_COL_KEYWORDS)
        spent_col = self._find_col(tbl.headers, self.SPENT_COL_KEYWORDS)
        outlay_col = self._find_col(tbl.headers, self.OUTLAY_COL_KEYWORDS)
        mode_col = self._find_col(tbl.headers, self.MODE_COL_KEYWORDS)
        ben_col = self._find_col(tbl.headers, self.BENEFICIARY_COL_KEYWORDS)

        # Must have at least project/activity and an amount or location column
        if proj_col is None and sec_col is None:
            return []
        if spent_col is None and outlay_col is None and loc_col is None:
            return []

        projects: List[CSRProjectRaw] = []

        for row in tbl.rows:
            if not row or len(row) <= max(c for c in [proj_col, sec_col, spent_col] if c is not None):
                continue

            proj_val = self._get_val(row, proj_col)
            sec_val = self._get_val(row, sec_col)
            loc_val = self._get_val(row, loc_col)
            spent_val = self._get_val(row, spent_col)
            outlay_val = self._get_val(row, outlay_col)
            mode_val = self._get_val(row, mode_col)
            ben_val = self._get_val(row, ben_col)

            # Skip summary/total rows or headers repeated in body
            if proj_val and any(kw in proj_val.lower() for kw in ["total", "sub total", "sub-total", "grand total"]):
                continue

            if not proj_val and not sec_val and not spent_val:
                continue

            # Build raw row key-value dictionary
            raw_row_data = {
                (tbl.headers[idx] if idx < len(tbl.headers) else f"col_{idx}"): cell
                for idx, cell in enumerate(row)
            }

            projects.append(
                CSRProjectRaw(
                    project_name=proj_val,
                    category=sec_val,
                    location=loc_val,
                    amount_spent=spent_val,
                    amount_allocated=outlay_val,
                    beneficiaries=ben_val,
                    implementation_mode=mode_val,
                    page_number=tbl.page_number,
                    raw_row_data=raw_row_data,
                )
            )

        return projects

    def _extract_projects_from_text(self, pages: List[ExtractedPageData]) -> List[CSRProjectRaw]:
        """Fallback method to identify project mentions from unstructured page text."""
        projects: List[CSRProjectRaw] = []
        project_regex = re.compile(
            r"(?:Project|Program|Initiative)[\s\:\-]+([^\n\.\;]{4,100})"
            r"(?:[^\n]*?(?:amount|spent|cost|expenditure)[\s\:\-]+(?:₹|rs\.?)?\s*([0-9.,]+\s*(?:crores?|lakhs?|cr|lacs)?))?",
            re.IGNORECASE,
        )

        for page in pages:
            if not page.raw_text:
                continue
            for match in project_regex.finditer(page.raw_text):
                p_name = match.group(1).strip()
                p_amount = match.group(2).strip() if match.group(2) else None
                projects.append(
                    CSRProjectRaw(
                        project_name=p_name,
                        amount_spent=p_amount,
                        page_number=page.page_number,
                    )
                )

        return projects

    def _find_col(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        for idx, h in enumerate(headers):
            h_clean = " ".join(str(h).lower().split())
            if any(kw in h_clean for kw in keywords):
                return idx
        return None

    def _get_val(self, row: List[Optional[str]], idx: Optional[int]) -> Optional[str]:
        if idx is not None and 0 <= idx < len(row):
            val = row[idx]
            if val is not None and str(val).strip() != "":
                return str(val).strip()
        return None
