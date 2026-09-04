"""
Document Metadata Normalization Service.
Validates, standardizes, and enriches document metadata according to the normalized document contract.
"""

from typing import Any, Dict, Optional
from mcp_server.contracts.document_contract import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    create_error_document,
    create_normalized_document,
)


def get_document_metadata(
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    source: Optional[str] = None,
    financial_year: Optional[str] = None,
    title: Optional[str] = None,
    url: Optional[str] = None,
    published_date: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    not_found_reason: Optional[str] = None,
    raw_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Normalizes and validates document metadata for downstream systems.
    Accepts individual fields or raw_metadata dictionary.
    """
    data: Dict[str, Any] = {}
    if raw_metadata and isinstance(raw_metadata, dict):
        data.update(raw_metadata)

    c_name = company_name or data.get("company_name")
    d_type = document_type or data.get("document_type")
    src = source or data.get("source")
    fy = financial_year or data.get("financial_year")
    tit = title or data.get("title")
    doc_url = url or data.get("url")
    pub_date = published_date or data.get("published_date")
    stat = status or data.get("status")
    err_msg = error_message or data.get("error_message")
    nf_reason = not_found_reason or data.get("not_found_reason")

    if not c_name or not str(c_name).strip():
        return create_error_document(
            company_name="UNKNOWN",
            document_type=DocumentType.ANNUAL_REPORT.value,
            source=DocumentSource.COMPANY.value,
            error_message="company_name is required in document metadata",
        )

    # Normalize document_type
    valid_types = [t.value for t in DocumentType]
    norm_type = str(d_type).lower() if d_type else None
    if norm_type not in valid_types:
        if norm_type and ("annual" in norm_type or "ar" in norm_type):
            norm_type = DocumentType.ANNUAL_REPORT.value
        elif norm_type and ("policy" in norm_type or "csr" in norm_type):
            norm_type = DocumentType.CSR_POLICY.value
        elif norm_type and ("brsr" in norm_type or "sustainability" in norm_type):
            norm_type = DocumentType.BRSR.value
        elif norm_type and ("disclosure" in norm_type or "announcement" in norm_type):
            norm_type = DocumentType.DISCLOSURE.value
        else:
            return create_error_document(
                company_name=c_name,
                document_type=DocumentType.ANNUAL_REPORT.value,
                source=src or DocumentSource.COMPANY.value,
                error_message=f"Invalid document_type '{d_type}'. Must be one of: {', '.join(valid_types)}",
            )

    # Normalize source
    valid_sources = [s.value for s in DocumentSource]
    norm_source = str(src).upper() if src else None
    if norm_source not in valid_sources:
        if norm_source and "NSE" in norm_source:
            norm_source = DocumentSource.NSE.value
        elif norm_source and "BSE" in norm_source:
            norm_source = DocumentSource.BSE.value
        else:
            norm_source = DocumentSource.COMPANY.value

    # Determine / validate status
    valid_statuses = [st.value for st in DocumentStatus]
    norm_status = str(stat).upper() if stat else None
    if norm_status not in valid_statuses:
        if doc_url:
            norm_status = DocumentStatus.FOUND.value
        elif err_msg:
            norm_status = DocumentStatus.ERROR.value
        else:
            norm_status = DocumentStatus.NOT_FOUND.value

    return create_normalized_document(
        company_name=c_name,
        document_type=norm_type,
        source=norm_source,
        status=norm_status,
        financial_year=fy,
        title=tit,
        url=doc_url,
        published_date=pub_date,
        error_message=err_msg,
        not_found_reason=nf_reason,
    )
