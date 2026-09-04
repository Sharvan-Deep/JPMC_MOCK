"""
Append-Only Recommendation History Repository for Task 12: Next-Best-Action Recommendation Copilot.

Ensures historical recommendations are never overwritten. Both previous and current
recommendations remain permanently queryable and auditable.
"""

import json
import os
import uuid
from typing import Dict, List, Optional
from ai_service.schemas.copilot import RecommendationHistoryResponse, RecommendationResult


class RecommendationRepository:
    """
    In-memory and file-persisted append-only repository for company recommendations.
    Guarantee: Historical records are NEVER overwritten.
    """

    def __init__(self, storage_path: Optional[str] = "data/recommendations_history.json"):
        self.storage_path = storage_path
        # In-memory store: normalized company name -> list of RecommendationResult in chronological order
        self._history: Dict[str, List[RecommendationResult]] = {}
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
                self._history[comp_key] = [RecommendationResult.model_validate(r) for r in records]
        except Exception:
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

    def save(self, result: RecommendationResult) -> RecommendationResult:
        """
        Appends a new recommendation result without overwriting existing history.
        Assigns unique recommendation_id if not present.
        """
        if not result.recommendation_id:
            result.recommendation_id = f"rec_{uuid.uuid4().hex[:12]}"

        key = self._normalize_name(result.company)
        if key not in self._history:
            self._history[key] = []

        self._history[key].append(result)
        self._persist_to_storage()
        return result

    def get_latest(self, company: str) -> Optional[RecommendationResult]:
        """Returns the most recent recommendation for the company, or None."""
        key = self._normalize_name(company)
        records = self._history.get(key, [])
        return records[-1] if records else None

    def get_history(self, company: str) -> RecommendationHistoryResponse:
        """Returns the full chronological history response for the company."""
        key = self._normalize_name(company)
        records = self._history.get(key, [])
        latest = records[-1] if records else None
        return RecommendationHistoryResponse(
            company=company,
            current_recommendation=latest,
            history=list(records),
        )

    def list_all_companies(self) -> List[str]:
        """Returns all distinct company names recorded in the history."""
        return [recs[-1].company for recs in self._history.values() if recs]
