"""
Pydantic Schemas for Task 4: CSR Data Extraction.
Defines contracts for extracted raw text, raw tables, identified CSR fields,
and extraction metadata. Preserves raw verbatim data without cleaning/normalization.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CSRProjectRaw(BaseModel):
    """Raw, uncleaned CSR project/program record extracted from text or tables."""

    project_name: Optional[str] = Field(None, description="Raw CSR project/program title")
    category: Optional[str] = Field(
        None, description="Raw CSR sector / Schedule VII activity category"
    )
    location: Optional[str] = Field(
        None, description="Raw project location (State, District, or Local Area)"
    )
    amount_spent: Optional[str] = Field(
        None, description="Verbatim raw amount spent (e.g., '12.50 Cr', 'Rs. 250 Lakhs')"
    )
    amount_allocated: Optional[str] = Field(
        None, description="Verbatim raw amount outlay/budget allocated"
    )
    beneficiaries: Optional[str] = Field(
        None, description="Raw targeted beneficiaries or impact count"
    )
    implementation_mode: Optional[str] = Field(
        None, description="Direct or through implementing agency"
    )
    page_number: Optional[int] = Field(
        None, description="1-indexed PDF page where project was identified"
    )
    raw_row_data: Optional[Dict[str, Optional[str]]] = Field(
        default=None, description="Verbatim table row key-value mapping if from a table"
    )


class CSRTableRaw(BaseModel):
    """Raw extracted table data preserving row/column relationships."""

    page_number: int = Field(..., description="1-indexed PDF page containing the table")
    table_index: int = Field(0, description="0-indexed table sequence on the page")
    headers: List[str] = Field(default_factory=list, description="Extracted header column names")
    rows: List[List[Optional[str]]] = Field(
        default_factory=list, description="Preserved matrix of raw cell values"
    )


class IdentifiedCSRData(BaseModel):
    """Structured CSR entities identified in the document (raw strings preserved)."""

    donor_name: Optional[str] = Field(None, description="Company / Donor entity name")
    financial_year: Optional[str] = Field(
        None, description="Reporting financial year (e.g. FY 2023-24)"
    )
    total_csr_amount: Optional[str] = Field(
        None, description="Verbatim total CSR expenditure or obligation figure"
    )
    csr_committee_members: Optional[List[str]] = Field(
        default=None, description="CSR committee member names if reported"
    )
    projects: List[CSRProjectRaw] = Field(
        default_factory=list, description="List of identified CSR projects/programs"
    )
    other_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Additional raw CSR fields identified"
    )


class ExtractionMetadata(BaseModel):
    """Technical and diagnostic metadata about the extraction run."""

    total_pages: int = Field(0, description="Total pages in the PDF")
    pages_with_text: int = Field(0, description="Count of pages yielding extractable text")
    pages_with_tables: int = Field(0, description="Count of pages containing extracted tables")
    total_tables: int = Field(0, description="Total tables extracted")
    ocr_required: bool = Field(
        False, description="Flag set to True if scanned/image-based pages require OCR"
    )
    ocr_pages: List[int] = Field(
        default_factory=list, description="1-indexed list of pages requiring OCR"
    )
    extraction_time_seconds: float = Field(0.0, description="Total execution duration in seconds")


class CSRExtractionResult(BaseModel):
    """Top-level structured result returned by Task 4 Data Extraction."""

    status: str = Field(
        ...,
        description="Execution status: SUCCESS, PARTIAL_SUCCESS, OCR_REQUIRED, or FAILED",
    )
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata of the source document"
    )
    ocr_required: bool = Field(
        False, description="Whether full or partial OCR is needed for complete data extraction"
    )
    ocr_details: Optional[str] = Field(
        None, description="Explanatory details if OCR is required"
    )
    identified_csr_data: IdentifiedCSRData = Field(
        default_factory=IdentifiedCSRData,
        description="Identified CSR entities with raw string representations",
    )
    raw_extracted_data: Dict[str, Any] = Field(
        default_factory=lambda: {"text_by_page": {}, "tables": []},
        description="Raw page-by-page text and table matrices preserved verbatim",
    )
    metadata: ExtractionMetadata = Field(
        default_factory=ExtractionMetadata, description="Extraction diagnostics and metrics"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of non-fatal warnings or fatal error messages"
    )
