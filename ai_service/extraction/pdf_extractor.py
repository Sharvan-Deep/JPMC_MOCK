"""
Low-level PDF Extractor for Task 4.
Extracts raw text, table matrices, and detects scanned/image-only pages requiring OCR.
Uses pdfplumber for robust layout and table structure preservation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pdfplumber
import pypdf

from ai_service.logging_config import logger


@dataclass
class ExtractedTableData:
    page_number: int
    table_index: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[Optional[str]]] = field(default_factory=list)


@dataclass
class ExtractedPageData:
    page_number: int
    raw_text: str = ""
    tables: List[ExtractedTableData] = field(default_factory=list)
    has_images: bool = False
    image_count: int = 0
    ocr_required: bool = False
    error: Optional[str] = None


@dataclass
class RawPDFExtraction:
    total_pages: int = 0
    pages: List[ExtractedPageData] = field(default_factory=list)
    ocr_required: bool = False
    ocr_pages: List[int] = field(default_factory=list)
    ocr_details: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class PDFExtractor:
    """Extracts raw text and tables from PDF documents and flags OCR-dependent pages."""

    def __init__(self, min_text_threshold_per_page: int = 25):
        self.min_text_threshold_per_page = min_text_threshold_per_page

    def extract(self, file_path: Union[str, Path]) -> RawPDFExtraction:
        """
        Extracts raw text and tables from a validated PDF file.

        Args:
            file_path: Path to the local PDF file.

        Returns:
            RawPDFExtraction containing page-level text, tables, and OCR indicators.
        """
        path = Path(file_path)
        result = RawPDFExtraction()

        if not path.exists():
            err = f"PDF file does not exist at '{path}'"
            logger.error(err)
            result.errors.append(err)
            return result

        if path.stat().st_size == 0:
            err = f"PDF file at '{path}' is 0 bytes (empty file)"
            logger.error(err)
            result.errors.append(err)
            return result

        # First verify it is openable with pypdf to check encryption or gross structural corruption
        try:
            reader = pypdf.PdfReader(str(path))
            if reader.is_encrypted:
                try:
                    # Attempt decrypt with empty password (common for public PDFs)
                    reader.decrypt("")
                except Exception:
                    err = f"PDF at '{path}' is password-encrypted and cannot be extracted"
                    logger.error(err)
                    result.errors.append(err)
                    return result
            num_pages = len(reader.pages)
            result.total_pages = num_pages
            if num_pages == 0:
                err = f"PDF at '{path}' contains 0 pages"
                logger.error(err)
                result.errors.append(err)
                return result
        except Exception as e:
            err = f"Failed to open or inspect PDF structure for '{path}': {str(e)}"
            logger.error(err)
            result.errors.append(err)
            return result

        # Extract content page-by-page using pdfplumber
        try:
            with pdfplumber.open(str(path)) as pdf:
                result.total_pages = len(pdf.pages)

                for idx, page in enumerate(pdf.pages, start=1):
                    page_data = ExtractedPageData(page_number=idx)
                    try:
                        # 1. Check embedded images
                        images = getattr(page, "images", []) or []
                        page_data.image_count = len(images)
                        page_data.has_images = len(images) > 0

                        # 2. Extract text
                        extracted_text = page.extract_text(layout=False) or ""
                        page_data.raw_text = extracted_text

                        # 3. Detect scanned / OCR-needed pages
                        cleaned_len = len(extracted_text.strip())
                        if cleaned_len < self.min_text_threshold_per_page and page_data.has_images:
                            page_data.ocr_required = True
                            result.ocr_pages.append(idx)
                        elif cleaned_len == 0 and page_data.has_images:
                            page_data.ocr_required = True
                            result.ocr_pages.append(idx)

                        # 4. Extract tables preserving 2D structure
                        raw_tables = page.extract_tables()
                        if raw_tables:
                            for tbl_idx, table_matrix in enumerate(raw_tables):
                                if not table_matrix or len(table_matrix) == 0:
                                    continue

                                # Header extraction: row 0 if available, else generic col names
                                first_row = table_matrix[0]
                                headers = [
                                    (str(col).strip() if col is not None else f"col_{c_idx}")
                                    for c_idx, col in enumerate(first_row)
                                ]
                                rows = table_matrix[1:] if len(table_matrix) > 1 else []

                                # Clean cell strings slightly (strip whitespace, retain raw value)
                                cleaned_rows: List[List[Optional[str]]] = []
                                for r in rows:
                                    cleaned_row = [
                                        (str(c).strip() if c is not None else None)
                                        for c in r
                                    ]
                                    # Ignore completely empty rows
                                    if any(c is not None and c != "" for c in cleaned_row):
                                        cleaned_rows.append(cleaned_row)

                                page_data.tables.append(
                                    ExtractedTableData(
                                        page_number=idx,
                                        table_index=tbl_idx,
                                        headers=headers,
                                        rows=cleaned_rows,
                                    )
                                )

                    except Exception as page_exc:
                        page_err = f"Error extracting page {idx}: {str(page_exc)}"
                        logger.warning(page_err)
                        page_data.error = page_err
                        result.errors.append(page_err)

                    result.pages.append(page_data)

        except Exception as e:
            err = f"Fatal extraction failure processing PDF at '{path}': {str(e)}"
            logger.error(err)
            result.errors.append(err)

        if result.ocr_pages:
            result.ocr_required = True
            result.ocr_details = (
                f"Pages {result.ocr_pages} appear to contain scanned images or insufficient "
                f"digital text (< {self.min_text_threshold_per_page} chars); OCR processing is required."
            )

        return result
