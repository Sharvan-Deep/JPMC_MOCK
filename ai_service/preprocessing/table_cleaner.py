"""
Table Preprocessing and Deduplication Module for Task 5.
Cleans extracted table matrices:
- Drops completely empty rows and columns
- Normalizes cell whitespace while preserving verbatim text
- Identifies and removes extraction-duplicate rows caused by page breaks
- Retains original page numbers and table indices
"""

from typing import Any, Dict, List, Optional, Tuple
from ai_service.schemas.extraction import CSRProjectRaw, CSRTableRaw
from ai_service.schemas.preprocessing import CleanedCSRRecord


class TableCleaner:
    """Cleans table matrices and filters extraction duplicate rows."""

    def clean_table(self, table_raw: CSRTableRaw) -> CSRTableRaw:
        """
        Cleans a single table matrix:
        - Prunes completely empty rows
        - Prunes completely empty columns
        - Normalizes cell whitespace
        """
        headers = [str(h).strip() if h is not None else "" for h in table_raw.headers]
        rows = table_raw.rows or []

        # 1. Normalize cell whitespace and filter empty rows
        cleaned_rows: List[List[Optional[str]]] = []
        for row in rows:
            cleaned_row = [
                (" ".join(str(c).split()) if (c is not None and str(c).strip()) else None)
                for c in row
            ]
            # Keep row only if at least one cell has content
            if any(c is not None for c in cleaned_row):
                cleaned_rows.append(cleaned_row)

        if not cleaned_rows:
            return CSRTableRaw(
                page_number=table_raw.page_number,
                table_index=table_raw.table_index,
                headers=headers,
                rows=[],
            )

        # 2. Check for completely empty columns across all rows and headers
        num_cols = max(len(headers), max(len(r) for r in cleaned_rows))
        non_empty_col_indices: List[int] = []

        for col_idx in range(num_cols):
            h_val = headers[col_idx] if col_idx < len(headers) else None
            has_col_content = bool(h_val and h_val.strip())

            if not has_col_content:
                for row in cleaned_rows:
                    if col_idx < len(row) and row[col_idx] is not None:
                        has_col_content = True
                        break

            if has_col_content:
                non_empty_col_indices.append(col_idx)

        # If some columns are completely empty, drop them safely
        if len(non_empty_col_indices) < num_cols and non_empty_col_indices:
            new_headers = [
                (headers[i] if i < len(headers) else f"col_{i}")
                for i in non_empty_col_indices
            ]
            new_rows: List[List[Optional[str]]] = []
            for r in cleaned_rows:
                new_row = [(r[i] if i < len(r) else None) for i in non_empty_col_indices]
                new_rows.append(new_row)
            headers = new_headers
            cleaned_rows = new_rows

        return CSRTableRaw(
            page_number=table_raw.page_number,
            table_index=table_raw.table_index,
            headers=headers,
            rows=cleaned_rows,
        )

    def filter_extraction_duplicates(
        self, records: List[CleanedCSRRecord]
    ) -> Tuple[List[CleanedCSRRecord], int]:
        """
        Detects and removes obvious duplicate records created by PDF extraction
        (e.g., when a table spanning multiple pages repeats the exact same row).
        Conservative: Only deduplicates when project_name, category, and amount match exactly.
        Returns: (deduplicated_records, count_removed)
        """
        seen_signatures = set()
        deduped: List[CleanedCSRRecord] = []
        duplicates_removed = 0

        for rec in records:
            p_name = (rec.project_name or "").lower().strip()
            p_cat = (rec.category or "").lower().strip()
            p_amt = str(rec.raw_amount_spent or "").lower().strip()

            # If project name or amount is substantial, check exact duplicate signature
            if p_name and (p_amt or p_cat):
                sig = f"{p_name}|{p_cat}|{p_amt}"
                if sig in seen_signatures:
                    rec.is_extraction_duplicate = True
                    duplicates_removed += 1
                    continue
                seen_signatures.add(sig)

            deduped.append(rec)

        return deduped, duplicates_removed
