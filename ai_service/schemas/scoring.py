"""
Pydantic Schemas for Task 11: CSR Donor Lead Scoring.

Defines models for:
- 0–100 transparent lead scoring across 7 weighted dimensions
- Priority bands: HIGH_PRIORITY, MEDIUM_PRIORITY, LOW_PRIORITY, VERY_LOW_PRIORITY
- Positive and limiting factor explainability
- Evidence coverage and data completeness
- Deterministic multi-criteria ranking outputs
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai_service.schemas.verification import CSREvidenceReference


class PriorityBand(str, Enum):
    """Configuration-driven priority classification bands."""

    HIGH_PRIORITY = "HIGH_PRIORITY"          # 80–100
    MEDIUM_PRIORITY = "MEDIUM_PRIORITY"      # 60–79
    LOW_PRIORITY = "LOW_PRIORITY"            # 40–59
    VERY_LOW_PRIORITY = "VERY_LOW_PRIORITY"  # 0–39


class ScoreComponentItem(BaseModel):
    """Detailed score and rationale for a single dimension."""

    name: str = Field(..., description="Name of the scoring dimension")
    points_awarded: float = Field(..., description="Points awarded for this dimension")
    max_points: float = Field(..., description="Maximum possible points for this dimension")
    percentage: float = Field(..., description="Percentage of max points earned")
    is_insufficient_evidence: bool = Field(
        False, description="Flag indicating score was 0 due to missing data rather than negative evidence"
    )
    rationale: str = Field(..., description="Transparent explanation for awarded points")
    evidence_sources: List[str] = Field(
        default_factory=list, description="Source documents or disclosures supporting this component"
    )


class ScoringComponentsBreakdown(BaseModel):
    """Container for the 7 individual scoring components (totaling 100 points)."""

    wash_relevance: ScoreComponentItem = Field(..., description="Dimension 1: WASH Relevance (30 pts)")
    wash_spending: ScoreComponentItem = Field(
        ..., description="Dimension 2: WASH Spending / Financial Signal (20 pts)"
    )
    freshness: ScoreComponentItem = Field(..., description="Dimension 3: Freshness / Recency (15 pts)")
    multi_year_commitment: ScoreComponentItem = Field(
        ..., description="Dimension 4: Multi-Year Commitment (10 pts)"
    )
    historical_track_record: ScoreComponentItem = Field(
        ..., description="Dimension 5: Historical WASH Track Record (10 pts)"
    )
    geographic_alignment: ScoreComponentItem = Field(
        ..., description="Dimension 6: Geographic Alignment (10 pts)"
    )
    recent_trend: ScoreComponentItem = Field(..., description="Dimension 7: Positive Recent Trend (5 pts)")


class CandidateScoringInput(BaseModel):
    """Input payload representing a candidate company's attributes across tasks."""

    company: str = Field(..., description="Company name")
    wash_classification: Optional[str] = Field(
        None, description="Task 6 status: WASH_RELEVANT, PARTIALLY_RELEVANT, NOT_WASH_RELEVANT, INSUFFICIENT_EVIDENCE"
    )
    wash_subcategories: List[str] = Field(
        default_factory=list, description="Categories like safe_drinking_water, sanitation, hygiene"
    )
    total_csr_spend_crore: Optional[float] = Field(None, description="Total CSR spend in ₹ Crores")
    wash_spend_crore: Optional[float] = Field(None, description="Actual WASH expenditure in ₹ Crores")
    water_spend_crore: Optional[float] = Field(None, description="Water expenditure in ₹ Crores")
    sanitation_spend_crore: Optional[float] = Field(None, description="Sanitation expenditure in ₹ Crores")
    freshness_status: Optional[str] = Field(
        None, description="Task 10 status: GREEN, YELLOW, RED"
    )
    has_multi_year_commitment: Optional[bool] = Field(
        None, description="Whether company has ongoing multi-year programs"
    )
    is_continuing_project: Optional[bool] = Field(
        None, description="Whether current project continues from prior period"
    )
    mca_active_years_count: Optional[int] = Field(
        None, description="Number of distinct years with WASH initiatives in MCA data"
    )
    mca_total_wash_spend_crore: Optional[float] = Field(
        None, description="Cumulative historical WASH spend in ₹ Crores"
    )
    company_states: List[str] = Field(
        default_factory=list, description="States where company conducts CSR operations"
    )
    company_districts: List[str] = Field(
        default_factory=list, description="Districts where company conducts CSR operations"
    )
    wash_direction: Optional[str] = Field(
        None, description="Task 9 direction: INCREASED, STABLE, NEW_FOCUS, MIXED, DECREASED, LOST_FOCUS"
    )
    evidence_references: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references from previous tasks"
    )


class LeadScore(BaseModel):
    """Complete, transparent lead scoring result for a CSR candidate."""

    company: str = Field(..., description="Company name")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Overall transparent score (0–100)")
    priority_band: PriorityBand = Field(..., description="Priority categorization band")
    components: ScoringComponentsBreakdown = Field(
        ..., description="Breakdown across all 7 weighted dimensions"
    )
    positive_factors: List[str] = Field(
        default_factory=list, description="Highlights positively impacting the score"
    )
    limiting_factors: List[str] = Field(
        default_factory=list, description="Points that constrained or reduced the score"
    )
    missing_information: List[str] = Field(
        default_factory=list, description="Unverified or missing data points"
    )
    evidence_coverage: float = Field(
        ..., ge=0.0, le=1.0, description="Proportion of scoring dimensions with available data (0.0–1.0)"
    )
    scoring_version: str = Field("v1", description="Algorithm version identifier")
    scored_at: str = Field(..., description="ISO-8601 timestamp when score was generated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata")


class BatchScoringRequest(BaseModel):
    """Payload for scoring a list of corporate candidates."""

    candidates: List[CandidateScoringInput] = Field(
        ..., min_length=1, description="List of candidate companies to evaluate"
    )
    target_states: Optional[List[str]] = Field(
        None, description="Optional override list of Jaldhaara operational target states"
    )


class BatchScoringResponse(BaseModel):
    """Ranked batch scoring output."""

    total_candidates: int = Field(..., description="Count of evaluated candidate companies")
    scored_candidates: List[LeadScore] = Field(
        ..., description="Deterministically ranked list of candidates"
    )
    scoring_version: str = Field("v1", description="Algorithm version identifier")
    scored_at: str = Field(..., description="ISO-8601 timestamp when batch was processed")
