"""
CSR Donor Lead Scoring Service for Task 11.

Calculates transparent 0–100 lead scores, assigns priority bands, evaluates
evidence coverage, generates explanations (positive/limiting factors), and ranks
candidates deterministically.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ai_service.config import get_settings
from ai_service.schemas.scoring import (
    CandidateScoringInput,
    LeadScore,
    PriorityBand,
    ScoringComponentsBreakdown,
)
from ai_service.scoring.components import ComponentScorers
from ai_service.scoring.mca_loader import MCACandidateRegistry, get_mca_registry
from ai_service.scoring.ranker import LeadRanker


class CSRLeadScoringService:
    """Core service for scoring, explaining, and ranking corporate donor candidates."""

    def __init__(
        self,
        mca_registry: Optional[MCACandidateRegistry] = None,
        target_states: Optional[List[str]] = None,
        scoring_version: Optional[str] = None,
    ):
        settings = get_settings()
        self.mca_registry = mca_registry or get_mca_registry()
        self.target_states = target_states or settings.JALDHAARA_TARGET_STATES
        self.scoring_version = scoring_version or settings.SCORING_VERSION
        self.scorers = ComponentScorers()
        self.ranker = LeadRanker()

    @staticmethod
    def _determine_priority_band(score: float) -> PriorityBand:
        """Assigns priority band based on configuration thresholds."""
        if score >= 80.0:
            return PriorityBand.HIGH_PRIORITY
        elif score >= 60.0:
            return PriorityBand.MEDIUM_PRIORITY
        elif score >= 40.0:
            return PriorityBand.LOW_PRIORITY
        else:
            return PriorityBand.VERY_LOW_PRIORITY

    def score_company(
        self,
        candidate: CandidateScoringInput,
        target_states: Optional[List[str]] = None,
    ) -> LeadScore:
        """Evaluates a single corporate candidate across 7 dimensions and returns LeadScore."""
        active_target_states = target_states or self.target_states
        mca_record = self.mca_registry.lookup(candidate.company)

        # 1. Calculate Component Scores
        c_wash_rel = self.scorers.score_wash_relevance(candidate)
        c_wash_spend = self.scorers.score_wash_spending(candidate)
        c_freshness = self.scorers.score_freshness(candidate)
        c_multi_year = self.scorers.score_multi_year_commitment(candidate)
        c_historical = self.scorers.score_historical_track_record(candidate, mca_record)
        c_geography = self.scorers.score_geographic_alignment(candidate, active_target_states, mca_record)
        c_trend = self.scorers.score_recent_trend(candidate)

        components_breakdown = ScoringComponentsBreakdown(
            wash_relevance=c_wash_rel,
            wash_spending=c_wash_spend,
            freshness=c_freshness,
            multi_year_commitment=c_multi_year,
            historical_track_record=c_historical,
            geographic_alignment=c_geography,
            recent_trend=c_trend,
        )

        all_components = [
            c_wash_rel,
            c_wash_spend,
            c_freshness,
            c_multi_year,
            c_historical,
            c_geography,
            c_trend,
        ]

        # 2. Total Score (0–100)
        total_pts = sum(c.points_awarded for c in all_components)
        total_score = round(min(max(total_pts, 0.0), 100.0), 1)

        # 3. Priority Band
        priority_band = self._determine_priority_band(total_score)

        # 4. Explainability Factors
        positive_factors: List[str] = []
        limiting_factors: List[str] = []
        missing_information: List[str] = []

        for c in all_components:
            ratio = (c.points_awarded / c.max_points) if c.max_points > 0 else 0.0

            if c.is_insufficient_evidence:
                missing_information.append(f"{c.name.replace('_', ' ').title()}: {c.rationale}")
            elif ratio >= 0.70:
                positive_factors.append(
                    f"+ {c.name.replace('_', ' ').title()} ({c.points_awarded}/{c.max_points}): {c.rationale}"
                )
            elif ratio <= 0.40:
                limiting_factors.append(
                    f"- {c.name.replace('_', ' ').title()} ({c.points_awarded}/{c.max_points}): {c.rationale}"
                )

        # 5. Evidence Coverage
        dimensions_with_data = sum(1 for c in all_components if not c.is_insufficient_evidence)
        evidence_coverage = round(dimensions_with_data / float(len(all_components)), 2)

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return LeadScore(
            company=candidate.company,
            total_score=total_score,
            priority_band=priority_band,
            components=components_breakdown,
            positive_factors=positive_factors,
            limiting_factors=limiting_factors,
            missing_information=missing_information,
            evidence_coverage=evidence_coverage,
            scoring_version=self.scoring_version,
            scored_at=now_iso,
            metadata={
                "mca_matched": bool(mca_record is not None),
                "mca_rank": mca_record.get("mca_rank") if mca_record else None,
                "target_states_count": len(active_target_states),
            },
        )

    def score_companies(
        self,
        candidates: List[CandidateScoringInput],
        target_states: Optional[List[str]] = None,
    ) -> List[LeadScore]:
        """Scores multiple candidate companies and returns them sorted by deterministic ranking."""
        scored_leads = [self.score_company(cand, target_states) for cand in candidates]
        return self.ranker.rank_leads(scored_leads)

    def score_top_mca_candidates(
        self,
        limit: int = 10,
        target_states: Optional[List[str]] = None,
    ) -> List[LeadScore]:
        """Convenience method to score and rank top candidates directly from MCA registry."""
        mca_records = self.mca_registry.get_all()[:limit]
        candidate_inputs = []

        for rec in mca_records:
            cand = CandidateScoringInput(
                company=rec["company_name"],
                wash_classification="WASH_RELEVANT",
                wash_subcategories=rec.get("csr_sectors", []),
                total_csr_spend_crore=None,
                wash_spend_crore=rec.get("total_wash_spend_crore"),
                water_spend_crore=rec.get("total_water_spend_crore"),
                sanitation_spend_crore=rec.get("total_sanitation_spend_crore"),
                freshness_status="YELLOW",  # Unverified live document baseline
                has_multi_year_commitment=True if (rec.get("active_years", 0) >= 3) else False,
                mca_active_years_count=int(rec.get("active_years", 0)),
                mca_total_wash_spend_crore=rec.get("total_wash_spend_crore"),
                company_states=rec.get("states", []),
                wash_direction="STABLE",
            )
            candidate_inputs.append(cand)

        return self.score_companies(candidate_inputs, target_states)
