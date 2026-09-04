"""
Scoring Component Calculators for Task 11: CSR Donor Lead Scoring.

Implements transparent, explainable 0–100 scoring across 7 orthogonal dimensions:
1. WASH Relevance (30 pts)
2. WASH Spending / Financial Signal (20 pts)
3. Freshness / Recency (15 pts)
4. Multi-Year Commitment (10 pts)
5. Historical WASH Track Record (10 pts)
6. Geographic Alignment (10 pts)
7. Positive Recent Trend (5 pts)

Ensures zero double-counting, preserves evidence links, and distinguishes
missing data from genuine zero scores.
"""

from typing import Any, Dict, List, Optional, Tuple
from ai_service.schemas.scoring import CandidateScoringInput, ScoreComponentItem


class ComponentScorers:
    """Evaluates the 7 individual scoring dimensions with full auditability."""

    # --------------------------------------------------------------------------
    # 1. WASH Relevance (30 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_wash_relevance(input_data: CandidateScoringInput) -> ScoreComponentItem:
        max_pts = 30.0
        status = (input_data.wash_classification or "").upper().strip()

        if status == "WASH_RELEVANT":
            pts = 30.0
            sub_str = f" ({', '.join(input_data.wash_subcategories)})" if input_data.wash_subcategories else ""
            rationale = f"Company is fully WASH relevant under Task 6 classification{sub_str}."
            insufficient = False
        elif status == "PARTIALLY_RELEVANT":
            pts = 15.0
            rationale = "Company activities demonstrate partial or secondary alignment with WASH sectors."
            insufficient = False
        elif status == "NOT_WASH_RELEVANT":
            pts = 0.0
            rationale = "Company CSR portfolio shows no alignment with WASH sectors."
            insufficient = False
        else:
            pts = 0.0
            rationale = "Task 6 WASH classification evidence is unavailable or insufficient."
            insufficient = True

        evidence_sources = [
            f"Classification: {status or 'UNSPECIFIED'}",
        ]
        if input_data.wash_subcategories:
            evidence_sources.append(f"Subcategories: {', '.join(input_data.wash_subcategories)}")

        return ScoreComponentItem(
            name="wash_relevance",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=insufficient,
            rationale=rationale,
            evidence_sources=evidence_sources,
        )

    # --------------------------------------------------------------------------
    # 2. WASH Spending / Financial Signal (20 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_wash_spending(input_data: CandidateScoringInput) -> ScoreComponentItem:
        max_pts = 20.0
        spend = input_data.wash_spend_crore
        total = input_data.total_csr_spend_crore

        if spend is None:
            # Check if MCA historical spend is present as backup
            if input_data.mca_total_wash_spend_crore is not None and input_data.mca_total_wash_spend_crore > 0:
                spend = input_data.mca_total_wash_spend_crore / max(input_data.mca_active_years_count or 1, 1)
            else:
                return ScoreComponentItem(
                    name="wash_spending",
                    points_awarded=0.0,
                    max_points=max_pts,
                    percentage=0.0,
                    is_insufficient_evidence=True,
                    rationale="Actual WASH expenditure data is unavailable.",
                    evidence_sources=["Spending data: Missing"],
                )

        ratio = (spend / total) if (total and total > 0 and spend is not None) else 0.0

        # Banded scoring to prevent sheer budget size from dominating:
        if spend >= 10.0 or (spend >= 2.0 and ratio >= 0.20):
            pts = 20.0
            tier = "Very strong"
        elif spend >= 5.0 or (spend >= 1.0 and ratio >= 0.10):
            pts = 15.0
            tier = "Strong"
        elif spend >= 2.0 or ratio >= 0.05:
            pts = 10.0
            tier = "Moderate"
        elif spend > 0.0:
            pts = 5.0
            tier = "Weak"
        else:
            pts = 0.0
            tier = "Zero"

        ratio_pct = f" ({round(ratio * 100, 1)}% of total CSR)" if total else ""
        rationale = f"{tier} WASH financial commitment: ₹{round(spend, 2)} Cr{ratio_pct}."

        evidence_sources = [f"WASH Spend: ₹{round(spend, 2)} Cr"]
        if total:
            evidence_sources.append(f"Total CSR: ₹{round(total, 2)} Cr")
        if input_data.water_spend_crore:
            evidence_sources.append(f"Water: ₹{round(input_data.water_spend_crore, 2)} Cr")
        if input_data.sanitation_spend_crore:
            evidence_sources.append(f"Sanitation: ₹{round(input_data.sanitation_spend_crore, 2)} Cr")

        return ScoreComponentItem(
            name="wash_spending",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=False,
            rationale=rationale,
            evidence_sources=evidence_sources,
        )

    # --------------------------------------------------------------------------
    # 3. Freshness / Recency (15 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_freshness(input_data: CandidateScoringInput) -> ScoreComponentItem:
        max_pts = 15.0
        status = (input_data.freshness_status or "").upper().strip()

        if status == "GREEN":
            pts = 15.0
            rationale = "Task 10 verified GREEN: information verified against latest available disclosure cycle."
            insufficient = False
        elif status == "YELLOW":
            pts = 7.0
            rationale = "Task 10 status is YELLOW: data is from a prior financial year or awaiting current verification."
            insufficient = False
        elif status == "RED":
            pts = 0.0
            rationale = "Task 10 status is RED: verified evidence indicates company discontinued WASH focus."
            insufficient = False
        else:
            pts = 0.0
            rationale = "Freshness status is unavailable / unverified."
            insufficient = True

        return ScoreComponentItem(
            name="freshness",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=insufficient,
            rationale=rationale,
            evidence_sources=[f"Task 10 Status: {status or 'UNSPECIFIED'}"],
        )

    # --------------------------------------------------------------------------
    # 4. Multi-Year Commitment (10 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_multi_year_commitment(input_data: CandidateScoringInput) -> ScoreComponentItem:
        max_pts = 10.0

        if input_data.has_multi_year_commitment is True:
            pts = 10.0
            rationale = "Strong multi-year commitment demonstrated with ongoing multi-year programs."
            insufficient = False
        elif input_data.is_continuing_project is True:
            pts = 6.0
            rationale = "Moderate commitment demonstrated via projects continuing across financial periods."
            insufficient = False
        elif input_data.has_multi_year_commitment is False:
            pts = 3.0
            rationale = "Single-year CSR project activity demonstrated without multi-year commitment."
            insufficient = False
        else:
            pts = 0.0
            rationale = "Multi-year commitment not demonstrated in available disclosures."
            insufficient = True

        return ScoreComponentItem(
            name="multi_year_commitment",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=insufficient,
            rationale=rationale,
            evidence_sources=[
                f"Multi-Year: {input_data.has_multi_year_commitment}",
                f"Continuing Project: {input_data.is_continuing_project}",
            ],
        )

    # --------------------------------------------------------------------------
    # 5. Historical WASH Track Record (10 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_historical_track_record(
        input_data: CandidateScoringInput, mca_record: Optional[Dict[str, Any]] = None
    ) -> ScoreComponentItem:
        max_pts = 10.0
        active_years = input_data.mca_active_years_count

        if active_years is None and mca_record:
            active_years = int(mca_record.get("active_years", 0) or mca_record.get("water_active_years", 0))

        if active_years is None or active_years <= 0:
            return ScoreComponentItem(
                name="historical_track_record",
                points_awarded=0.0,
                max_points=max_pts,
                percentage=0.0,
                is_insufficient_evidence=True,
                rationale="No historical MCA WASH records found for this company.",
                evidence_sources=["MCA Historical: Not found"],
            )

        if active_years >= 5:
            pts = 10.0
            level = "Exceptional multi-year track record"
        elif active_years >= 3:
            pts = 7.0
            level = "Strong historical track record"
        elif active_years == 2:
            pts = 5.0
            level = "Moderate historical track record"
        else:
            pts = 3.0
            level = "Initial / single-year historical presence"

        spend_info = ""
        if mca_record and mca_record.get("total_wash_spend_crore"):
            spend_info = f" (₹{round(mca_record['total_wash_spend_crore'], 2)} Cr cumulative MCA spend)"

        rationale = f"{level} across {active_years} active financial years{spend_info}."

        evidence_sources = [f"Active Years: {active_years}"]
        if mca_record and mca_record.get("wash_record_count"):
            evidence_sources.append(f"MCA Record Count: {mca_record['wash_record_count']}")

        return ScoreComponentItem(
            name="historical_track_record",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=False,
            rationale=rationale,
            evidence_sources=evidence_sources,
        )

    # --------------------------------------------------------------------------
    # 6. Geographic Alignment (10 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_geographic_alignment(
        input_data: CandidateScoringInput,
        target_states: List[str],
        mca_record: Optional[Dict[str, Any]] = None,
    ) -> ScoreComponentItem:
        max_pts = 10.0
        # Combine states from candidate input and MCA record
        cand_states = set(s.strip().title() for s in input_data.company_states if s and s.strip())
        if not cand_states and mca_record and mca_record.get("states"):
            cand_states = set(s.strip().title() for s in mca_record["states"] if s and s.strip())

        if not cand_states:
            return ScoreComponentItem(
                name="geographic_alignment",
                points_awarded=0.0,
                max_points=max_pts,
                percentage=0.0,
                is_insufficient_evidence=True,
                rationale="Geographic location data is unavailable.",
                evidence_sources=["Geography: Missing"],
            )

        target_set = set(s.strip().title() for s in target_states if s and s.strip())
        overlap = sorted(list(cand_states & target_set))
        has_pan_india = any("Pan India" in s for s in cand_states)

        if len(overlap) >= 3:
            pts = 10.0
            rationale = f"High alignment with Jaldhaara operational regions ({', '.join(overlap[:4])})."
        elif len(overlap) in (1, 2):
            pts = 6.0
            rationale = f"Moderate alignment in core target states ({', '.join(overlap)})."
        elif has_pan_india:
            pts = 4.0
            rationale = "Pan-India operational mandate provides eligible geographic alignment."
        else:
            pts = 0.0
            rationale = f"Operating locations ({', '.join(list(cand_states)[:3])}) do not overlap with target areas."

        evidence_sources = [f"Overlap: {', '.join(overlap) if overlap else 'None'}"]
        if cand_states:
            evidence_sources.append(f"Locations: {', '.join(list(cand_states)[:4])}")

        return ScoreComponentItem(
            name="geographic_alignment",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=False,
            rationale=rationale,
            evidence_sources=evidence_sources,
        )

    # --------------------------------------------------------------------------
    # 7. Positive Recent Trend (5 Points)
    # --------------------------------------------------------------------------
    @staticmethod
    def score_recent_trend(input_data: CandidateScoringInput) -> ScoreComponentItem:
        max_pts = 5.0
        direction = (input_data.wash_direction or "").upper().strip()

        if direction in ("INCREASED", "NEW_FOCUS"):
            pts = 5.0
            rationale = f"Task 9 verified positive trend: {direction} WASH engagement."
            insufficient = False
        elif direction == "STABLE":
            pts = 3.0
            rationale = "Task 9 verified consistent, stable WASH engagement."
            insufficient = False
        elif direction == "MIXED":
            pts = 2.0
            rationale = "Task 9 verified mixed directional signals across spending and programs."
            insufficient = False
        elif direction == "DECREASED":
            pts = 1.0
            rationale = "Task 9 verified reduced WASH activity or spending."
            insufficient = False
        elif direction == "LOST_FOCUS":
            pts = 0.0
            rationale = "Task 9 verified complete cessation / loss of WASH focus."
            insufficient = False
        else:
            pts = 0.0
            rationale = "Recent trend evidence is unavailable or insufficient."
            insufficient = True

        return ScoreComponentItem(
            name="recent_trend",
            points_awarded=pts,
            max_points=max_pts,
            percentage=round((pts / max_pts) * 100.0, 1),
            is_insufficient_evidence=insufficient,
            rationale=rationale,
            evidence_sources=[f"Task 9 Direction: {direction or 'UNSPECIFIED'}"],
        )
