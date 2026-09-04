"""
Append-Only Freshness History Repository for Task 10: CSR Freshness System.

Ensures historical assessments are never overwritten. Both previous and current
freshness records remain permanently queryable and auditable.
"""

import json
import os
import uuid
from typing import Dict, List, Optional
from ai_service.schemas.freshness import FreshnessAssessment, FreshnessStatus


class FreshnessRepository:
    """
    In-memory and file-persisted append-only repository for company freshness records.
    Guarantee: Historical records are NEVER overwritten.
    """

    def __init__(self, storage_path: Optional[str] = "data/freshness_history.json"):
        self.storage_path = storage_path
        # In-memory store: company -> list of FreshnessAssessment in chronological order
        self._history: Dict[str, List[FreshnessAssessment]] = {}
        self._load_from_storage()

    def _normalize_name(self, company: str) -> str:
        return company.strip().lower()

    def _load_from_storage(self) -> None:
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            for comp_key, records in raw_data.items():
                self._history[comp_key] = [FreshnessAssessment.model_validate(r) for r in records]
        except Exception:
            # If storage corrupted or empty, start fresh
            self._history = {}

    def _persist_to_storage(self) -> None:
        if not self.storage_path:
            return
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            serialized = {
                comp: [rec.model_dump() for rec in recs]
                for comp, recs in self._history.items()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
        except Exception:
            pass

    def save(self, assessment: FreshnessAssessment) -> FreshnessAssessment:
        """
        Appends a new freshness assessment without overwriting existing history.
        Automatically links previous_status if available.
        """
        comp_key = self._normalize_name(assessment.company)
        history_list = self._history.setdefault(comp_key, [])

        if not assessment.assessment_id:
            assessment.assessment_id = str(uuid.uuid4())

        # Link previous_status from most recent prior record if not set
        if assessment.previous_status is None and history_list:
            assessment.previous_status = history_list[-1].status

        # Append to chronological list (NEVER replace)
        history_list.append(assessment)
        self._persist_to_storage()
        return assessment

    def get_current_status(self, company: str) -> Optional[FreshnessAssessment]:
        """Returns the most recent freshness assessment for the specified company."""
        comp_key = self._normalize_name(company)
        history_list = self._history.get(comp_key, [])
        return history_list[-1] if history_list else None

    def get_history(self, company: str) -> List[FreshnessAssessment]:
        """Returns the complete chronological history of assessments for the company."""
        comp_key = self._normalize_name(company)
        return list(self._history.get(comp_key, []))

    def get_last_verified(self, company: str) -> Optional[FreshnessAssessment]:
        """Returns the most recent assessment where verification was successfully conducted."""
        history = self.get_history(company)
        for record in reversed(history):
            if record.verified_at:
                return record
        return None

    def clear(self) -> None:
        """Clears stored history (useful for test isolation)."""
        self._history.clear()
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                os.remove(self.storage_path)
            except Exception:
                pass
