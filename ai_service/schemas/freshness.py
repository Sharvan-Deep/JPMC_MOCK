"""
Pydantic Schemas for Task 10: CSR Freshness System.

Defines models for:
- Freshness states: GREEN, YELLOW, RED
- Source-level freshness tracking (Annual Report, BRSR, Policy, Disclosures)
- Complete FreshnessAssessment with cycle tracking and evidence traceability
- Historical freshness timelines and retrieval contracts
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai_service.schemas.verification import CSREvidenceReference, WASHDirection


class FreshnessStatus(str, Enum):
    """
    Primary CSR/WASH freshness classification states.
    - GREEN: Current information verified against latest disclosure + WASH active.
    - YELLOW: Older FY, unverified current information, missing document, or insufficient evidence.
    - RED: Verified evidence shows the company has moved away from WASH (e.g. LOST_FOCUS).
    """

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class SourceType(str, Enum):
    """Types of CSR disclosure sources."""

    CSR_ANNUAL_REPORT = "CSR_ANNUAL_REPORT"
    BRSR = "BRSR"
    CSR_POLICY = "CSR_POLICY"
    EXCHANGE_DISCLOSURE = "EXCHANGE_DISCLOSURE"
    OTHER = "OTHER"


class SourceFreshnessRecord(BaseModel):
    """Freshness metadata and evaluation for an individual disclosure document."""

    source_name: str = Field(..., description="Name or label of source (e.g. 'Annual Report 2024-25')")
    document_type: str = Field(..., description="Document type (e.g. 'CSR_ANNUAL_REPORT', 'BRSR')")
    document_version: Optional[int] = Field(1, description="Document version number")
    document_hash: Optional[str] = Field(None, description="SHA-256 hash of document")
    source_url: Optional[str] = Field(None, description="Source URL where document was retrieved")
    publication_date: Optional[str] = Field(
        None, description="Official publication date (YYYY-MM-DD) if available; None if unavailable"
    )
    retrieved_at: Optional[str] = Field(None, description="ISO timestamp when document was downloaded")
    verified_at: Optional[str] = Field(None, description="ISO timestamp when document was verified")
    financial_year: Optional[str] = Field(None, description="Reporting financial year (e.g. '2024-25')")
    status: FreshnessStatus = Field(FreshnessStatus.YELLOW, description="Freshness status of this source")
    reason: Optional[str] = Field(None, description="Explanation for source-level status")


class FreshnessAssessment(BaseModel):
    """
    Comprehensive freshness assessment for a company preserving verification cycle,
    source traceability, WASH direction, and audit history.
    """

    assessment_id: Optional[str] = Field(None, description="Unique assessment identifier")
    company: str = Field(..., description="Company name")
    status: FreshnessStatus = Field(..., description="Overall company freshness status (GREEN/YELLOW/RED)")
    reason: str = Field(..., description="Detailed deterministic rationale for assigned status")
    financial_year: Optional[str] = Field(None, description="Financial year evaluated (e.g. '2024-25')")
    document_type: Optional[str] = Field(None, description="Primary document type used for evaluation")
    document_version: Optional[int] = Field(1, description="Primary document version")
    source: Optional[str] = Field(None, description="Primary source name")
    source_url: Optional[str] = Field(None, description="Primary source document URL")
    document_hash: Optional[str] = Field(None, description="Primary document SHA-256 hash")
    publication_date: Optional[str] = Field(
        None, description="Document publication date if explicitly known, never invented"
    )
    retrieved_at: Optional[str] = Field(
        None, description="Timestamp when primary document was retrieved"
    )
    verified_at: Optional[str] = Field(
        None, description="Timestamp when verification was performed"
    )
    verification_cycle: str = Field(
        ..., description="Deterministic verification cycle identifier (e.g. '2026-09')"
    )
    wash_direction: Optional[WASHDirection] = Field(
        None, description="Task 9 synthesized WASH direction"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Supporting evidence references"
    )
    previous_status: Optional[FreshnessStatus] = Field(
        None, description="Previous freshness status from earlier cycle/assessment"
    )
    sources: List[SourceFreshnessRecord] = Field(
        default_factory=list, description="All disclosure sources evaluated for this assessment"
    )
    assessment_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Operational metadata and audit flags"
    )


class FreshnessHistoryResponse(BaseModel):
    """Historical timeline and current summary of company freshness assessments."""

    company: str = Field(..., description="Company name")
    current_status: FreshnessStatus = Field(..., description="Current freshness status")
    last_verified_at: Optional[str] = Field(None, description="Most recent verification timestamp")
    last_verified_financial_year: Optional[str] = Field(
        None, description="Most recently verified financial year"
    )
    verification_cycle: str = Field(..., description="Most recent verification cycle")
    reason: str = Field(..., description="Reason for current status")
    previous_status: Optional[FreshnessStatus] = Field(
        None, description="Immediate previous freshness status"
    )
    history: List[FreshnessAssessment] = Field(
        default_factory=list, description="Complete chronological list of freshness assessments"
    )


class FreshnessCalculationRequest(BaseModel):
    """API request payload to calculate freshness."""

    company: str = Field(..., description="Company name")
    verification_cycle: Optional[str] = Field(
        None, description="Verification cycle (defaults to current YYYY-MM)"
    )
    financial_year: Optional[str] = Field(
        None, description="Target financial year being assessed (e.g. '2024-25')"
    )
    is_current_reporting_cycle: bool = Field(
        True, description="Whether the assessed document represents the current active reporting cycle"
    )
    wash_direction: Optional[WASHDirection] = Field(
        None, description="WASH direction from Task 9 verification"
    )
    has_wash_evidence: bool = Field(
        True, description="Whether verified evidence contains active WASH initiatives"
    )
    retrieved_at: Optional[str] = Field(
        None, description="ISO timestamp when document was retrieved"
    )
    verified_at: Optional[str] = Field(
        None, description="ISO timestamp when document was verified"
    )
    primary_document: Optional[Dict[str, Any]] = Field(
        None, description="Metadata dictionary for the primary evaluated document"
    )
    sources: List[SourceFreshnessRecord] = Field(
        default_factory=list, description="List of source disclosures available for this company"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references from Task 9"
    )

