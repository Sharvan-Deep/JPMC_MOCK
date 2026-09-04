"""
Document input and response schemas for AI/Data Service.
Ensures strong typing and validation for metadata generated in Task 2.
"""

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentTypeEnum(str, Enum):
    ANNUAL_REPORT = "annual_report"
    CSR_POLICY = "csr_policy"
    BRSR = "brsr"
    DISCLOSURE = "disclosure"


class DocumentStatusEnum(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


# Valid financial year regex: FY2023-24, 2023-24, FY23-24, 2024, general
FY_PATTERN = re.compile(r"^(FY)?(\d{4}|\d{2})(-\d{2,4})?$|^general$", re.IGNORECASE)

# Valid SHA-256 regex: exactly 64 hexadecimal characters
SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class DocumentInputSchema(BaseModel):
    """
    Validated document input contract for AI/Data Service.
    Directly consumes metadata produced by Task 2 document retrieval.
    """

    company_name: str = Field(min_length=1, max_length=500, description="Legal or registered company name")
    company_identifier: Optional[str] = Field(default=None, max_length=100, description="Exchange symbol, BSE scrip, or CIN")
    document_type: str = Field(description="Document category: annual_report, csr_policy, brsr, disclosure")
    financial_year: Optional[str] = Field(default=None, max_length=50, description="Target financial year (e.g. 2023-24)")
    title: Optional[str] = Field(default=None, max_length=1000, description="Document title or disclosure subject")
    source: str = Field(min_length=1, max_length=100, description="Retrieval source: NSE, BSE, COMPANY")
    source_url: Optional[str] = Field(default=None, max_length=2048, description="Public source URL")
    local_file_path: Optional[str] = Field(default=None, max_length=1024, description="Local path to stored PDF")
    file_name: Optional[str] = Field(default=None, max_length=500, description="Filename of stored document")
    file_size: Optional[int] = Field(default=None, ge=0, description="Size in bytes")
    content_type: Optional[str] = Field(default=None, max_length=100, description="MIME content type")
    sha256: Optional[str] = Field(default=None, description="64-character SHA-256 hex digest")
    version: int = Field(default=1, ge=1, description="Document revision version integer")
    is_latest: bool = Field(default=True, description="True if this is the most current version")
    published_date: Optional[str] = Field(default=None, description="Date document was published by source")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of retrieval",
    )
    last_verified_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp of last verification")
    status: str = Field(default=DocumentStatusEnum.FOUND.value, description="Status: FOUND, NOT_FOUND, ERROR")
    error_information: Optional[str] = Field(default=None, description="Error detail if status is ERROR or NOT_FOUND")

    model_config = ConfigDict(extra="ignore")

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        clean = v.strip().lower()
        valid_types = [t.value for t in DocumentTypeEnum]
        if clean not in valid_types:
            raise ValueError(
                f"Unsupported document_type '{v}'. Must be one of: {', '.join(valid_types)}"
            )
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.strip().upper()
        valid_statuses = [s.value for s in DocumentStatusEnum]
        if clean not in valid_statuses:
            raise ValueError(
                f"Unsupported status '{v}'. Must be one of: {', '.join(valid_statuses)}"
            )
        return clean

    @field_validator("financial_year")
    @classmethod
    def validate_financial_year(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        clean = v.strip()
        if not FY_PATTERN.match(clean):
            raise ValueError(
                f"Invalid financial_year format '{v}'. Expected format like '2023-24', 'FY2023-24', or 'general'"
            )
        return clean

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        clean = v.strip().lower()
        if not SHA256_PATTERN.match(clean):
            raise ValueError(
                f"Invalid SHA-256 format. Expected 64 hexadecimal characters, received '{v}'"
            )
        return clean


class DocumentValidationResponse(BaseModel):
    """Response returned when validating a document metadata contract."""

    valid: bool = Field(description="True if document contract and schema are fully valid")
    message: str = Field(description="Summary validation result")
    company_name: str
    document_type: str
    financial_year: Optional[str] = None
    sha256: Optional[str] = None
    version: int
    file_exists_locally: Optional[bool] = Field(
        default=None, description="True if local_file_path points to an existing file on disk"
    )
