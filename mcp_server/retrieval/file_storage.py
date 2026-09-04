"""
File Storage Manager for Versioned Document Storage.
Organizes documents into deterministic, filesystem-safe paths under data/documents/.
"""

import os
import re
from pathlib import Path
from typing import Optional

BASE_DOCUMENTS_DIR = Path("data") / "documents"

FOLDER_MAPPING = {
    "annual_report": "annual_reports",
    "csr_policy": "csr_policies",
    "brsr": "brsr",
    "disclosure": "disclosures",
}


def sanitize_filename_part(part: Optional[str], default: str = "doc") -> str:
    """Sanitizes a string component for safe inclusion in filenames and paths."""
    if not part:
        return default
    # Remove filesystem illegal characters: <>:"/\|?* and control characters
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(part))
    # Replace spaces and punctuation runs with single underscore
    cleaned = re.sub(r"[\s\-_.]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned[:64] or default


def get_document_folder(document_type: str, base_dir: Optional[Path] = None) -> Path:
    """Returns the subfolder path for a given document type."""
    base = Path(base_dir) if base_dir else BASE_DOCUMENTS_DIR
    subfolder = FOLDER_MAPPING.get(document_type, "disclosures")
    target_dir = base / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def generate_versioned_filename(
    company_name: str,
    document_type: str,
    financial_year: Optional[str] = None,
    version: int = 1,
    sha256_hash: Optional[str] = None,
) -> str:
    """
    Generates a deterministic, filesystem-safe filename for a versioned document.
    Format: {company}_{document_type}_{financial_year}_v{version}_{hash[:8]}.pdf
    """
    safe_company = sanitize_filename_part(company_name, "COMPANY")
    safe_type = sanitize_filename_part(document_type, "doc")
    safe_fy = sanitize_filename_part(financial_year, "general")
    hash_tag = (sha256_hash[:8]) if sha256_hash else "nohash"

    return f"{safe_company}_{safe_type}_{safe_fy}_v{version}_{hash_tag}.pdf"


def save_document_file(
    content: bytes,
    company_name: str,
    document_type: str,
    financial_year: Optional[str] = None,
    version: int = 1,
    sha256_hash: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Atomically saves document bytes into versioned directory.
    Returns the Path to the saved document.
    """
    target_dir = get_document_folder(document_type, base_dir=base_dir)
    filename = generate_versioned_filename(
        company_name=company_name,
        document_type=document_type,
        financial_year=financial_year,
        version=version,
        sha256_hash=sha256_hash,
    )
    dest_path = target_dir / filename

    # Atomic write via temporary file
    temp_path = dest_path.with_suffix(".tmp")
    with open(temp_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    temp_path.replace(dest_path)
    return dest_path
