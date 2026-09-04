"""
CSR Data Extraction Orchestration Service for Task 4.
Integrates Task 3 validation and orchestrates low-level PDF extraction and CSR parsing.
Enforces the validation gate: extraction ONLY proceeds if document is valid.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ai_service.extraction.csr_parser import CSRParser
from ai_service.extraction.pdf_extractor import PDFExtractor
from ai_service.logging_config import logger
from ai_service.schemas.document import DocumentInputSchema
from ai_service.schemas.extraction import (
    CSRExtractionResult,
    ExtractionMetadata,
    IdentifiedCSRData,
)
from ai_service.services.document_service import DocumentService
from mcp_server.retrieval.document_validator import validate_pdf_content


class CSRExtractorService:
    """Orchestrator for validating and extracting CSR data from documents."""

    def __init__(
        self,
        document_service: Optional[DocumentService] = None,
        pdf_extractor: Optional[PDFExtractor] = None,
        csr_parser: Optional[CSRParser] = None,
    ):
        self.document_service = document_service or DocumentService()
        self.pdf_extractor = pdf_extractor or PDFExtractor()
        self.csr_parser = csr_parser or CSRParser()

    def extract_from_document(
        self,
        document: Union[DocumentInputSchema, Dict[str, Any]],
    ) -> CSRExtractionResult:
        """
        Validates the document contract (Task 3) and performs Task 4 CSR data extraction.

        Strictly enforces:
        1. Task 3 schema & contract validation.
        2. File existence on disk.
        3. Binary PDF format validation (starts with %PDF-, min bytes, not HTML/JSON).
        4. Structured extraction only on validated PDFs.
        """
        start_time = time.time()

        # Normalize to DocumentInputSchema
        if isinstance(document, dict):
            try:
                doc_obj = DocumentInputSchema(**document)
            except Exception as schema_err:
                logger.error(f"Document input schema validation failed: {schema_err}")
                return CSRExtractionResult(
                    status="FAILED",
                    document_metadata=document,
                    ocr_required=False,
                    identified_csr_data=IdentifiedCSRData(),
                    raw_extracted_data={"text_by_page": {}, "tables": []},
                    metadata=ExtractionMetadata(
                        extraction_time_seconds=round(time.time() - start_time, 4)
                    ),
                    errors=[f"Schema validation error: {str(schema_err)}"],
                )
        else:
            doc_obj = document

        doc_meta = doc_obj.model_dump()

        # Step 1: Execute Task 3 Document Contract Validation
        validation_resp = self.document_service.validate_document_contract(doc_obj)
        if not validation_resp.valid:
            return CSRExtractionResult(
                status="FAILED",
                document_metadata=doc_meta,
                ocr_required=False,
                identified_csr_data=IdentifiedCSRData(),
                raw_extracted_data={"text_by_page": {}, "tables": []},
                metadata=ExtractionMetadata(
                    extraction_time_seconds=round(time.time() - start_time, 4)
                ),
                errors=[f"Task 3 validation failed: {validation_resp.message}"],
            )

        # Step 2: Verify local file path existence
        if not doc_obj.local_file_path:
            return CSRExtractionResult(
                status="FAILED",
                document_metadata=doc_meta,
                ocr_required=False,
                identified_csr_data=IdentifiedCSRData(),
                raw_extracted_data={"text_by_page": {}, "tables": []},
                metadata=ExtractionMetadata(
                    extraction_time_seconds=round(time.time() - start_time, 4)
                ),
                errors=["local_file_path is missing or null; cannot extract from non-existent file"],
            )

        pdf_path = Path(doc_obj.local_file_path)
        if not pdf_path.exists() or not pdf_path.is_file():
            return CSRExtractionResult(
                status="FAILED",
                document_metadata=doc_meta,
                ocr_required=False,
                identified_csr_data=IdentifiedCSRData(),
                raw_extracted_data={"text_by_page": {}, "tables": []},
                metadata=ExtractionMetadata(
                    extraction_time_seconds=round(time.time() - start_time, 4)
                ),
                errors=[f"PDF file not found at path '{pdf_path}'"],
            )

        # Step 3: Verify binary PDF content using Task 2 validator
        try:
            with open(pdf_path, "rb") as f:
                content_bytes = f.read()

            is_valid_pdf, pdf_err = validate_pdf_content(
                content=content_bytes,
                content_type=doc_obj.content_type or "application/pdf",
                min_bytes=100,
            )
            if not is_valid_pdf:
                return CSRExtractionResult(
                    status="FAILED",
                    document_metadata=doc_meta,
                    ocr_required=False,
                    identified_csr_data=IdentifiedCSRData(),
                    raw_extracted_data={"text_by_page": {}, "tables": []},
                    metadata=ExtractionMetadata(
                        extraction_time_seconds=round(time.time() - start_time, 4)
                    ),
                    errors=[f"Binary PDF validation failed: {pdf_err}"],
                )
        except Exception as read_err:
            return CSRExtractionResult(
                status="FAILED",
                document_metadata=doc_meta,
                ocr_required=False,
                identified_csr_data=IdentifiedCSRData(),
                raw_extracted_data={"text_by_page": {}, "tables": []},
                metadata=ExtractionMetadata(
                    extraction_time_seconds=round(time.time() - start_time, 4)
                ),
                errors=[f"Error reading file '{pdf_path}': {str(read_err)}"],
            )

        # Step 4: Low-level PDF Extraction
        raw_extraction = self.pdf_extractor.extract(pdf_path)
        if raw_extraction.errors and not raw_extraction.pages:
            return CSRExtractionResult(
                status="FAILED",
                document_metadata=doc_meta,
                ocr_required=raw_extraction.ocr_required,
                ocr_details=raw_extraction.ocr_details,
                identified_csr_data=IdentifiedCSRData(),
                raw_extracted_data={"text_by_page": {}, "tables": []},
                metadata=ExtractionMetadata(
                    total_pages=raw_extraction.total_pages,
                    ocr_required=raw_extraction.ocr_required,
                    ocr_pages=raw_extraction.ocr_pages,
                    extraction_time_seconds=round(time.time() - start_time, 4),
                ),
                errors=raw_extraction.errors,
            )

        # Step 5: High-level CSR Information Parsing
        identified_csr_data, raw_extracted_data = self.csr_parser.parse(
            raw_extraction=raw_extraction,
            document_metadata=doc_meta,
        )

        # Calculate metrics
        pages_with_text = sum(1 for p in raw_extraction.pages if len(p.raw_text.strip()) > 0)
        pages_with_tables = sum(1 for p in raw_extraction.pages if len(p.tables) > 0)
        total_tables = sum(len(p.tables) for p in raw_extraction.pages)

        # Determine top-level status
        if raw_extraction.ocr_required:
            if pages_with_text > 0 or total_tables > 0:
                status = "PARTIAL_SUCCESS"
            else:
                status = "OCR_REQUIRED"
        elif raw_extraction.errors:
            status = "PARTIAL_SUCCESS"
        else:
            status = "SUCCESS"

        metadata = ExtractionMetadata(
            total_pages=raw_extraction.total_pages,
            pages_with_text=pages_with_text,
            pages_with_tables=pages_with_tables,
            total_tables=total_tables,
            ocr_required=raw_extraction.ocr_required,
            ocr_pages=raw_extraction.ocr_pages,
            extraction_time_seconds=round(time.time() - start_time, 4),
        )

        return CSRExtractionResult(
            status=status,
            document_metadata=doc_meta,
            ocr_required=raw_extraction.ocr_required,
            ocr_details=raw_extraction.ocr_details,
            identified_csr_data=identified_csr_data,
            raw_extracted_data=raw_extracted_data,
            metadata=metadata,
            errors=raw_extraction.errors,
        )

    def extract_from_file_path(
        self,
        file_path: Union[str, Path],
        company_name: Optional[str] = None,
        document_type: str = "annual_report",
        financial_year: str = "2023-24",
        source: str = "LOCAL_FILE",
    ) -> CSRExtractionResult:
        """Convenience method to extract directly from a file path."""
        p = Path(file_path)
        sha256_val = None
        file_size_val = None
        if p.exists() and p.is_file():
            try:
                with open(p, "rb") as f:
                    content = f.read()
                from mcp_server.retrieval.hasher import compute_sha256
                sha256_val = compute_sha256(content)
                file_size_val = len(content)
            except Exception:
                pass

        doc = DocumentInputSchema(
            company_name=company_name or p.stem,
            document_type=document_type,
            financial_year=financial_year,
            source=source,
            local_file_path=str(p.resolve()),
            file_name=p.name,
            file_size=file_size_val,
            sha256=sha256_val,
            version=1,
            status="FOUND",
        )
        return self.extract_from_document(doc)
