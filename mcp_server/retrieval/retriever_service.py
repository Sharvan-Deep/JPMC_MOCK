"""
Document Retrieval Service for Task 2.
Coordinates MCP tool metadata -> download -> validation -> hashing -> versioning -> persistence.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from mcp_server.retrieval.document_validator import validate_pdf_content
from mcp_server.retrieval.downloader import download_document_bytes
from mcp_server.retrieval.file_storage import save_document_file
from mcp_server.retrieval.hasher import compute_sha256
from mcp_server.retrieval.version_manager import VersionManager


class DocumentRetrieverService:
    """
    Main orchestration service for retrieving, validating, hashing,
    and versioning documents discovered via MCP.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        index_path: Optional[Path] = None,
        session: Optional[requests.Session] = None,
    ):
        self.base_dir = Path(base_dir) if base_dir else Path("data") / "documents"
        self.version_manager = VersionManager(
            index_path=index_path or (self.base_dir / "metadata.json")
        )
        self.session = session

    def process_document_retrieval(
        self,
        doc_contract: Dict[str, Any],
        custom_content: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Processes a single normalized document object through the full retrieval pipeline:
        1. Checks input contract status.
        2. Downloads content if URL is present (or uses custom_content for mocks/fixtures).
        3. Validates PDF magic header and rejects HTML/corrupt responses.
        4. Calculates SHA-256 hash.
        5. Handles versioning (skip duplicate vs create incremented version).
        6. Persists file and metadata record.

        Returns:
            Dict containing retrieval action, document record, and execution details.
        """
        company_name = doc_contract.get("company_name", "UNKNOWN").strip()
        doc_type = doc_contract.get("document_type", "disclosure").strip().lower()
        financial_year = doc_contract.get("financial_year")
        source = doc_contract.get("source", "UNKNOWN")
        url = doc_contract.get("url")
        title = doc_contract.get("title")
        published_date = doc_contract.get("published_date")
        meta = doc_contract.get("metadata") or {}
        company_id = meta.get("symbol") or meta.get("bse_scrip")

        # Handle existing NOT_FOUND status from MCP discovery
        if doc_contract.get("status") == "NOT_FOUND":
            record = self.version_manager.record_document(
                company_name=company_name,
                document_type=doc_type,
                source=source,
                source_url=url,
                financial_year=financial_year,
                title=title,
                status="NOT_FOUND",
                error_information=doc_contract.get("not_found_reason") or "Document not found at source",
                company_identifier=company_id,
            )
            return {"action": "NOT_FOUND_RECORDED", "status": "NOT_FOUND", "record": record}

        # Handle existing ERROR status from MCP discovery
        if doc_contract.get("status") == "ERROR":
            record = self.version_manager.record_document(
                company_name=company_name,
                document_type=doc_type,
                source=source,
                source_url=url,
                financial_year=financial_year,
                title=title,
                status="ERROR",
                error_information=doc_contract.get("error_message") or "Source retrieval error",
                company_identifier=company_id,
            )
            return {"action": "ERROR_RECORDED", "status": "ERROR", "record": record}

        # Download or use provided content
        if custom_content is not None:
            status = "FOUND"
            content = custom_content
            content_type = "application/pdf"
            err_msg = None
        else:
            if not url:
                record = self.version_manager.record_document(
                    company_name=company_name,
                    document_type=doc_type,
                    source=source,
                    financial_year=financial_year,
                    title=title,
                    status="ERROR",
                    error_information="Document status was FOUND but no URL was provided",
                    company_identifier=company_id,
                )
                return {"action": "ERROR_RECORDED", "status": "ERROR", "record": record}

            status, content, content_type, err_msg = download_document_bytes(
                url=url,
                session=self.session,
            )

        if status == "NOT_FOUND":
            record = self.version_manager.record_document(
                company_name=company_name,
                document_type=doc_type,
                source=source,
                source_url=url,
                financial_year=financial_year,
                title=title,
                status="NOT_FOUND",
                error_information=err_msg or "HTTP 404: Document not found",
                company_identifier=company_id,
            )
            return {"action": "NOT_FOUND_RECORDED", "status": "NOT_FOUND", "record": record}

        if status == "ERROR" or content is None:
            record = self.version_manager.record_document(
                company_name=company_name,
                document_type=doc_type,
                source=source,
                source_url=url,
                financial_year=financial_year,
                title=title,
                status="ERROR",
                error_information=err_msg or "Failed to download document content",
                company_identifier=company_id,
            )
            return {"action": "ERROR_RECORDED", "status": "ERROR", "record": record}

        # Step 3: Validate binary content
        is_valid, val_err = validate_pdf_content(content, content_type=content_type)
        if not is_valid:
            record = self.version_manager.record_document(
                company_name=company_name,
                document_type=doc_type,
                source=source,
                source_url=url,
                financial_year=financial_year,
                title=title,
                content_type=content_type,
                file_size=len(content),
                status="ERROR",
                error_information=f"Validation failed: {val_err}",
                company_identifier=company_id,
            )
            return {"action": "VALIDATION_FAILED", "status": "ERROR", "record": record}

        # Step 4: Compute SHA-256 hash
        sha256_hash = compute_sha256(content)

        # Step 5: Versioning evaluation
        action, ver_to_use, existing_rec = self.version_manager.evaluate_version(
            company_name=company_name,
            document_type=doc_type,
            financial_year=financial_year,
            sha256_hash=sha256_hash,
        )

        if action == "DUPLICATE_SKIPPED" and existing_rec:
            updated_rec = self.version_manager.touch_duplicate_record(existing_rec)
            return {
                "action": "DUPLICATE_SKIPPED",
                "status": "FOUND",
                "version": updated_rec.get("version"),
                "sha256": sha256_hash,
                "record": updated_rec,
            }

        # Step 6: Save document file
        saved_path = save_document_file(
            content=content,
            company_name=company_name,
            document_type=doc_type,
            financial_year=financial_year,
            version=ver_to_use,
            sha256_hash=sha256_hash,
            base_dir=self.base_dir,
        )

        # Step 7: Record metadata
        record = self.version_manager.record_document(
            company_name=company_name,
            document_type=doc_type,
            source=source,
            source_url=url,
            financial_year=financial_year,
            title=title,
            local_file_path=str(saved_path),
            file_name=saved_path.name,
            file_size=len(content),
            content_type="application/pdf",
            sha256_hash=sha256_hash,
            version=ver_to_use,
            is_latest=True,
            published_date=published_date,
            status="FOUND",
            company_identifier=company_id,
        )

        return {
            "action": action,
            "status": "FOUND",
            "version": ver_to_use,
            "sha256": sha256_hash,
            "local_file_path": str(saved_path),
            "record": record,
        }
