"""
Pydantic Schemas for Task 9: CSR Verification & Change Detection.

Defines contracts for comparing CSR information from different document versions
and financial years across 7 dimensions:
1. WASH Focus
2. Projects
3. Spending
4. Geography
5. Beneficiaries
6. Commitments
7. CSR Policy / Strategic Focus

Preserves historical and current states with complete evidence traceability.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChangeCategory(str, Enum):
    """Standardized change classification categories."""

    UNCHANGED = "UNCHANGED"
    INCREASED = "INCREASED"
    DECREASED = "DECREASED"
    NEW = "NEW"
    DISCONTINUED = "DISCONTINUED"
    EXPANDED = "EXPANDED"
    CONTRACTED = "CONTRACTED"
    CONTINUED = "CONTINUED"
    CHANGED_DIRECTION = "CHANGED_DIRECTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class WASHDirection(str, Enum):
    """Overall strategic WASH direction across compared periods."""

    INCREASED = "INCREASED"
    STABLE = "STABLE"
    DECREASED = "DECREASED"
    NEW_FOCUS = "NEW_FOCUS"
    LOST_FOCUS = "LOST_FOCUS"
    MIXED = "MIXED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class VerificationConfidence(str, Enum):
    """Confidence score for semantic conclusions."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CSREvidenceReference(BaseModel):
    """Traceable evidence reference anchoring detected changes to source documents."""

    company: Optional[str] = Field(None, description="Company name")
    financial_year: Optional[str] = Field(None, description="Financial year (e.g. 2023-24)")
    document_type: Optional[str] = Field(None, description="Document type (e.g. CSR_REPORT)")
    document_version: Optional[int] = Field(None, description="Document version number")
    page: Optional[int] = Field(None, description="1-indexed source PDF page")
    source_url: Optional[str] = Field(None, description="Document retrieval source URL")
    relevant_source_text: Optional[str] = Field(None, description="Verbatim source excerpt")
    document_hash: Optional[str] = Field(None, description="SHA-256 hash of source document")


class CSRProjectSnapshot(BaseModel):
    """Snapshot of an individual CSR project within a document/year."""

    project_id: Optional[str] = Field(None, description="Unique project identifier if available")
    project_name: str = Field(..., description="Project name/title")
    description: Optional[str] = Field(None, description="Project narrative description")
    sector: Optional[str] = Field(None, description="CSR sector / category")
    is_wash: bool = Field(False, description="Whether project relates to WASH")
    wash_subcategories: List[str] = Field(
        default_factory=list, description="Subcategories like drinking_water, sanitation, hygiene"
    )
    budget_inr_crore: Optional[float] = Field(None, description="Budget/outlay in ₹ Crores")
    amount_spent_inr_crore: Optional[float] = Field(
        None, description="Actual expenditure in ₹ Crores"
    )
    state: Optional[str] = Field(None, description="State location")
    district: Optional[str] = Field(None, description="District location")
    is_multi_year: bool = Field(False, description="Whether project is multi-year/ongoing")
    duration_years: Optional[int] = Field(None, description="Project duration in years")
    beneficiaries_target: Optional[str] = Field(None, description="Target beneficiary group")
    page_number: Optional[int] = Field(None, description="Page number of record in source document")


class CSRDocumentProfile(BaseModel):
    """Structured CSR profile representing a single document version or financial year."""

    company: str = Field(..., description="Company name")
    financial_year: Optional[str] = Field(None, description="Financial year (e.g. '2023-24')")
    document_version: Optional[int] = Field(1, description="Document version number (e.g. 1, 2)")
    document_type: Optional[str] = Field("CSR_REPORT", description="Type of document")
    source_url: Optional[str] = Field(None, description="Source URL")
    document_hash: Optional[str] = Field(None, description="SHA-256 hash")

    # Financials
    total_csr_spend_crore: Optional[float] = Field(
        None, description="Total CSR expenditure in ₹ Crores"
    )
    wash_spend_crore: Optional[float] = Field(
        None, description="Total WASH expenditure in ₹ Crores"
    )
    water_spend_crore: Optional[float] = Field(
        None, description="Drinking water expenditure in ₹ Crores"
    )
    sanitation_spend_crore: Optional[float] = Field(
        None, description="Sanitation expenditure in ₹ Crores"
    )

    # Focus & Activities
    wash_focus_areas: List[str] = Field(
        default_factory=list,
        description="Active WASH subcategories (e.g. drinking_water, sanitation, hygiene, water_access)",
    )
    has_wash_activity: Optional[bool] = Field(
        None, description="Explicit flag if WASH activity was detected"
    )

    # Projects & Geography
    projects: List[CSRProjectSnapshot] = Field(
        default_factory=list, description="List of individual CSR projects"
    )
    states: List[str] = Field(default_factory=list, description="List of operating states")
    districts: List[str] = Field(default_factory=list, description="List of operating districts")
    cities: List[str] = Field(default_factory=list, description="List of operating cities")

    # Beneficiaries
    beneficiary_groups: List[str] = Field(
        default_factory=list, description="Target beneficiary demographics"
    )
    beneficiary_count: Optional[int] = Field(
        None, description="Total reported beneficiary count (unestimated)"
    )
    target_communities: List[str] = Field(
        default_factory=list, description="Target communities or regions"
    )

    # Commitments
    multi_year_commitments: List[str] = Field(
        default_factory=list, description="Active multi-year commitments"
    )
    ongoing_projects: List[str] = Field(
        default_factory=list, description="Ongoing project identifiers/names"
    )
    recurring_programs: List[str] = Field(
        default_factory=list, description="Recurring annual programs"
    )
    stated_future_plans: List[str] = Field(
        default_factory=list, description="Explicit future outlook statements"
    )

    # Policy
    policy_priorities: List[str] = Field(
        default_factory=list, description="Strategic CSR priorities stated in policy"
    )
    raw_evidence_pages: Dict[str, int] = Field(
        default_factory=dict, description="Mapping of key terms to page numbers"
    )


class SpendingComparisonItem(BaseModel):
    """Deterministic comparison item for a specific expenditure category."""

    metric: str = Field(..., description="Expenditure metric name")
    previous_value: Optional[float] = Field(None, description="Previous value in INR Crores")
    current_value: Optional[float] = Field(None, description="Current value in INR Crores")
    absolute_change: Optional[float] = Field(
        None, description="current_value - previous_value in INR Crores"
    )
    percentage_change: Optional[float] = Field(
        None, description="Percentage change ((current - prev) / prev) * 100"
    )
    unit: str = Field("INR Crores", description="Unit of measurement")
    change_type: ChangeCategory = Field(..., description="Change classification category")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class SpendingComparison(BaseModel):
    """Spending comparison across overall CSR and WASH categories."""

    metrics: List[SpendingComparisonItem] = Field(
        default_factory=list, description="Core financial metrics"
    )
    project_spending_changes: List[SpendingComparisonItem] = Field(
        default_factory=list, description="Project-level budget/expenditure changes"
    )
    overall_change_type: ChangeCategory = Field(
        ChangeCategory.UNCHANGED, description="Overall spending direction"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Associated evidence"
    )


class WASHFocusComparison(BaseModel):
    """WASH strategic focus area comparison."""

    previous_focus: List[str] = Field(
        default_factory=list, description="WASH focus areas in previous document"
    )
    current_focus: List[str] = Field(
        default_factory=list, description="WASH focus areas in current document"
    )
    added_focus: List[str] = Field(default_factory=list, description="Newly introduced focus areas")
    removed_focus: List[str] = Field(default_factory=list, description="Discontinued focus areas")
    retained_focus: List[str] = Field(default_factory=list, description="Continued focus areas")
    direction: WASHDirection = Field(..., description="Direction of WASH focus")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class ProjectSemanticMatch(BaseModel):
    """Semantic match between differently named projects describing similar activity."""

    previous_project: str = Field(..., description="Previous project name")
    current_project: str = Field(..., description="Current project name")
    similarity_score: float = Field(..., description="Semantic similarity score (0.0 - 1.0)")
    rationale: str = Field(..., description="Explanation of semantic equivalence")


class ProjectComparison(BaseModel):
    """Project-level comparison including new, discontinued, and continuing programs."""

    new_projects: List[str] = Field(
        default_factory=list, description="Newly introduced project names"
    )
    discontinued_projects: List[str] = Field(
        default_factory=list, description="Discontinued project names"
    )
    continuing_projects: List[str] = Field(
        default_factory=list, description="Projects continuing from previous period"
    )
    multi_year_projects: List[str] = Field(
        default_factory=list, description="Continuing multi-year programs"
    )
    semantic_matches: List[ProjectSemanticMatch] = Field(
        default_factory=list, description="Projects linked via semantic similarity"
    )
    change_type: ChangeCategory = Field(..., description="Overall project change category")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class GeographyComparison(BaseModel):
    """Geographic footprint expansion or contraction comparison."""

    new_locations: List[str] = Field(default_factory=list, description="Newly added states/regions")
    removed_locations: List[str] = Field(
        default_factory=list, description="States/regions no longer active"
    )
    continuing_locations: List[str] = Field(
        default_factory=list, description="Consistently active states/regions"
    )
    new_districts: List[str] = Field(default_factory=list, description="Newly added districts")
    removed_districts: List[str] = Field(
        default_factory=list, description="Districts no longer active"
    )
    direction: ChangeCategory = Field(
        ..., description="EXPANDED, CONTRACTED, UNCHANGED, or INSUFFICIENT_EVIDENCE"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class BeneficiaryComparison(BaseModel):
    """Beneficiary group and count comparison (without estimation)."""

    previous_groups: List[str] = Field(default_factory=list, description="Previous target groups")
    current_groups: List[str] = Field(default_factory=list, description="Current target groups")
    new_groups: List[str] = Field(default_factory=list, description="Newly targeted groups")
    removed_groups: List[str] = Field(default_factory=list, description="Discontinued target groups")
    previous_count: Optional[int] = Field(
        None, description="Previous unestimated beneficiary count"
    )
    current_count: Optional[int] = Field(None, description="Current unestimated beneficiary count")
    count_absolute_change: Optional[int] = Field(
        None, description="Numeric difference in beneficiaries"
    )
    count_percentage_change: Optional[float] = Field(
        None, description="Percentage change in beneficiary reach"
    )
    target_communities_change: Optional[str] = Field(
        None, description="Narrative summary of community changes"
    )
    change_type: ChangeCategory = Field(..., description="Beneficiary reach change category")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class CommitmentComparison(BaseModel):
    """Commitments and multi-year program continuation comparison."""

    continued_commitments: List[str] = Field(
        default_factory=list, description="Ongoing multi-year commitments"
    )
    new_commitments: List[str] = Field(
        default_factory=list, description="Newly initiated multi-year commitments"
    )
    completed_commitments: List[str] = Field(
        default_factory=list, description="Completed commitments"
    )
    ongoing_projects: List[str] = Field(
        default_factory=list, description="List of active ongoing projects"
    )
    recurring_programs: List[str] = Field(
        default_factory=list, description="Consistently recurring programs"
    )
    stated_future_plans: List[str] = Field(
        default_factory=list, description="Stated future outlook commitments"
    )
    change_type: ChangeCategory = Field(..., description="Commitments change category")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class PolicyComparison(BaseModel):
    """CSR policy and strategic priority shifts."""

    added_priorities: List[str] = Field(
        default_factory=list, description="Newly added strategic priorities"
    )
    removed_priorities: List[str] = Field(
        default_factory=list, description="De-prioritized or removed focus areas"
    )
    strengthened_priorities: List[str] = Field(
        default_factory=list, description="Priorities with increased emphasis"
    )
    reduced_priorities: List[str] = Field(
        default_factory=list, description="Priorities with reduced emphasis"
    )
    unchanged_priorities: List[str] = Field(
        default_factory=list, description="Consistently maintained priorities"
    )
    wash_priority_status: str = Field(
        ..., description="Summary status of WASH in corporate policy"
    )
    change_type: ChangeCategory = Field(..., description="Policy change category")
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Evidence references"
    )


class CSRChangeItem(BaseModel):
    """Granular structured change item across any dimension."""

    dimension: str = Field(..., description="Dimension name (e.g. 'spending', 'wash_focus', 'projects')")
    change_type: ChangeCategory = Field(..., description="Change classification category")
    description: str = Field(..., description="Human-readable description of detected change")
    previous_value: Optional[Any] = Field(None, description="Previous state or value")
    current_value: Optional[Any] = Field(None, description="Current state or value")
    absolute_change: Optional[float] = Field(None, description="Absolute numeric delta if applicable")
    percentage_change: Optional[float] = Field(
        None, description="Percentage change if applicable"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Anchoring evidence references"
    )


class CSRDimensionsComparison(BaseModel):
    """Container holding comparison results across all 7 dimensions."""

    wash_focus: WASHFocusComparison
    projects: ProjectComparison
    spending: SpendingComparison
    geography: GeographyComparison
    beneficiaries: BeneficiaryComparison
    commitments: CommitmentComparison
    csr_policy: PolicyComparison


class DocumentSummaryHeader(BaseModel):
    """High-level header summarizing compared document snapshot."""

    company: str
    financial_year: Optional[str] = None
    document_version: Optional[int] = 1
    document_type: Optional[str] = "CSR_REPORT"
    document_hash: Optional[str] = None


class CSRChangeDetectionResult(BaseModel):
    """Comprehensive comparison output preserving both historical and current states."""

    company: str = Field(..., description="Company name")
    previous_document: Optional[DocumentSummaryHeader] = Field(
        None, description="Previous document metadata"
    )
    current_document: Optional[DocumentSummaryHeader] = Field(
        None, description="Current document metadata"
    )
    comparison_period: str = Field(
        ..., description="Comparison label (e.g. 'FY 2023-24 -> FY 2024-25' or 'v1 -> v2')"
    )
    dimensions: CSRDimensionsComparison = Field(
        ..., description="Comparison across all 7 dimensions"
    )
    overall_wash_direction: WASHDirection = Field(
        ..., description="Synthesized overall WASH direction"
    )
    changes: List[CSRChangeItem] = Field(
        default_factory=list, description="Flat list of all detected change items"
    )
    evidence: List[CSREvidenceReference] = Field(
        default_factory=list, description="Aggregated evidence references"
    )
    confidence: VerificationConfidence = Field(
        VerificationConfidence.HIGH, description="Confidence level of findings"
    )
    verification_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata regarding verification execution"
    )


class CSRChangeDetectionRequest(BaseModel):
    """Request payload for change detection API."""

    previous_profile: Optional[CSRDocumentProfile] = Field(
        None, description="CSR profile for previous period/version"
    )
    current_profile: Optional[CSRDocumentProfile] = Field(
        None, description="CSR profile for current period/version"
    )
    query_chromadb_if_needed: bool = Field(
        True, description="Whether to query ChromaDB for supplemental evidence"
    )
