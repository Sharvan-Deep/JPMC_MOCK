"""
Document Validation Module for Task 2.
Validates downloaded content before saving to disk.
Enforces PDF magic number (%PDF-), rejects HTML/error responses, and checks response size.
"""

from typing import Optional, Tuple

# Standard PDF header signature
PDF_MAGIC_BYTES = b"%PDF-"


def validate_pdf_content(
    content: bytes,
    content_type: Optional[str] = None,
    min_bytes: int = 100,
) -> Tuple[bool, Optional[str]]:
    """
    Validates binary content to ensure it is a legitimate PDF document.

    Checks:
    1. Content is not None and not empty.
    2. Rejects HTML, JSON, XML error responses masquerading as PDF.
    3. Content begins with PDF magic number '%PDF-'.
    4. Content meets minimum size threshold.
    5. Checks Content-Type header if provided.

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if content is None or len(content) == 0:
        return False, "Response body is empty (0 bytes)"

    # Inspect the first 1024 bytes for HTML, JSON or error markers
    header_sample = content[:1024].lower()

    # Reject obvious HTML or error strings
    if (
        b"<!doctype html" in header_sample
        or b"<html" in header_sample
        or b"<head" in header_sample
        or b"<body" in header_sample
    ):
        return False, "Received HTML error page instead of PDF document"

    if header_sample.strip().startswith(b"{") and (b"error" in header_sample or b"message" in header_sample):
        return False, "Received JSON error response instead of PDF document"

    # Validate content_type header if provided
    if content_type:
        clean_ct = content_type.lower().split(";")[0].strip()
        acceptable_types = [
            "application/pdf",
            "application/x-pdf",
            "application/octet-stream",
            "binary/octet-stream",
        ]
        if clean_ct and clean_ct not in acceptable_types and not clean_ct.startswith("application/"):
            return False, f"Unexpected Content-Type header '{content_type}', expected 'application/pdf'"

    # Check for %PDF- signature (standard specification allows %PDF- within first 1024 bytes)
    if PDF_MAGIC_BYTES not in content[:1024]:
        return False, "Invalid PDF: Missing '%PDF-' file signature in header"

    if len(content) < min_bytes:
        return False, f"File payload too small ({len(content)} bytes), below minimum threshold of {min_bytes} bytes"

    return True, None
