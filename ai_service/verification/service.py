"""
CSR Verification & Change Detection Service for Task 9.

Orchestrates deterministic calculations, semantic AI comparisons, and optional
ChromaDB evidence retrieval to compare CSR profiles across financial years or
document versions without overwriting historical records.
"""

import logging
from typing import Any, Dict, List, Optional
from ai_service.schemas.verification import (
    BeneficiaryComparison,
    ChangeCategory,
    CommitmentComparison,
    CSRChangeDetectionRequest,
    CSRChangeDetectionResult,
    CSRChangeItem,
    CSRDimensionsComparison,
    CSRDocumentProfile,
    CSREvidenceReference,
    DocumentSummaryHeader,
    GeographyComparison,
    PolicyComparison,
    ProjectComparison,
    SpendingComparison,
    VerificationConfidence,
    WASHDirection,
    WASHFocusComparison,
)
from ai_service.verification.comparator import DeterministicComparator, _build_evidence_ref
from ai_service.verification.providers import (
    BaseChangeDetectionProvider,
    MockChangeDetectionProvider,
)

logger = logging.getLogger(__name__)


class CSRChangeDetectionService:
    """
    Main service for verifying CSR documents and detecting changes between
    versions or reporting periods across 7 core dimensions.
    """

    def __init__(
        self,
        semantic_provider: Optional[BaseChangeDetectionProvider] = None,
        search_service: Optional[Any] = None,
    ):
        self.comparator = DeterministicComparator()
        self.semantic_provider = semantic_provider or MockChangeDetectionProvider()
        self.search_service = search_service

    def verify_changes(
        self,
        previous_profile: Optional[CSRDocumentProfile],
        current_profile: Optional[CSRDocumentProfile],
        query_chromadb_if_needed: bool = False,
    ) -> CSRChangeDetectionResult:
        """
        Executes complete verification and change detection between two profiles.

        Raises:
            ValueError: If either previous_profile or current_profile is missing.
        """
        # 1. Guard clauses for missing profiles
        if previous_profile is None and current_profile is None:
            raise ValueError("Both previous and current document profiles are missing.")
        if previous_profile is None:
            raise ValueError(
                "Missing previous document profile for comparison: cannot perform delta analysis."
            )
        if current_profile is None:
            raise ValueError(
                "Missing current document profile for comparison: cannot perform delta analysis."
            )

        prev = previous_profile
        curr = current_profile

        # 2. Comparison Period Label
        prev_period = prev.financial_year or f"v{prev.document_version}"
        curr_period = curr.financial_year or f"v{curr.document_version}"
        comparison_period = f"{prev_period} -> {curr_period}"

        # 3. Headers preserving both states
        prev_hdr = DocumentSummaryHeader(
            company=prev.company,
            financial_year=prev.financial_year,
            document_version=prev.document_version,
            document_type=prev.document_type,
            document_hash=prev.document_hash,
        )
        curr_hdr = DocumentSummaryHeader(
            company=curr.company,
            financial_year=curr.financial_year,
            document_version=curr.document_version,
            document_type=curr.document_type,
            document_hash=curr.document_hash,
        )

        # 4. Optional ChromaDB Evidence Gathering
        chroma_evidence: List[CSREvidenceReference] = []
        if query_chromadb_if_needed and self.search_service is not None:
            try:
                # Query previous period
                prev_query = f"{prev.company} CSR projects {prev_period}"
                prev_search = self.search_service.search(
                    query=prev_query,
                    filters={"financial_year": prev.financial_year} if prev.financial_year else None,
                    top_k=2,
                )
                for res in prev_search.results:
                    meta = res.metadata or {}
                    chroma_evidence.append(
                        CSREvidenceReference(
                            company=meta.get("company_name", prev.company),
                            financial_year=meta.get("financial_year", prev.financial_year),
                            document_type=meta.get("document_type", prev.document_type),
                            document_version=meta.get("document_version", prev.document_version),
                            page=meta.get("page_number"),
                            source_url=prev.source_url,
                            relevant_source_text=res.text[:200],
                            document_hash=meta.get("sha256") or prev.document_hash,
                        )
                    )
            except Exception as e:
                logger.warning("Failed to retrieve supplemental ChromaDB evidence: %s", e)


        # 5. Dimension Comparisons

        # (a) Spending
        spending_comp: SpendingComparison = self.comparator.compare_spending(prev, curr)

        # (b) Geography
        geography_comp: GeographyComparison = self.comparator.compare_geography(prev, curr)

        # (c) Projects: Exact + Semantic Matching
        unmatched_prev, unmatched_curr, continuing_exact = self.comparator.match_exact_projects(
            prev, curr
        )

        continuing_names = [p_pair[1].project_name for p_pair in continuing_exact]
        multi_year_names = [
            p_pair[1].project_name
            for p_pair in continuing_exact
            if p_pair[0].is_multi_year or p_pair[1].is_multi_year
        ]

        # Semantic matching for remaining unmatched projects
        semantic_matches = []
        if unmatched_prev and unmatched_curr:
            try:
                semantic_matches = self.semantic_provider.find_semantic_project_matches(
                    unmatched_prev, unmatched_curr
                )
            except Exception as e:
                logger.warning("Semantic provider encountered error: %s", e)

        sem_prev_matched = {m.previous_project for m in semantic_matches}
        sem_curr_matched = {m.current_project for m in semantic_matches}

        for m in semantic_matches:
            continuing_names.append(m.current_project)

        discontinued_projs = [
            p.project_name for p in unmatched_prev if p.project_name not in sem_prev_matched
        ]
        new_projs = [
            p.project_name for p in unmatched_curr if p.project_name not in sem_curr_matched
        ]

        # Project change type
        if not prev.projects and not curr.projects:
            proj_change_type = ChangeCategory.INSUFFICIENT_EVIDENCE
        elif new_projs and not discontinued_projs:
            proj_change_type = ChangeCategory.NEW
        elif discontinued_projs and not new_projs:
            proj_change_type = ChangeCategory.DISCONTINUED
        elif new_projs and discontinued_projs:
            proj_change_type = ChangeCategory.CHANGED_DIRECTION
        else:
            proj_change_type = ChangeCategory.CONTINUED

        proj_ev_prev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("projects"))
        proj_ev_curr = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("projects"))
        proj_ev = [e for e in (proj_ev_prev, proj_ev_curr) if e is not None]

        project_comp = ProjectComparison(
            new_projects=new_projs,
            discontinued_projects=discontinued_projs,
            continuing_projects=continuing_names,
            multi_year_projects=multi_year_names,
            semantic_matches=semantic_matches,
            change_type=proj_change_type,
            evidence=proj_ev,
        )

        # (d) Beneficiaries
        beneficiary_comp: BeneficiaryComparison = self.comparator.compare_beneficiaries(prev, curr)

        # (e) Commitments
        commitment_comp: CommitmentComparison = self.comparator.compare_commitments(prev, curr)

        # (f) Policy
        policy_comp: PolicyComparison = self.comparator.compare_policy(prev, curr)

        # (g) WASH Focus & Synthesized Direction
        wash_focus_comp, overall_wash_dir = self.comparator.determine_wash_focus_and_direction(
            prev, curr, spending_comp, project_comp
        )

        # 6. Aggregate Individual Change Items
        changes: List[CSRChangeItem] = []

        # Spending changes
        for m in spending_comp.metrics:
            if m.change_type not in (ChangeCategory.UNCHANGED, ChangeCategory.INSUFFICIENT_EVIDENCE):
                changes.append(
                    CSRChangeItem(
                        dimension=f"spending:{m.metric}",
                        change_type=m.change_type,
                        description=(
                            f"{m.metric.replace('_', ' ').title()} changed by "
                            f"{m.absolute_change} {m.unit} ({m.percentage_change}%)."
                        ),
                        previous_value=m.previous_value,
                        current_value=m.current_value,
                        absolute_change=m.absolute_change,
                        percentage_change=m.percentage_change,
                        evidence=m.evidence,
                    )
                )

        # Project changes
        for np in project_comp.new_projects:
            changes.append(
                CSRChangeItem(
                    dimension="projects",
                    change_type=ChangeCategory.NEW,
                    description=f"New project introduced: '{np}'.",
                    current_value=np,
                    evidence=project_comp.evidence,
                )
            )
        for dp in project_comp.discontinued_projects:
            changes.append(
                CSRChangeItem(
                    dimension="projects",
                    change_type=ChangeCategory.DISCONTINUED,
                    description=f"Project discontinued: '{dp}'.",
                    previous_value=dp,
                    evidence=project_comp.evidence,
                )
            )
        for sm in project_comp.semantic_matches:
            changes.append(
                CSRChangeItem(
                    dimension="projects",
                    change_type=ChangeCategory.CONTINUED,
                    description=f"Project continuation (semantic match): '{sm.previous_project}' -> '{sm.current_project}' ({sm.rationale}).",
                    previous_value=sm.previous_project,
                    current_value=sm.current_project,
                    evidence=project_comp.evidence,
                )
            )

        # Geography changes
        if geography_comp.new_locations:
            changes.append(
                CSRChangeItem(
                    dimension="geography",
                    change_type=ChangeCategory.EXPANDED,
                    description=f"Geographic expansion to states: {', '.join(geography_comp.new_locations)}.",
                    current_value=geography_comp.new_locations,
                    evidence=geography_comp.evidence,
                )
            )
        if geography_comp.removed_locations:
            changes.append(
                CSRChangeItem(
                    dimension="geography",
                    change_type=ChangeCategory.CONTRACTED,
                    description=f"Geographic exit from states: {', '.join(geography_comp.removed_locations)}.",
                    previous_value=geography_comp.removed_locations,
                    evidence=geography_comp.evidence,
                )
            )

        # WASH Focus changes
        if wash_focus_comp.direction != WASHDirection.STABLE:
            changes.append(
                CSRChangeItem(
                    dimension="wash_focus",
                    change_type=ChangeCategory(wash_focus_comp.direction.value)
                    if wash_focus_comp.direction.value in ChangeCategory._value2member_map_
                    else ChangeCategory.CHANGED_DIRECTION,
                    description=f"WASH strategic focus shifted: {wash_focus_comp.direction.value}.",
                    previous_value=wash_focus_comp.previous_focus,
                    current_value=wash_focus_comp.current_focus,
                    evidence=wash_focus_comp.evidence,
                )
            )

        # 7. Collect all unique evidence items
        all_evidence: List[CSREvidenceReference] = []
        seen_ev = set()
        for ev in (
            spending_comp.evidence
            + geography_comp.evidence
            + project_comp.evidence
            + beneficiary_comp.evidence
            + commitment_comp.evidence
            + policy_comp.evidence
            + wash_focus_comp.evidence
            + chroma_evidence
        ):
            key = (ev.financial_year, ev.document_version, ev.page, ev.relevant_source_text)
            if key not in seen_ev:
                seen_ev.add(key)
                all_evidence.append(ev)

        # 8. Determine Confidence
        if overall_wash_dir == WASHDirection.INSUFFICIENT_EVIDENCE:
            confidence = VerificationConfidence.LOW
        elif semantic_matches:
            confidence = VerificationConfidence.MEDIUM
        else:
            confidence = VerificationConfidence.HIGH

        # 9. Assemble container
        dimensions = CSRDimensionsComparison(
            wash_focus=wash_focus_comp,
            projects=project_comp,
            spending=spending_comp,
            geography=geography_comp,
            beneficiaries=beneficiary_comp,
            commitments=commitment_comp,
            csr_policy=policy_comp,
        )

        return CSRChangeDetectionResult(
            company=curr.company or prev.company,
            previous_document=prev_hdr,
            current_document=curr_hdr,
            comparison_period=comparison_period,
            dimensions=dimensions,
            overall_wash_direction=overall_wash_dir,
            changes=changes,
            evidence=all_evidence,
            confidence=confidence,
            verification_metadata={
                "version_separation_preserved": True,
                "deterministic_metrics_evaluated": len(spending_comp.metrics),
                "semantic_matches_evaluated": len(semantic_matches),
                "chromadb_evidence_count": len(chroma_evidence),
            },
        )
