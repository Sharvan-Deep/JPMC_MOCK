"""
MCA Historical Candidate Data Loader for Task 11: CSR Donor Lead Scoring.

Loads and indexes historical MCA WASH records from `04_top_500_mca_candidates.csv`.
Provides historical track records (active years, WASH spend, states) to prevent
double-counting and support historical scoring.
"""

import csv
import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional
from ai_service.config import get_settings

logger = logging.getLogger(__name__)


def normalize_company_name(name: str) -> str:
    """Canonicalizes company name for robust lookup."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", name.upper())
    tokens = [t for t in clean.split() if t not in ("LTD", "LIMITED", "CORP", "CORPORATION", "PVT", "PRIVATE", "LLP", "INC")]
    return " ".join(tokens).strip()


class MCACandidateRegistry:
    """In-memory index of Top 500 MCA candidate companies and historical track records."""

    def __init__(self, csv_path: Optional[str] = None):
        settings = get_settings()
        self.csv_path = csv_path or settings.MCA_CANDIDATES_CSV_PATH
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._raw_records: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.csv_path):
            logger.warning("MCA candidates CSV not found at '%s'. Historical lookups will be empty.", self.csv_path)
            return

        try:
            with open(self.csv_path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_name = row.get("company_name", "").strip()
                    if not raw_name:
                        continue

                    # Parse numbers safely
                    def _parse_float(val: Optional[str]) -> float:
                        try:
                            return float(val) if val else 0.0
                        except ValueError:
                            return 0.0

                    def _parse_int(val: Optional[str]) -> int:
                        try:
                            return int(float(val)) if val else 0
                        except ValueError:
                            return 0

                    record = {
                        "company_name": raw_name,
                        "mca_rank": _parse_int(row.get("mca_preliminary_rank")),
                        "total_wash_spend_crore": _parse_float(row.get("total_wash_spend_crore")),
                        "total_water_spend_crore": _parse_float(row.get("total_water_spend_crore")),
                        "total_sanitation_spend_crore": _parse_float(row.get("total_sanitation_spend_crore")),
                        "water_active_years": _parse_float(row.get("water_active_years")),
                        "sanitation_active_years": _parse_float(row.get("sanitation_active_years")),
                        "active_years": _parse_float(row.get("active_years")),
                        "wash_record_count": _parse_int(row.get("wash_record_count")),
                        "financial_years": [y.strip() for y in row.get("financial_years", "").split(",") if y.strip()],
                        "states": [s.strip() for s in row.get("states", "").split(",") if s.strip()],
                        "csr_sectors": [sec.strip() for sec in row.get("csr_sectors", "").split(",") if sec.strip()],
                    }

                    self._raw_records.append(record)
                    norm_key = normalize_company_name(raw_name)
                    self._registry[norm_key] = record
                    # Also register verbatim key
                    self._registry[raw_name.upper()] = record

            logger.info("Loaded %d MCA candidate records into index.", len(self._raw_records))
        except Exception as e:
            logger.warning("Error reading MCA candidates CSV '%s': %s", self.csv_path, e)

    def lookup(self, company: str) -> Optional[Dict[str, Any]]:
        """Finds historical MCA record for a given company name."""
        if not company:
            return None
        # Try verbatim exact upper
        upper_name = company.strip().upper()
        if upper_name in self._registry:
            return self._registry[upper_name]

        # Try normalized
        norm_name = normalize_company_name(company)
        if norm_name in self._registry:
            return self._registry[norm_name]

        # Fuzzy partial match
        for key, rec in self._registry.items():
            if norm_name and (norm_name in key or key in norm_name):
                return rec
        return None

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all loaded raw MCA candidate records."""
        return list(self._raw_records)


@lru_cache
def get_mca_registry() -> MCACandidateRegistry:
    """Cached singleton provider for MCA candidates registry."""
    return MCACandidateRegistry()
