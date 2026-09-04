"""
Field Normalization Module for Task 5.
Deterministically normalizes structured CSR fields:
- Company names into canonical title representations
- Financial years into standardized YYYY-YY strings
- Monetary figures into INR Crores (₹ Cr)
CRITICAL: Strictly preserves the original raw string alongside normalized values.
"""

import re
from typing import Optional, Tuple


class FieldNormalizer:
    """Provides deterministic, safe normalizations for structured CSR entities."""

    # Corporate suffix removal pattern
    CORP_SUFFIX_PATTERN = re.compile(
        r"[\,\.\s]+(?:limited|ltd\.?|private\s+limited|pvt\.?\s+ltd\.?|corp(?:oration)?\.?|inc\.?|llp|plc)[\s\.]*$",
        re.IGNORECASE,
    )

    # Financial year patterns (supports FY 2023-24, FY24-25, 2023-2024, etc.)
    FY_PATTERN_1 = re.compile(r"(?:FY)?\s*(?:20)?(\d\d)\s*[\-–]\s*(?:20)?(\d\d)\b", re.IGNORECASE)
    FY_PATTERN_2 = re.compile(r"\bended\s+(?:31st\s+)?March\s*\,?\s*(20\d\d)\b", re.IGNORECASE)

    # Amount extraction regex: matches number and unit
    # 1 Crore = 100 Lakhs = 10,000,000 INR
    AMOUNT_PATTERN = re.compile(
        r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:[\,\.][0-9]+)*)\s*(crores?|cr|lakhs?|lacs?|lac|million|billion|thousand|k)?",
        re.IGNORECASE,
    )

    def normalize_company_name(self, raw_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalizes company name into a clean, canonical representation.
        Returns: (canonical_name, raw_name)
        """
        if not raw_name:
            return None, raw_name

        cleaned = " ".join(raw_name.strip().split())
        if not cleaned:
            return None, raw_name

        # Strip standard corporate suffixes
        canonical = self.CORP_SUFFIX_PATTERN.sub("", cleaned).strip(" ,.-")

        # Convert ALL-CAPS or all-lower names to Title Case, while keeping short acronyms
        words = canonical.split()
        title_words = []
        for w in words:
            pure_alpha = "".join(c for c in w if c.isalpha())
            if len(pure_alpha) <= 3 and pure_alpha.isupper() and "(" not in w and ")" not in w:
                title_words.append(w)
            else:
                title_words.append(re.sub(r"[a-zA-Z]+", lambda m: m.group(0).capitalize(), w))
        canonical = " ".join(title_words)

        return canonical, raw_name

    def normalize_financial_year(self, raw_fy: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalizes financial year representation into standard 'YYYY-YY'.
        Returns: (normalized_fy, raw_fy)
        """
        if not raw_fy:
            return None, raw_fy

        cleaned = raw_fy.strip()
        if cleaned.lower() == "general":
            return "general", raw_fy

        # Match FY 2023-24, FY24-25, 2023-2024, FY 2023–24
        m1 = self.FY_PATTERN_1.search(cleaned)
        if m1:
            start_yr = m1.group(1)
            end_yr = m1.group(2)
            if len(start_yr) == 2:
                start_yr = f"20{start_yr}"
            if len(end_yr) == 4:
                end_yr = end_yr[-2:]
            return f"{start_yr}-{end_yr}", raw_fy

        # Match "ended 31st March 2024" -> 2023-24
        m2 = self.FY_PATTERN_2.search(cleaned)
        if m2:
            end_yr_int = int(m2.group(1))
            start_yr_int = end_yr_int - 1
            return f"{start_yr_int}-{str(end_yr_int)[-2:]}", raw_fy

        return cleaned, raw_fy

    def normalize_amount_to_crores(self, raw_amount: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
        """
        Converts unambiguous currency strings into numeric INR Crores (₹ Cr).
        1 Crore = 100 Lakhs = 10,000,000 INR.

        Examples:
        - '₹ 12.50 Cr' -> 12.50
        - '1250 Lakhs' -> 12.50
        - 'Rs. 50,00,000' -> 0.50
        - '5000000' -> 0.50
        - '50,000' -> 0.005

        Returns: (normalized_amount_crore, raw_amount)
        """
        if not raw_amount or not str(raw_amount).strip():
            return None, raw_amount

        text = str(raw_amount).strip()

        # Check for non-monetary text like 'Nil', 'N/A', '-'
        if text.lower() in ["nil", "n/a", "na", "-", "none", "zero"]:
            return 0.0, raw_amount

        match = self.AMOUNT_PATTERN.search(text)
        if not match:
            return None, raw_amount

        num_str = match.group(1).replace(",", "")
        unit = (match.group(2) or "").lower()

        try:
            val = float(num_str)
        except ValueError:
            return None, raw_amount

        # Convert based on unit
        if unit in ["crores", "crore", "cr"]:
            norm_val = val
        elif unit in ["lakhs", "lacs", "lakh", "lac"]:
            # 100 Lakhs = 1 Crore
            norm_val = val / 100.0
        elif unit in ["million"]:
            # 10 Million = 1 Crore (10,000,000 INR)
            norm_val = val / 10.0
        elif unit in ["billion"]:
            # 1 Billion = 100 Crore
            norm_val = val * 100.0
        elif unit in ["thousand", "k"]:
            norm_val = (val * 1000.0) / 10000000.0
        else:
            # No explicit unit:
            # If value is large (>= 10,000), assume raw INR
            if val >= 10000:
                norm_val = val / 10000000.0
            else:
                # If value is small and context mentions Crore in the column header or document,
                # but no unit is in the cell, we don't guess blindly unless explicit.
                # Safe conservative return: treat as already in Crores if <= 1000 and has decimal,
                # otherwise return None to prevent silent distortion.
                return None, raw_amount

        return round(norm_val, 4), raw_amount
