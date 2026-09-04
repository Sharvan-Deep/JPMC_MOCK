"""
Text Preprocessing and Cleaning Module for Task 5.
Cleans raw extracted PDF text:
- Normalizes excessive whitespace and irregular line breaks
- Removes obvious extraction artifacts (e.g. repeated page numbering or stamps)
- Preserves meaningful punctuation, currency symbols, and CSR domain terminology
- Preserves page boundaries and page-to-text mapping
"""

import re
from typing import Dict, List, Tuple


class TextCleaner:
    """Cleans raw text extracted from PDF pages while maintaining traceability."""

    # Common extraction artifact patterns
    PAGE_NUMBER_PATTERNS = [
        re.compile(r"^\s*page\s+\d+\s*(?:of\s*\d+)?\s*$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^\s*[-—]\s*\d+\s*[-—]\s*$", re.MULTILINE),
        re.compile(r"^\s*[-—]\s*Page\s+\d+\s*[-—]\s*$", re.IGNORECASE | re.MULTILINE),
    ]

    # Artifact markers inserted by extraction or header stamps
    EXTRACTION_STAMP_PATTERN = re.compile(r"^\s*---\s*Page\s+\d+\s*---\s*$", re.MULTILINE)

    def clean_page_text(self, raw_text: str) -> str:
        """
        Cleans raw text for a single page.
        Normalizes spaces and line breaks while preserving paragraph boundaries.
        """
        if not raw_text:
            return ""

        text = raw_text

        # 1. Remove obvious extraction stamps and isolated page-number lines
        text = self.EXTRACTION_STAMP_PATTERN.sub("", text)
        for pat in self.PAGE_NUMBER_PATTERNS:
            text = pat.sub("", text)

        # 2. Normalize non-standard space characters (non-breaking spaces, zero-width spaces)
        text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

        # 3. Clean trailing whitespace on each line
        lines = [line.strip() for line in text.splitlines()]

        # 4. Collapse consecutive empty lines (allow at most 1 blank line between paragraphs)
        cleaned_lines: List[str] = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank and cleaned_lines:
                    cleaned_lines.append("")
                    prev_blank = True
            else:
                # Collapse intra-line multiple spaces
                line_normalized = " ".join(line.split())
                cleaned_lines.append(line_normalized)
                prev_blank = False

        return "\n".join(cleaned_lines).strip()

    def clean_text_by_page(self, raw_text_by_page: Dict[int, str]) -> Tuple[Dict[int, str], List[str]]:
        """
        Cleans text dictionary page-by-page.
        Detects repeated headers/footers appearing across 3 or more pages.
        """
        warnings: List[str] = []
        cleaned_dict: Dict[int, str] = {}

        if not raw_text_by_page:
            return cleaned_dict, warnings

        # Step 1: Clean each page individually
        for page_num, raw_text in raw_text_by_page.items():
            cleaned_dict[int(page_num)] = self.clean_page_text(raw_text)

        # Step 2: Detect boilerplate headers/footers repeated identically across pages
        if len(cleaned_dict) >= 3:
            first_lines: Dict[str, int] = {}
            last_lines: Dict[str, int] = {}

            for text in cleaned_dict.values():
                page_lines = [l for l in text.splitlines() if l.strip()]
                if page_lines:
                    fl = page_lines[0].lower()
                    ll = page_lines[-1].lower()
                    # Only consider short lines as candidate headers/footers (< 80 chars)
                    if len(fl) < 80 and not any(kw in fl for kw in ["project", "expenditure", "csr", "table"]):
                        first_lines[fl] = first_lines.get(fl, 0) + 1
                    if len(ll) < 80:
                        last_lines[ll] = last_lines.get(ll, 0) + 1

            # Identify headers occurring on > 75% of pages
            threshold = int(len(cleaned_dict) * 0.75)
            boilerplate_headers = {l for l, c in first_lines.items() if c >= max(3, threshold)}
            boilerplate_footers = {l for l, c in last_lines.items() if c >= max(3, threshold)}

            if boilerplate_headers or boilerplate_footers:
                for page_num, text in cleaned_dict.items():
                    p_lines = text.splitlines()
                    if not p_lines:
                        continue
                    if p_lines and p_lines[0].lower().strip() in boilerplate_headers:
                        p_lines = p_lines[1:]
                    if p_lines and p_lines[-1].lower().strip() in boilerplate_footers:
                        p_lines = p_lines[:-1]
                    cleaned_dict[page_num] = "\n".join(p_lines).strip()
                warnings.append(
                    f"Removed boilerplate headers/footers occurring across multiple pages: "
                    f"{list(boilerplate_headers | boilerplate_footers)}"
                )

        return cleaned_dict, warnings
