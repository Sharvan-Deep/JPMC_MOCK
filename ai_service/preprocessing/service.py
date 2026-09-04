"""
CSR Data Preprocessing Orchestration Service for Task 5.
Coordinates text cleaning, field normalization (Crores, FY, company name),
table matrix cleaning, and extraction-duplicate filtering.
Maintains full traceability to Task 4 raw extraction.
"""

import time
from typing import Any, Dict, List, Optional, Union

from ai_service.logging_config import logger
from ai_service.preprocessing.cleaner import TextCleaner
from ai_service.preprocessing.normalizer import FieldNormalizer
from ai_service.preprocessing.table_cleaner import TableCleaner
from ai_service.schemas.extraction import CSRExtractionResult, CSRTableRaw
from ai_service.schemas.preprocessing import (
    CleanedCSRData,
    CleanedCSRRecord,
    CSRPreprocessingResult,
    PreprocessingMetadata,
)


class CSRPreprocessingService:
    """Orchestrates cleaning and deterministic normalization of Task 4 extracted data."""

    def __init__(
        self,
        text_cleaner: Optional[TextCleaner] = None,
        normalizer: Optional[FieldNormalizer] = None,
        table_cleaner: Optional[TableCleaner] = None,
    ):
        self.text_cleaner = text_cleaner or TextCleaner()
        self.normalizer = normalizer or FieldNormalizer()
        self.table_cleaner = table_cleaner or TableCleaner()

    def preprocess(
        self,
        extraction_data: Union[CSRExtractionResult, Dict[str, Any]],
    ) -> CSRPreprocessingResult:
        """
        Preprocesses and cleans raw Task 4 extraction output.

        Strictly guarantees:
        1. Original raw values and page mappings are preserved.
        2. Text artifacts and whitespace are cleaned.
        3. Amounts, financial years, and company names are deterministically normalized.
        4. Empty table rows/columns are pruned and extraction duplicates filtered.
        5. Does NOT make WASH relevance or donation decisions (reserved for Task 6).
        """
        start_time = time.time()
        warnings: List[str] = []
        errors: List[str] = []

        # Convert dict to CSRExtractionResult if needed
        if isinstance(extraction_data, dict):
            try:
                extraction_obj = CSRExtractionResult(**extraction_data)
            except Exception as e:
                err_msg = f"Failed to parse extraction data into CSRExtractionResult: {str(e)}"
                logger.error(err_msg)
                return CSRPreprocessingResult(
                    status="FAILED",
                    document_metadata=extraction_data.get("document_metadata", {}),
                    cleaned_data=CleanedCSRData(),
                    cleaned_text_by_page={},
                    cleaned_tables=[],
                    metadata=PreprocessingMetadata(
                        processing_time_seconds=round(time.time() - start_time, 4)
                    ),
                    errors=[err_msg],
                )
        else:
            extraction_obj = extraction_data

        doc_meta = extraction_obj.document_metadata or {}

        # Validate Task 4 status
        valid_statuses = {"SUCCESS", "PARTIAL_SUCCESS", "OCR_REQUIRED"}
        if extraction_obj.status not in valid_statuses:
            err_msg = f"Invalid or failed Task 4 extraction status '{extraction_obj.status}'"
            logger.warning(err_msg)
            return CSRPreprocessingResult(
                status="FAILED",
                document_metadata=doc_meta,
                cleaned_data=CleanedCSRData(),
                cleaned_text_by_page={},
                cleaned_tables=[],
                metadata=PreprocessingMetadata(
                    processing_time_seconds=round(time.time() - start_time, 4)
                ),
                errors=[err_msg],
            )

        raw_identified = extraction_obj.identified_csr_data
        raw_extracted = extraction_obj.raw_extracted_data or {}

        # 1. Clean page-by-page text
        raw_text_dict = raw_extracted.get("text_by_page", {})
        cleaned_text_by_page, text_warnings = self.text_cleaner.clean_text_by_page(raw_text_dict)
        warnings.extend(text_warnings)

        # 2. Normalize top-level fields
        canonical_comp, raw_comp = self.normalizer.normalize_company_name(
            raw_identified.donor_name or doc_meta.get("company_name")
        )
        norm_fy, raw_fy = self.normalizer.normalize_financial_year(
            raw_identified.financial_year or doc_meta.get("financial_year")
        )
        norm_total_amt, raw_total_amt = self.normalizer.normalize_amount_to_crores(
            raw_identified.total_csr_amount
        )

        # 3. Clean raw tables
        raw_tables = raw_extracted.get("tables", [])
        cleaned_tables: List[CSRTableRaw] = []
        for t_dict in raw_tables:
            try:
                t_obj = CSRTableRaw(**t_dict) if isinstance(t_dict, dict) else t_dict
                cleaned_t = self.table_cleaner.clean_table(t_obj)
                cleaned_tables.append(cleaned_t)
            except Exception as tbl_err:
                warnings.append(f"Error cleaning table: {tbl_err}")

        # 4. Clean and normalize individual project records
        raw_projects = raw_identified.projects or []
        cleaned_records: List[CleanedCSRRecord] = []

        for p in raw_projects:
            # Clean text attributes
            c_name = " ".join(p.project_name.split()) if p.project_name else None
            c_cat = " ".join(p.category.split()) if p.category else None
            c_loc = " ".join(p.location.split()) if p.location else None
            c_ben = " ".join(p.beneficiaries.split()) if p.beneficiaries else None
            c_mode = " ".join(p.implementation_mode.split()) if p.implementation_mode else None

            # Normalize amounts to crores while preserving raw
            norm_spent, raw_spent = self.normalizer.normalize_amount_to_crores(p.amount_spent)
            norm_alloc, raw_alloc = self.normalizer.normalize_amount_to_crores(p.amount_allocated)

            rec = CleanedCSRRecord(
                raw_project=p,
                project_name=c_name,
                category=c_cat,
                location=c_loc,
                raw_amount_spent=raw_spent,
                normalized_amount_spent_crore=norm_spent,
                raw_amount_allocated=raw_alloc,
                normalized_amount_allocated_crore=norm_alloc,
                beneficiaries=c_ben,
                implementation_mode=c_mode,
                page_number=p.page_number,
                is_extraction_duplicate=False,
            )
            cleaned_records.append(rec)

        # 5. Filter extraction duplicate records
        raw_record_count = len(cleaned_records)
        deduped_records, duplicates_removed = self.table_cleaner.filter_extraction_duplicates(
            cleaned_records
        )

        cleaned_data = CleanedCSRData(
            canonical_company_name=canonical_comp,
            raw_company_name=raw_comp,
            normalized_financial_year=norm_fy,
            raw_financial_year=raw_fy,
            raw_total_csr_amount=raw_total_amt,
            normalized_total_csr_amount_crore=norm_total_amt,
            records=deduped_records,
            other_fields=raw_identified.other_fields or {},
        )

        # Calculate metadata
        raw_pages_count = extraction_obj.metadata.total_pages or len(cleaned_text_by_page)
        proc_metadata = PreprocessingMetadata(
            raw_pages=raw_pages_count,
            processed_pages=len(cleaned_text_by_page),
            raw_records_count=raw_record_count,
            cleaned_records_count=len(deduped_records),
            duplicates_removed=duplicates_removed,
            warnings=warnings,
            processing_time_seconds=round(time.time() - start_time, 4),
        )

        status = "SUCCESS"
        if errors:
            status = "PARTIAL_SUCCESS" if (deduped_records or cleaned_text_by_page) else "FAILED"

        return CSRPreprocessingResult(
            status=status,
            document_metadata=doc_meta,
            cleaned_data=cleaned_data,
            cleaned_text_by_page=cleaned_text_by_page,
            cleaned_tables=cleaned_tables,
            metadata=proc_metadata,
            errors=errors,
        )
