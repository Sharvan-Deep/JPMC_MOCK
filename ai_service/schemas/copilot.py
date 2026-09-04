"""
Pydantic Schemas for Task 12: Next-Best-Action Recommendation Copilot.

Defines models for:
- Controlled recommendation actions (PRIORITIZE_OUTREACH, MONITOR, etc.)
- Comprehensive, evidence-grounded recommendation results
- Interactive copilot chat queries and grounded responses
- Recommendation history and versioning
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ai_service.schemas.verification import CSREvidenceReference


class RecommendationAction(str, Enum):
    """Controlled set of advisory next-best actions for Jaldhaara staff."""

    PRIORITIZE_OUTREACH = "PRIORITIZE_OUTREACH"
    APPROACH_WITH_PARTNERSHIP_PROPOSAL = "APPROACH_WITH_PARTNERSHIP_PROPOSAL"
    APPROACH_WITH_IMPACT_PROPOSAL = "APPROACH_WITH_IMPACT_PROPOSAL"
    RESEARCH_BEFORE_OUTREACH = "RESEARCH_BEFORE_OUTREACH"
    MONITOR = "MONITOR"
    REVERIFY = "REVERIFY"
    DO_NOT_PRIORITIZE = "DO_NOT_PRIORITIZE"


class RecommendationRequest(BaseModel):
    """Payload to generate a next-best-action recommendation."""

    company: str = Field(..., description="Company name")
    lead_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Task 11 Lead Score (0–100)")
    priority_band: Optional[str] = Field(None, description="Task 11 Priority Band")
    freshness_status: Optional[str] = Field(None, description="Task 10 Freshness Status (GREEN/YELLOW/RED)")
    wash_classification: Optional[str] = Field(None, description="Task 6 WASH Classification")
    wash_direction: Optional[str] = Field(None, description="Task 9 WASH Direction")
    has_multi_year_commitment: Optional[bool] = Field(None, description="Multi-year commitment status")
    evidence_coverage: Optional[float] = Field(None, ge=0.0, le=1.0, description="Evidence coverage ratio")
    wash_spend_crore: Optional[float] = Field(None, description="Actual WASH expenditure in ₹ Crores")
    financial_year: Optional[str] = Field(None, description="Evaluated financial year")
    evidence: List[CSREvidenceReference] = Field(default_factory=list, description="Supporting evidence references")


class RecommendationResult(BaseModel):
    """Complete, evidence-grounded recommendation result with human advisory boundary."""

    recommendation_id: Optional[str] = Field(None, description="Unique recommendation ID")
    company: str = Field(..., description="Company name")
    recommended_action: RecommendationAction = Field(..., description="Selected next-best action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this recommendation")
    reasons: List[str] = Field(default_factory=list, description="Core affirmative rationales")
    supporting_evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Traceable evidence anchoring the recommendation"
    )
    positive_factors: List[str] = Field(
        default_factory=list, description="Favorable attributes identified"
    )
    limiting_factors: List[str] = Field(
        default_factory=list, description="Constraining factors or weaknesses"
    )
    missing_information: List[str] = Field(
        default_factory=list, description="Missing or unverified intelligence"
    )
    risks: List[str] = Field(
        default_factory=list, description="Advisory caveats and risks staff should be cautious of"
    )
    next_steps: List[str] = Field(
        default_factory=list, description="Concrete next steps suggested for staff"
    )
    is_advisory: bool = Field(
        True, description="Strict human boundary flag: advisory only, no automated action taken"
    )
    scoring_version: str = Field("v1", description="Lead scoring version")
    recommendation_version: str = Field("v1", description="Recommendation logic version")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata")


class RecommendationHistoryResponse(BaseModel):
    """Chronological history of recommendations for a company."""

    company: str = Field(..., description="Company name")
    current_recommendation: Optional[RecommendationResult] = Field(
        None, description="Most recent recommendation"
    )
    history: List[RecommendationResult] = Field(
        default_factory=list, description="Chronological timeline of past recommendations"
    )


class CopilotChatRequest(BaseModel):
    """Staff natural language question about a candidate company."""

    company: str = Field(..., description="Target company name")
    question: str = Field(..., min_length=1, description="Question asked by staff member")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list, description="Prior conversational turns"
    )


class CopilotChatResponse(BaseModel):
    """Grounded interactive response from the recommendation assistant."""

    company: str = Field(..., description="Target company name")
    question: str = Field(..., description="Original question asked")
    answer: str = Field(..., description="Grounded answer based strictly on verified evidence")
    supporting_sources: List[str] = Field(
        default_factory=list, description="Document chunks, pages, or structured citations"
    )
    evidence_status: str = Field(
        "AVAILABLE", description="'AVAILABLE' or 'INSUFFICIENT_EVIDENCE'"
    )
    timestamp: str = Field(..., description="ISO-8601 response timestamp")
