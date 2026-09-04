"""
Pydantic Schemas for Task 6: AI/NLP CSR + WASH Classification.
Defines contracts for classification results, evidence items with page numbers,
and confidence metrics.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WASHClassificationEnum(str, Enum):
    WASH_RELEVANT = "WASH_RELEVANT"
    PARTIALLY_RELEVANT = "PARTIALLY_RELEVANT"
    NOT_WASH_RELEVANT = "NOT_WASH_RELEVANT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceStrengthEnum(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    NEGATIVE = "NEGATIVE"  # E.g. industrial water efficiency, factory ETP


class WASHEvidenceItem(BaseModel):
    """Verbatim evidence snippet supporting the WASH classification."""

    text: str = Field(..., description="Verbatim text excerpt demonstrating presence or context")
    page: Optional[int] = Field(None, description="1-indexed PDF page where evidence occurs")
    category: str = Field(
        ...,
        description="WASH pillar: water, sanitation, hygiene, community_wash, or negative_industrial",
    )
    project_name: Optional[str] = Field(None, description="Associated project title if identified")
    strength: str = Field(
        EvidenceStrengthEnum.STRONG.value,
        description="Strength of evidence: STRONG, WEAK, or NEGATIVE",
    )


class WASHClassificationResult(BaseModel):
    """Structured AI/NLP classification result for CSR WASH relevance."""

    classification: str = Field(
        ...,
        description="WASH_RELEVANT, PARTIALLY_RELEVANT, NOT_WASH_RELEVANT, or INSUFFICIENT_EVIDENCE",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in the classification (0.0 to 1.0, not donor lead priority)",
    )
    water_relevance: bool = Field(
        False, description="True if genuine safe drinking water or community water access exists"
    )
    sanitation_relevance: bool = Field(
        False, description="True if community sanitation or toilet facilities exist"
    )
    hygiene_relevance: bool = Field(
        False, description="True if hygiene, WASH training, or menstrual hygiene programs exist"
    )
    reasoning: str = Field(
        ..., description="Context-aware rationale explaining the classification decision"
    )
    evidence: List[WASHEvidenceItem] = Field(
        default_factory=list, description="List of verbatim evidence snippets with page references"
    )
    evidence_pages: List[int] = Field(
        default_factory=list, description="Unique sorted list of pages containing evidence"
    )
    model_used: str = Field(
        ..., description="LLM provider or rule-based model identifier used for inference"
    )
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata of the classified document"
    )
    processing_time_seconds: float = Field(
        0.0, description="Inference execution duration in seconds"
    )
    errors: List[str] = Field(
        default_factory=list, description="Non-fatal warnings or error messages"
    )
