"""
Normalized Document Contract for Jaldhaara Foundation
CSR Document MCP Server & Source Retrieval Foundation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    ANNUAL_REPORT = "annual_report"
    CSR_POLICY = "csr_policy"
    BRSR = "brsr"
    DISCLOSURE = "disclosure"


class DocumentSource(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    COMPANY = "COMPANY"


class DocumentStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class NormalizedDocument(BaseModel):
    """
    Standard contract for all document retrieval tools.
    Downstream systems (PDF processing, AI analysis) consume this contract.
    """
    company_name: str
    document_type: str
    financial_year: Optional[str] = None
    title: Optional[str] = None
    source: str
    url: Optional[str] = None
    published_date: Optional[str] = None
    retrieved_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str
    error_message: Optional[str] = None
    not_found_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def create_normalized_document(
    company_name: str,
    document_type: str,
    source: str,
    status: str = DocumentStatus.FOUND.value,
    financial_year: Optional[str] = None,
    title: Optional[str] = None,
    url: Optional[str] = None,
    published_date: Optional[str] = None,
    retrieved_date: Optional[str] = None,
    error_message: Optional[str] = None,
    not_found_reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Builds and validates a normalized document dictionary."""
    if not company_name or not company_name.strip():
        raise ValueError("company_name is required and cannot be empty")

    doc = NormalizedDocument(
        company_name=company_name.strip(),
        document_type=str(document_type),
        source=str(source),
        status=str(status),
        financial_year=financial_year.strip() if financial_year else None,
        title=title.strip() if title else None,
        url=url.strip() if url else None,
        published_date=published_date.strip() if published_date else None,
        retrieved_date=retrieved_date or datetime.now(timezone.utc).isoformat(),
        error_message=error_message.strip() if error_message else None,
        not_found_reason=not_found_reason.strip() if not_found_reason else None,
        metadata=metadata,
    )
    return doc.to_dict()


def create_not_found_document(
    company_name: str,
    document_type: str,
    source: str,
    financial_year: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to return a NOT_FOUND normalized document."""
    return create_normalized_document(
        company_name=company_name,
        document_type=document_type,
        source=source,
        status=DocumentStatus.NOT_FOUND.value,
        financial_year=financial_year,
        not_found_reason=reason or "Document not found at source",
    )


def create_error_document(
    company_name: str,
    document_type: str,
    source: str,
    error_message: str,
    financial_year: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to return an ERROR normalized document."""
    return create_normalized_document(
        company_name=company_name,
        document_type=document_type,
        source=source,
        status=DocumentStatus.ERROR.value,
        financial_year=financial_year,
        error_message=error_message or "An unexpected error occurred during retrieval",
    )
