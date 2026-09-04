"""
CSR Freshness Service for Task 10.

Evaluates how current and trustworthy CSR/WASH data is for a company.
Integrates with Task 9 verification results, tracks verification cycles,
handles multiple sources, and preserves append-only historical records.
"""

from typing import Any, Dict, List, Optional
from ai_service.freshness.cycle import (
    format_iso_timestamp,
    get_current_verification_cycle,
    is_valid_cycle,
)
from ai_service.freshness.repository import FreshnessRepository
from ai_service.freshness.rules import FreshnessRulesEngine
from ai_service.schemas.freshness import (
    FreshnessAssessment,
    FreshnessHistoryResponse,
    FreshnessStatus,
    SourceFreshnessRecord,
    SourceType,
)
from ai_service.schemas.verification import (
    CSRChangeDetectionResult,
    CSRDocumentProfile,
    CSREvidenceReference,
    WASHDirection,
)


class CSRFreshnessService:
    """Core service for evaluating, recording, and querying CSR freshness states."""

    SOURCE_PRECEDENCE = {
        "CSR_ANNUAL_REPORT": 1,
        "ANNUAL_REPORT": 1,
        "BRSR": 2,
        "CSR_POLICY": 3,
        "EXCHANGE_DISCLOSURE": 4,
        "OTHER": 5,
    }

    def __init__(self, repository: Optional[FreshnessRepository] = None):
        self.repository = repository or FreshnessRepository()
        self.rules_engine = FreshnessRulesEngine()

    def calculate_freshness(
        self,
        company: str,
        verification_result: Optional[CSRChangeDetectionResult] = None,
        document_profile: Optional[CSRDocumentProfile] = None,
        verification_cycle: Optional[str] = None,
        financial_year: Optional[str] = None,
        is_current_reporting_cycle: bool = True,
        document_available: bool = True,
        wash_direction: Optional[WASHDirection] = None,
        sources: Optional[List[SourceFreshnessRecord]] = None,
        primary_document_metadata: Optional[Dict[str, Any]] = None,
        retrieved_at: Optional[str] = None,
        verified_at: Optional[str] = None,
        publication_date: Optional[str] = None,
    ) -> FreshnessAssessment:
        """
        Calculates and records a traceable freshness assessment for the company.
        Preserves historical audit trail (never overwrites).
        """
        cycle = verification_cycle or get_current_verification_cycle()
        if not is_valid_cycle(cycle):
            cycle = get_current_verification_cycle()

        now_iso = format_iso_timestamp()
        primary_meta = primary_document_metadata or {}

        # 1. Resolve Document Identity & Metadata
        doc_fy = (
            financial_year
            or (document_profile.financial_year if document_profile else None)
            or (
                verification_result.current_document.financial_year
                if verification_result and verification_result.current_document
                else None
            )
            or primary_meta.get("financial_year")
        )
        doc_type = (
            (document_profile.document_type if document_profile else None)
            or (
                verification_result.current_document.document_type
                if verification_result and verification_result.current_document
                else None
            )
            or primary_meta.get("document_type", "CSR_ANNUAL_REPORT")
        )
        doc_version = (
            (document_profile.document_version if document_profile else 1)
            or (
                verification_result.current_document.document_version
                if verification_result and verification_result.current_document
                else 1
            )
            or primary_meta.get("document_version", 1)
        )
        doc_hash = (
            (document_profile.document_hash if document_profile else None)
            or (
                verification_result.current_document.document_hash
                if verification_result and verification_result.current_document
                else None
            )
            or primary_meta.get("document_hash")
        )
        source_url = (
            (document_profile.source_url if document_profile else None)
            or primary_meta.get("source_url")
        )
        pub_date = publication_date or primary_meta.get("publication_date")  # None if unavailable
        doc_retrieved_at = retrieved_at or primary_meta.get("retrieved_at", now_iso)

        # 2. Distinguish Retrieval from Actual Verification
        # Retrieval alone is NOT successful verification
        is_verified = bool(verified_at or verification_result is not None)
        doc_verified_at = verified_at or (now_iso if is_verified else None)

        # 3. Extract WASH Direction and Evidence
        wash_dir: Optional[WASHDirection] = wash_direction
        evidence_list: List[CSREvidenceReference] = []

        if verification_result:
            wash_dir = verification_result.overall_wash_direction
            evidence_list.extend(verification_result.evidence)

        # Check if WASH is active
        has_wash = False
        if document_profile:
            has_wash = bool(
                document_profile.has_wash_activity
                or (document_profile.wash_spend_crore and document_profile.wash_spend_crore > 0)
                or any(p.is_wash for p in document_profile.projects)
                or document_profile.wash_focus_areas
            )
        elif wash_dir in (WASHDirection.INCREASED, WASHDirection.STABLE, WASHDirection.NEW_FOCUS, WASHDirection.MIXED):
            has_wash = True

        is_insufficient = (wash_dir == WASHDirection.INSUFFICIENT_EVIDENCE)

        # 4. Multi-Source Evaluation & Precedence
        all_sources = list(sources or [])
        if not all_sources and doc_type:
            # Create a source record from primary doc
            source_rec = SourceFreshnessRecord(
                source_name=primary_meta.get("source_name", f"{doc_type} {doc_fy or ''}".strip()),
                document_type=doc_type,
                document_version=doc_version,
                document_hash=doc_hash,
                source_url=source_url,
                publication_date=pub_date,
                retrieved_at=doc_retrieved_at,
                verified_at=doc_verified_at,
                financial_year=doc_fy,
                status=FreshnessStatus.YELLOW,  # Will be adjusted by rules
                reason="Primary evaluated CSR disclosure document",
            )
            all_sources.append(source_rec)

        # 5. Evaluate Rules
        status, reason = self.rules_engine.evaluate(
            is_verified_current_cycle=is_verified,
            is_current_reporting_cycle=is_current_reporting_cycle,
            wash_direction=wash_dir,
            has_wash_evidence=has_wash,
            document_available=document_available,
            is_insufficient_evidence=is_insufficient,
        )

        # Update primary source status to match evaluation
        if all_sources:
            # Sort sources by domain precedence
            all_sources.sort(key=lambda s: self.SOURCE_PRECEDENCE.get(s.document_type.upper(), 99))
            all_sources[0].status = status
            all_sources[0].reason = reason

        # 6. Retrieve Previous Assessment for Transition Tracking
        prev_assessment = self.repository.get_current_status(company)
        prev_status = prev_assessment.status if prev_assessment else None

        # 7. Construct and Persist FreshnessAssessment
        assessment = FreshnessAssessment(
            company=company,
            status=status,
            reason=reason,
            financial_year=doc_fy,
            document_type=doc_type,
            document_version=doc_version,
            source=primary_meta.get("source_name", doc_type),
            source_url=source_url,
            document_hash=doc_hash,
            publication_date=pub_date,
            retrieved_at=doc_retrieved_at,
            verified_at=doc_verified_at,
            verification_cycle=cycle,
            wash_direction=wash_dir,
            evidence=evidence_list,
            previous_status=prev_status,
            sources=all_sources,
            assessment_metadata={
                "is_verified_current_cycle": is_verified,
                "is_current_reporting_cycle": is_current_reporting_cycle,
                "document_available": document_available,
                "sources_evaluated_count": len(all_sources),
            },
        )

        # Append-only persistence (never overwrites historical records)
        saved_assessment = self.repository.save(assessment)
        return saved_assessment

    def get_current_status(self, company: str) -> Optional[FreshnessAssessment]:
        """Retrieves the latest freshness assessment for the company."""
        return self.repository.get_current_status(company)

    def get_history(self, company: str) -> FreshnessHistoryResponse:
        """Retrieves complete chronological freshness timeline and summary for the company."""
        history = self.repository.get_history(company)
        current = self.repository.get_current_status(company)
        last_verified = self.repository.get_last_verified(company)

        if not current:
            # No prior assessment exists
            cycle = get_current_verification_cycle()
            return FreshnessHistoryResponse(
                company=company,
                current_status=FreshnessStatus.YELLOW,
                last_verified_at=None,
                last_verified_financial_year=None,
                verification_cycle=cycle,
                reason="No verification assessments recorded for this company yet.",
                previous_status=None,
                history=[],
            )

        return FreshnessHistoryResponse(
            company=company,
            current_status=current.status,
            last_verified_at=last_verified.verified_at if last_verified else None,
            last_verified_financial_year=last_verified.financial_year if last_verified else None,
            verification_cycle=current.verification_cycle,
            reason=current.reason,
            previous_status=current.previous_status,
            history=history,
        )

    def get_last_verification(self, company: str) -> Optional[FreshnessAssessment]:
        """Retrieves the most recent assessment where verification was completed."""
        return self.repository.get_last_verified(company)
