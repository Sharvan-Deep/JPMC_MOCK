"""Contracts package."""
from mcp_server.contracts.document_contract import (
    DocumentType,
    DocumentSource,
    DocumentStatus,
    NormalizedDocument,
    create_normalized_document,
    create_not_found_document,
    create_error_document,
)

__all__ = [
    "DocumentType",
    "DocumentSource",
    "DocumentStatus",
    "NormalizedDocument",
    "create_normalized_document",
    "create_not_found_document",
    "create_error_document",
]
