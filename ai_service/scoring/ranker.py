"""
Deterministic Multi-Criteria Ranker for Task 11: CSR Donor Lead Scoring.

Sorts scored candidates by:
1. total_score (descending)
2. wash_relevance (descending)
3. freshness (descending)
4. historical_track_record (descending)
5. company name (ascending, alphabetical final tie-breaker)
"""

from typing import List
from ai_service.schemas.scoring import LeadScore


class LeadRanker:
    """Provides deterministic ranking and tie-breaking for donor leads."""

    @staticmethod
    def rank_leads(leads: List[LeadScore]) -> List[LeadScore]:
        """
        Sorts leads deterministically using multi-criteria priority.
        """
        return sorted(
            leads,
            key=lambda item: (
                -item.total_score,
                -item.components.wash_relevance.points_awarded,
                -item.components.freshness.points_awarded,
                -item.components.historical_track_record.points_awarded,
                item.company.upper().strip(),
            ),
        )
