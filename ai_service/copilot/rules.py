"""
Deterministic Rules Engine for Task 12: Next-Best-Action Recommendation Copilot.

Maps company intelligence (Lead Score, Priority Band, Freshness, WASH Direction,
Evidence Coverage, Multi-Year Commitments) into controlled Next-Best Actions.
"""

from typing import Any, Dict, List, Optional, Tuple
from ai_service.schemas.copilot import RecommendationAction, RecommendationRequest, RecommendationResult
from ai_service.schemas.verification import CSREvidenceReference


class RecommendationRulesEngine:
    """
    Evaluates corporate CSR intelligence deterministically against controlled actions.
    Ensures that recommendations are never arbitrarily invented by an LLM and are
    traceably justified with positive factors, limiting factors, risks, and next steps.
    """

    @classmethod
    def evaluate(
        cls, request: RecommendationRequest
    ) -> Tuple[RecommendationAction, float, List[str], List[str], List[str], List[str], List[str], List[str]]:
        """
        Evaluate candidate data against deterministic rules.

        Returns:
            Tuple of:
            - recommended_action (RecommendationAction)
            - confidence (float: 0.0 - 1.0)
            - reasons (List[str])
            - positive_factors (List[str])
            - limiting_factors (List[str])
            - missing_information (List[str])
            - risks (List[str])
            - next_steps (List[str])
        """
        lead_score = request.lead_score if request.lead_score is not None else 0.0
        freshness = (request.freshness_status or "YELLOW").upper()
        wash_dir = (request.wash_direction or "INSUFFICIENT_EVIDENCE").upper()
        wash_class = (request.wash_classification or "").upper()
        multi_year = bool(request.has_multi_year_commitment)
        # If evidence_coverage is None, treat as adequately covered (1.0) unless explicitly specified
        evidence_cov = request.evidence_coverage if request.evidence_coverage is not None else 1.0

        reasons: List[str] = []
        positive_factors: List[str] = []
        limiting_factors: List[str] = []
        missing_information: List[str] = []
        risks: List[str] = []
        next_steps: List[str] = []

        # Analyze factors
        if lead_score >= 80.0:
            positive_factors.append(f"High donor lead score of {lead_score:.1f}/100 indicating exceptional donor potential.")
        elif lead_score >= 60.0:
            positive_factors.append(f"Solid donor lead score of {lead_score:.1f}/100 indicating good alignment.")
        elif lead_score >= 40.0:
            limiting_factors.append(f"Moderate donor lead score of {lead_score:.1f}/100.")
        else:
            limiting_factors.append(f"Low donor lead score of {lead_score:.1f}/100.")

        if freshness == "GREEN":
            positive_factors.append("Current and verified CSR disclosures (GREEN freshness status).")
        elif freshness == "YELLOW":
            limiting_factors.append("Disclosures are aging or require re-verification (YELLOW freshness status).")
            risks.append("Information may reflect prior reporting cycles rather than current fiscal year priorities.")
        elif freshness == "RED":
            limiting_factors.append("Disclosures indicate active departure or discontinuation of WASH activities (RED freshness status).")
            risks.append("High risk of immediate rejection due to shifted corporate priorities.")

        if wash_dir in ["INCREASED", "NEW_FOCUS"]:
            positive_factors.append(f"WASH commitment trajectory is actively growing ({wash_dir}).")
        elif wash_dir == "STABLE":
            positive_factors.append("Consistent, stable historical track record in WASH funding.")
        elif wash_dir in ["DECREASED", "LOST_FOCUS"]:
            limiting_factors.append(f"WASH focus has diminished or ceased ({wash_dir}).")

        if multi_year:
            positive_factors.append("Demonstrated willingness to enter multi-year CSR commitments.")
        else:
            limiting_factors.append("No verified multi-year CSR commitments identified.")

        if evidence_cov < 0.6:
            missing_information.append(f"Low evidence coverage ratio ({evidence_cov*100:.1f}%). Key project or budgetary disclosures are missing.")
            risks.append("CSR outreach strategy would rely on partial or unconfirmed data.")
        else:
            positive_factors.append(f"High verifiable evidence coverage ({evidence_cov*100:.1f}%).")

        if wash_class == "NOT_WASH_RELEVANT":
            limiting_factors.append("Recent CSR activities do not relate to Water, Sanitation, or Hygiene (WASH).")

        # Deterministic Decision Logic
        # 1. Negative / Out-of-scope triggers -> DO_NOT_PRIORITIZE
        if (
            wash_dir == "LOST_FOCUS"
            or freshness == "RED"
            or wash_class == "NOT_WASH_RELEVANT"
            or lead_score < 40.0
        ):
            action = RecommendationAction.DO_NOT_PRIORITIZE
            confidence = 0.90 if freshness == "RED" or wash_dir == "LOST_FOCUS" else 0.85
            reasons.append(
                f"Candidate displays low alignment or diminished WASH interest (Score: {lead_score:.1f}, "
                f"Freshness: {freshness}, WASH Direction: {wash_dir})."
            )
            next_steps.extend([
                "Deprioritize active outreach for current quarterly cycle.",
                "Archive company in the lead pipeline with monitoring flag for subsequent annual filings.",
                "Direct partnership resources to higher-priority candidates."
            ])

        # 2. Re-verification triggers -> REVERIFY
        elif freshness == "YELLOW" and lead_score >= 60.0 and evidence_cov >= 0.5:
            action = RecommendationAction.REVERIFY
            confidence = 0.85
            reasons.append(
                f"Candidate has strong fundamental alignment (Score: {lead_score:.1f}) but disclosures are aging "
                f"or require verification against the latest annual filing."
            )
            risks.append("Initiating outreach without re-verifying current year budget or board allocations may misalign proposals.")
            next_steps.extend([
                "Run document discovery (Task 1) and retrieve newest annual report or MCA filing.",
                "Execute Task 9 Verification to re-baseline expenditure and priority changes.",
                "Update freshness assessment before scheduling outreach."
            ])

        # 3. Top candidates with verified multi-year commitments -> APPROACH_WITH_PARTNERSHIP_PROPOSAL
        elif lead_score >= 80.0 and freshness == "GREEN" and multi_year:
            action = RecommendationAction.APPROACH_WITH_PARTNERSHIP_PROPOSAL
            confidence = 0.95
            reasons.append(
                f"Top-tier donor candidate (Score: {lead_score:.1f}, HIGH_PRIORITY) with current verified disclosures "
                f"and demonstrated commitment to multi-year CSR infrastructure programs."
            )
            next_steps.extend([
                "Formulate multi-year institutional partnership proposal focusing on water purification hubs.",
                "Schedule exploratory dialogue with the CSR committee head / sustainability lead.",
                "Present multi-year co-funding impact model aligned with corporate geographic priorities."
            ])

        # 4. Top candidates without multi-year commitments -> APPROACH_WITH_IMPACT_PROPOSAL
        elif lead_score >= 80.0 and freshness == "GREEN":
            action = RecommendationAction.APPROACH_WITH_IMPACT_PROPOSAL
            confidence = 0.90
            reasons.append(
                f"High-priority donor candidate (Score: {lead_score:.1f}) with current verified disclosures; "
                f"best suited for targeted, milestone-driven project impact proposals."
            )
            next_steps.extend([
                "Draft targeted project proposal for high-need water-stressed districts matching donor operations.",
                "Prepare turnkey implementation timeline and community beneficiary projections.",
                "Initiate introductory presentation to CSR program manager."
            ])

        # 5. Low evidence coverage on viable candidates -> RESEARCH_BEFORE_OUTREACH
        elif lead_score >= 60.0 and evidence_cov < 0.6:
            action = RecommendationAction.RESEARCH_BEFORE_OUTREACH
            confidence = 0.80
            reasons.append(
                f"Candidate has attractive scoring indicators (Score: {lead_score:.1f}) but insufficient "
                f"evidence coverage ({evidence_cov*100:.1f}%) prevents tailoring a high-conviction proposal."
            )
            next_steps.extend([
                "Conduct targeted research on recent CSR committee announcements and press releases.",
                "Retrieve missing BRSR / Business Responsibility disclosures.",
                "Identify specific geographical regions where company CSR funds are actively deployed."
            ])

        # 6. Moderate candidates or aging disclosures -> MONITOR
        elif (40.0 <= lead_score < 60.0) or (freshness == "YELLOW" and lead_score < 60.0):
            action = RecommendationAction.MONITOR
            confidence = 0.80
            reasons.append(
                f"Candidate demonstrates moderate donor suitability (Score: {lead_score:.1f}, Priority: "
                f"{request.priority_band or 'LOW_PRIORITY'}), warranting observation and monitoring rather than immediate direct outreach."
            )
            next_steps.extend([
                "Set monitoring trigger for next financial year CSR disclosures.",
                "Track if the company expands CSR budget or increases focus on clean drinking water initiatives.",
                "Re-score after new CSR filings become available."
            ])

        # 7. General outreach fallback for viable candidates (e.g. 60–79 with GREEN freshness) -> PRIORITIZE_OUTREACH
        elif lead_score >= 60.0 and freshness == "GREEN":
            action = RecommendationAction.PRIORITIZE_OUTREACH
            confidence = 0.85
            reasons.append(
                f"Qualified donor candidate (Score: {lead_score:.1f}, Medium/High Priority) with verified green freshness. "
                f"Active outreach is recommended."
            )
            next_steps.extend([
                "Prioritize in upcoming outreach sprint.",
                "Prepare standard Jaldhaara capability deck tailored to company's CSR focus.",
                "Contact CSR secretariat to request introductory briefing."
            ])

        # Default fallback
        else:
            action = RecommendationAction.MONITOR
            confidence = 0.70
            reasons.append(f"Candidate requires monitoring due to mixed score ({lead_score:.1f}) and data indicators.")
            next_steps.append("Maintain in periodic monitoring pipeline.")

        return action, confidence, reasons, positive_factors, limiting_factors, missing_information, risks, next_steps
