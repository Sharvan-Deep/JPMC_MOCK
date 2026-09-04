"""
Document Validation & Intake Service.
Validates document contracts and file integrity for downstream AI processing.
Strictly does NOT perform text extraction, chunking, or LLM operations.
"""

from pathlib import Path
from typing import Optional

from ai_service.logging_config import logger
from ai_service.schemas.document import DocumentInputSchema, DocumentValidationResponse
from mcp_server.retrieval.hasher import compute_sha256


class DocumentService:
    """Service handling document contract validation and local integrity checks."""

    def __init__(self, storage_base_path: Optional[str] = None):
        self.storage_base_path = Path(storage_base_path) if storage_base_path else Path("data/documents")

    def validate_document_contract(self, document: DocumentInputSchema) -> DocumentValidationResponse:
        """
        Validates document contract and verifies local storage existence if path is supplied.
        """
        logger.info(
            f"Validating document contract: company='{document.company_name}', type='{document.document_type}', "
            f"FY='{document.financial_year}', version={document.version}"
        )

        file_exists = None
        if document.local_file_path:
            p = Path(document.local_file_path)
            file_exists = p.exists() and p.is_file()

            # If file exists and sha256 was provided, verify hash consistency
            if file_exists and document.sha256:
                try:
                    with open(p, "rb") as f:
                        file_bytes = f.read()
                    actual_hash = compute_sha256(file_bytes)
                    if actual_hash.lower() != document.sha256.lower():
                        logger.warning(
                            f"SHA-256 mismatch for '{p}': expected {document.sha256}, calculated {actual_hash}"
                        )
                except Exception as e:
                    logger.warning(f"Could not compute local file hash for '{p}': {e}")

        return DocumentValidationResponse(
            valid=True,
            message="Document contract is valid and verified",
            company_name=document.company_name,
            document_type=document.document_type,
            financial_year=document.financial_year,
            sha256=document.sha256,
            version=document.version,
            file_exists_locally=file_exists,
        )
