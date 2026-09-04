"""
Version Manager & Metadata Store for Document Retrieval.
Maintains persistent versioned document index and enforces deduplication and versioning rules.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_INDEX_PATH = Path("data") / "documents" / "metadata.json"


class VersionManager:
    """
    Manages document version records and deduplication logic.
    Persists state in metadata.json to ensure full traceability across sessions.
    """

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = Path(index_path) if index_path else DEFAULT_INDEX_PATH
        self._ensure_index_file()

    def _ensure_index_file(self):
        """Creates the metadata index file if it does not exist."""
        if not self.index_path.exists():
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_records([])

    def _read_records(self) -> List[Dict[str, Any]]:
        """Reads all records from the persistent JSON index."""
        try:
            if not self.index_path.exists():
                return []
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_records(self, records: List[Dict[str, Any]]) -> None:
        """Atomically writes records to the persistent JSON index."""
        temp_file = self.index_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(self.index_path)

    def find_records_for_document(
        self,
        company_name: str,
        document_type: str,
        financial_year: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Finds all existing historical version records for a specific document identity."""
        c_norm = company_name.strip().upper()
        d_norm = document_type.strip().lower()
        fy_norm = (financial_year.strip() if financial_year else "general").upper()

        records = self._read_records()
        matches = []
        for r in records:
            r_c = r.get("company_name", "").strip().upper()
            r_d = r.get("document_type", "").strip().lower()
            r_fy = (r.get("financial_year") or "general").strip().upper()

            if r_c == c_norm and r_d == d_norm and r_fy == fy_norm:
                matches.append(r)

        return sorted(matches, key=lambda x: x.get("version", 1))

    def evaluate_version(
        self,
        company_name: str,
        document_type: str,
        sha256_hash: str,
        financial_year: Optional[str] = None,
    ) -> Tuple[str, int, Optional[Dict[str, Any]]]:
        """
        Evaluates whether content is a duplicate, a new revision, or a new document.

        Returns:
            (action, version_to_use, existing_match)
            action in ['DUPLICATE_SKIPPED', 'NEW_VERSION_CREATED', 'CREATED']
        """
        existing = self.find_records_for_document(
            company_name=company_name,
            document_type=document_type,
            financial_year=financial_year,
        )

        if not existing:
            return "CREATED", 1, None

        # Check if identical hash already exists in this document identity
        for rec in existing:
            if rec.get("sha256") == sha256_hash:
                return "DUPLICATE_SKIPPED", rec.get("version", 1), rec

        # Content hash differs: create new incremented version
        highest_version = max(r.get("version", 1) for r in existing)
        return "NEW_VERSION_CREATED", highest_version + 1, None

    def record_document(
        self,
        company_name: str,
        document_type: str,
        source: str,
        source_url: Optional[str] = None,
        financial_year: Optional[str] = None,
        title: Optional[str] = None,
        local_file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        content_type: Optional[str] = None,
        sha256_hash: Optional[str] = None,
        version: int = 1,
        is_latest: bool = True,
        published_date: Optional[str] = None,
        status: str = "FOUND",
        error_information: Optional[str] = None,
        company_identifier: Optional[str] = None,
        retrieved_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a document metadata record. Updates is_latest flags on historical versions.
        """
        now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()
        records = self._read_records()

        # If marking as latest, set previous versions for the same identity to is_latest = False
        if is_latest:
            c_norm = company_name.strip().upper()
            d_norm = document_type.strip().lower()
            fy_norm = (financial_year.strip() if financial_year else "general").upper()

            for r in records:
                r_c = r.get("company_name", "").strip().upper()
                r_d = r.get("document_type", "").strip().lower()
                r_fy = (r.get("financial_year") or "general").strip().upper()

                if r_c == c_norm and r_d == d_norm and r_fy == fy_norm:
                    r["is_latest"] = False

        record: Dict[str, Any] = {
            "company_name": company_name.strip(),
            "company_identifier": company_identifier,
            "document_type": document_type.strip(),
            "financial_year": financial_year.strip() if financial_year else None,
            "title": title.strip() if title else None,
            "source": source.strip(),
            "source_url": source_url.strip() if source_url else None,
            "local_file_path": str(local_file_path) if local_file_path else None,
            "file_name": file_name,
            "file_size": file_size,
            "content_type": content_type,
            "sha256": sha256_hash,
            "version": version,
            "is_latest": is_latest,
            "published_date": published_date,
            "retrieved_at": now_iso,
            "last_verified_at": now_iso,
            "status": status,
            "error_information": error_information,
        }

        records.append(record)
        self._write_records(records)
        return record

    def touch_duplicate_record(self, existing_record: Dict[str, Any]) -> Dict[str, Any]:
        """Updates last_verified_at timestamp for a duplicate document without re-writing the file."""
        now_iso = datetime.now(timezone.utc).isoformat()
        records = self._read_records()

        for r in records:
            if r.get("sha256") == existing_record.get("sha256") and r.get("file_name") == existing_record.get("file_name"):
                r["last_verified_at"] = now_iso
                existing_record["last_verified_at"] = now_iso
                break

        self._write_records(records)
        return existing_record
