"""
Pydantic Schemas for Task 5: CSR Data Preprocessing & Cleaning.
Defines contracts for cleaned text, normalized entities (amounts in Crores,
canonical company names, standardized FY), and cleaned table records.
Maintains full traceability to original raw values and page numbers.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai_service.schemas.extraction import CSRProjectRaw, CSRTableRaw


class CleanedCSRRecord(BaseModel):
    """Cleaned CSR project record linked directly to its raw extracted source."""

    raw_project: Optional[CSRProjectRaw] = Field(
        None, description="Verbatim raw project record extracted in Task 4"
    )
    project_name: Optional[str] = Field(None, description="Cleaned project title")
    category: Optional[str] = Field(
        None, description="Cleaned CSR sector / Schedule VII activity category"
    )
    location: Optional[str] = Field(
        None, description="Cleaned project location (State / District / Area)"
    )
    raw_amount_spent: Optional[str] = Field(
        None, description="Verbatim original amount spent string"
    )
    normalized_amount_spent_crore: Optional[float] = Field(
        None, description="Unambiguously normalized expenditure in INR Crores (₹ Cr)"
    )
    raw_amount_allocated: Optional[str] = Field(
        None, description="Verbatim original outlay string"
    )
    normalized_amount_allocated_crore: Optional[float] = Field(
        None, description="Unambiguously normalized outlay/budget in INR Crores (₹ Cr)"
    )
    beneficiaries: Optional[str] = Field(
        None, description="Cleaned target beneficiaries or population reach"
    )
    implementation_mode: Optional[str] = Field(
        None, description="Direct or through implementing agency"
    )
    page_number: Optional[int] = Field(
        None, description="1-indexed PDF page where record was extracted"
    )
    is_extraction_duplicate: bool = Field(
        False, description="Flag indicating if this record was an extraction duplicate"
    )


class CleanedCSRData(BaseModel):
    """Top-level structured entities cleaned and normalized in Task 5."""

    canonical_company_name: Optional[str] = Field(
        None, description="Standardized canonical company name"
    )
    raw_company_name: Optional[str] = Field(
        None, description="Verbatim company name from Task 4"
    )
    normalized_financial_year: Optional[str] = Field(
        None, description="Normalized financial year (e.g. '2023-24')"
    )
    raw_financial_year: Optional[str] = Field(
        None, description="Verbatim financial year string"
    )
    raw_total_csr_amount: Optional[str] = Field(
        None, description="Verbatim total CSR expenditure string"
    )
    normalized_total_csr_amount_crore: Optional[float] = Field(
        None, description="Normalized total CSR expenditure in INR Crores (₹ Cr)"
    )
    records: List[CleanedCSRRecord] = Field(
        default_factory=list, description="Cleaned and deduplicated CSR records"
    )
    other_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Additional cleaned metadata"
    )


class PreprocessingMetadata(BaseModel):
    """Diagnostic and processing metrics for Task 5."""

    raw_pages: int = Field(0, description="Total raw pages received")
    processed_pages: int = Field(0, description="Pages successfully cleaned")
    raw_records_count: int = Field(0, description="Raw projects received from Task 4")
    cleaned_records_count: int = Field(0, description="Cleaned projects retained")
    duplicates_removed: int = Field(0, description="Extraction duplicates filtered")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal data warnings")
    processing_time_seconds: float = Field(0.0, description="Duration of preprocessing run")


class CSRPreprocessingResult(BaseModel):
    """Structured output contract for Task 5: Preprocessing & Cleaning."""

    status: str = Field(
        ...,
        description="Preprocessing status: SUCCESS, PARTIAL_SUCCESS, or FAILED",
    )
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata preserved from Task 4"
    )
    cleaned_data: CleanedCSRData = Field(
        default_factory=CleanedCSRData,
        description="Cleaned and normalized CSR entities",
    )
    cleaned_text_by_page: Dict[int, str] = Field(
        default_factory=dict,
        description="Page-by-page cleaned text preserving structure and boundaries",
    )
    cleaned_tables: List[CSRTableRaw] = Field(
        default_factory=list,
        description="Cleaned tables with empty rows/columns pruned and cell whitespace normalized",
    )
    metadata: PreprocessingMetadata = Field(
        default_factory=PreprocessingMetadata, description="Preprocessing metrics"
    )
    errors: List[str] = Field(
        default_factory=list, description="Error messages if preprocessing encountered issues"
    )
