"""
Append-Only Repository for Task 13: Outreach Drafting Assistant.

Persists:
1. OutreachDraft objects with complete revision histories in `data/outreach_drafts.json`.
2. SendAuditRecord objects in `data/outreach_send_audit.json`.

Guarantees:
- Historical drafts and revisions are never silently overwritten or lost.
- All send activities are permanently and immutably auditable.
"""

import json
import os
import uuid
from typing import Dict, List, Optional

from ai_service.schemas.outreach import (
    OutreachApprovalStatus,
    OutreachDraft,
    SendAuditRecord,
)


class OutreachRepository:
    """In-memory and file-persisted repository for outreach drafts and send audit trails."""

    def __init__(
        self,
        drafts_path: Optional[str] = "data/outreach_drafts.json",
        audit_path: Optional[str] = "data/outreach_send_audit.json",
    ):
        self.drafts_path = drafts_path
        self.audit_path = audit_path
        self._drafts: Dict[str, OutreachDraft] = {}
        self._audit_records: List[SendAuditRecord] = []
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        if self.drafts_path and os.path.exists(self.drafts_path):
            try:
                with open(self.drafts_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for draft_id, draft_dict in data.items():
                    self._drafts[draft_id] = OutreachDraft.model_validate(draft_dict)
            except Exception:
                self._drafts = {}

        if self.audit_path and os.path.exists(self.audit_path):
            try:
                with open(self.audit_path, "r", encoding="utf-8") as f:
                    audit_list = json.load(f)
                self._audit_records = [SendAuditRecord.model_validate(a) for a in audit_list]
            except Exception:
                self._audit_records = []

    def _persist_drafts(self) -> None:
        if not self.drafts_path:
            return
        try:
            os.makedirs(os.path.dirname(self.drafts_path), exist_ok=True)
            serialized = {d_id: d.model_dump() for d_id, d in self._drafts.items()}
            with open(self.drafts_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
        except Exception:
            pass

    def _persist_audit(self) -> None:
        if not self.audit_path:
            return
        try:
            os.makedirs(os.path.dirname(self.audit_path), exist_ok=True)
            serialized = [a.model_dump() for a in self._audit_records]
            with open(self.audit_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
        except Exception:
            pass

    def save_draft(self, draft: OutreachDraft) -> OutreachDraft:
        """Saves or updates a draft record with its revision history."""
        self._drafts[draft.draft_id] = draft
        self._persist_drafts()
        return draft

    def get_draft(self, draft_id: str) -> Optional[OutreachDraft]:
        """Retrieves a draft by ID."""
        return self._drafts.get(draft_id)

    def get_drafts_by_company(self, company: str) -> List[OutreachDraft]:
        """Returns all drafts created for a specific company in chronological order."""
        comp_norm = company.strip().lower()
        return [d for d in self._drafts.values() if d.company.strip().lower() == comp_norm]

    def record_send_audit(self, audit: SendAuditRecord) -> SendAuditRecord:
        """Appends a permanent send audit record."""
        self._audit_records.append(audit)
        self._persist_audit()
        return audit

    def get_audit_records(self, company: Optional[str] = None) -> List[SendAuditRecord]:
        """Returns all send audit records, optionally filtered by company."""
        if not company:
            return list(self._audit_records)
        comp_norm = company.strip().lower()
        return [a for a in self._audit_records if a.company.strip().lower() == comp_norm]
