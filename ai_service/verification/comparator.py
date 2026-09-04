"""
Deterministic Comparator for Task 9: CSR Verification & Change Detection.

Calculates deterministic differences for:
- Financial values (total CSR, WASH, water, sanitation) and percentage changes
- Geography sets (new, removed, continuing states and districts)
- Exact project name matches (new, discontinued, continuing)
- Beneficiary counts and demographic groups
- Multi-year commitments and recurring programs
- CSR policy strategic priorities
- Baseline WASH focus direction
"""

from typing import Dict, List, Optional, Set, Tuple
from ai_service.schemas.verification import (
    BeneficiaryComparison,
    ChangeCategory,
    CommitmentComparison,
    CSRChangeItem,
    CSRDocumentProfile,
    CSREvidenceReference,
    CSRProjectSnapshot,
    GeographyComparison,
    PolicyComparison,
    ProjectComparison,
    ProjectSemanticMatch,
    SpendingComparison,
    SpendingComparisonItem,
    WASHDirection,
    WASHFocusComparison,
)


def _build_evidence_ref(
    profile: Optional[CSRDocumentProfile],
    page: Optional[int] = None,
    source_text: Optional[str] = None,
) -> Optional[CSREvidenceReference]:
    """Helper to construct a CSREvidenceReference from a profile and page."""
    if not profile:
        return None
    return CSREvidenceReference(
        company=profile.company,
        financial_year=profile.financial_year,
        document_type=profile.document_type,
        document_version=profile.document_version,
        page=page,
        source_url=profile.source_url,
        relevant_source_text=source_text,
        document_hash=profile.document_hash,
    )


class DeterministicComparator:
    """Performs rigorous, repeatable, deterministic comparisons between two CSR profiles."""

    @staticmethod
    def calculate_numeric_change(
        prev_val: Optional[float], curr_val: Optional[float]
    ) -> Tuple[Optional[float], Optional[float], ChangeCategory]:
        """
        Calculates absolute delta and percentage change without hallucination.

        Returns (absolute_change, percentage_change, change_type).
        """
        if prev_val is None and curr_val is None:
            return None, None, ChangeCategory.INSUFFICIENT_EVIDENCE

        if prev_val is None and curr_val is not None:
            return round(curr_val, 4), None, ChangeCategory.NEW

        if prev_val is not None and curr_val is None:
            return None, None, ChangeCategory.DISCONTINUED

        # Both values are present
        abs_change = round(curr_val - prev_val, 4)
        if prev_val == 0:
            pct_change = 100.0 if curr_val > 0 else (0.0 if curr_val == 0 else -100.0)
        else:
            pct_change = round(((curr_val - prev_val) / abs(prev_val)) * 100.0, 2)

        if abs_change > 0:
            change_type = ChangeCategory.INCREASED
        elif abs_change < 0:
            change_type = ChangeCategory.DECREASED
        else:
            change_type = ChangeCategory.UNCHANGED

        return abs_change, pct_change, change_type

    def compare_spending(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> SpendingComparison:
        """Compares spending across total CSR, WASH, water, and sanitation."""
        metrics: List[SpendingComparisonItem] = []
        evidence_list: List[CSREvidenceReference] = []

        # Previous and current evidence anchors
        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("spending"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("spending"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        spend_fields = [
            ("total_csr_expenditure", prev.total_csr_spend_crore, curr.total_csr_spend_crore),
            ("wash_expenditure", prev.wash_spend_crore, curr.wash_spend_crore),
            ("water_expenditure", prev.water_spend_crore, curr.water_spend_crore),
            ("sanitation_expenditure", prev.sanitation_spend_crore, curr.sanitation_spend_crore),
        ]

        overall_change = ChangeCategory.UNCHANGED
        for metric_name, prev_val, curr_val in spend_fields:
            abs_chg, pct_chg, chg_type = self.calculate_numeric_change(prev_val, curr_val)
            item = SpendingComparisonItem(
                metric=metric_name,
                previous_value=prev_val,
                current_value=curr_val,
                absolute_change=abs_chg,
                percentage_change=pct_chg,
                unit="INR Crores",
                change_type=chg_type,
                evidence=base_ev,
            )
            metrics.append(item)
            if metric_name == "wash_expenditure" and chg_type != ChangeCategory.INSUFFICIENT_EVIDENCE:
                overall_change = chg_type
            elif metric_name == "total_csr_expenditure" and overall_change == ChangeCategory.UNCHANGED:
                overall_change = chg_type

        # Project level spending changes for exact matched projects
        proj_spend_changes: List[SpendingComparisonItem] = []
        prev_proj_map = {p.project_name.lower().strip(): p for p in prev.projects if p.amount_spent_inr_crore is not None}
        for curr_proj in curr.projects:
            c_key = curr_proj.project_name.lower().strip()
            if c_key in prev_proj_map and curr_proj.amount_spent_inr_crore is not None:
                p_proj = prev_proj_map[c_key]
                p_val = p_proj.amount_spent_inr_crore
                c_val = curr_proj.amount_spent_inr_crore
                abs_chg, pct_chg, chg_type = self.calculate_numeric_change(p_val, c_val)
                proj_spend_changes.append(
                    SpendingComparisonItem(
                        metric=f"project:{curr_proj.project_name}",
                        previous_value=p_val,
                        current_value=c_val,
                        absolute_change=abs_chg,
                        percentage_change=pct_chg,
                        unit="INR Crores",
                        change_type=chg_type,
                        evidence=[
                            e for e in (
                                _build_evidence_ref(prev, page=p_proj.page_number),
                                _build_evidence_ref(curr, page=curr_proj.page_number),
                            ) if e is not None
                        ],
                    )
                )

        return SpendingComparison(
            metrics=metrics,
            project_spending_changes=proj_spend_changes,
            overall_change_type=overall_change,
            evidence=base_ev,
        )

    def compare_geography(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> GeographyComparison:
        """Calculates set differences for states and districts."""
        prev_states = {s.strip().title() for s in prev.states if s and s.strip()}
        curr_states = {s.strip().title() for s in curr.states if s and s.strip()}

        prev_districts = {d.strip().title() for d in prev.districts if d and d.strip()}
        curr_districts = {d.strip().title() for d in curr.districts if d and d.strip()}

        new_states = sorted(list(curr_states - prev_states))
        removed_states = sorted(list(prev_states - curr_states))
        continuing_states = sorted(list(curr_states & prev_states))

        new_districts = sorted(list(curr_districts - prev_districts))
        removed_districts = sorted(list(prev_districts - curr_districts))

        # Evidence
        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("geography"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("geography"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        if not prev_states and not curr_states and not prev_districts and not curr_districts:
            direction = ChangeCategory.INSUFFICIENT_EVIDENCE
        elif (new_states or new_districts) and not (removed_states or removed_districts):
            direction = ChangeCategory.EXPANDED
        elif (removed_states or removed_districts) and not (new_states or new_districts):
            direction = ChangeCategory.CONTRACTED
        elif (new_states or new_districts) and (removed_states or removed_districts):
            direction = ChangeCategory.CHANGED_DIRECTION
        else:
            direction = ChangeCategory.UNCHANGED

        return GeographyComparison(
            new_locations=new_states,
            removed_locations=removed_states,
            continuing_locations=continuing_states,
            new_districts=new_districts,
            removed_districts=removed_districts,
            direction=direction,
            evidence=base_ev,
        )

    def match_exact_projects(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> Tuple[List[CSRProjectSnapshot], List[CSRProjectSnapshot], List[Tuple[CSRProjectSnapshot, CSRProjectSnapshot]]]:
        """
        Partitions projects into:
        - unmatched previous projects (candidates for discontinuation or semantic matching)
        - unmatched current projects (candidates for new or semantic matching)
        - exact continuing matches (prev_snapshot, curr_snapshot)
        """
        def _norm(name: str) -> str:
            return "".join(c.lower() for c in name if c.isalnum() or c.isspace()).strip()

        prev_by_norm = {_norm(p.project_name): p for p in prev.projects}
        curr_by_norm = {_norm(p.project_name): p for p in curr.projects}

        matched_norms = set(prev_by_norm.keys()) & set(curr_by_norm.keys())

        continuing = [(prev_by_norm[k], curr_by_norm[k]) for k in matched_norms]
        unmatched_prev = [prev_by_norm[k] for k in prev_by_norm if k not in matched_norms]
        unmatched_curr = [curr_by_norm[k] for k in curr_by_norm if k not in matched_norms]

        return unmatched_prev, unmatched_curr, continuing

    def compare_beneficiaries(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> BeneficiaryComparison:
        """Compares target beneficiary demographics and reported counts."""
        prev_groups = {g.strip() for g in prev.beneficiary_groups if g and g.strip()}
        curr_groups = {g.strip() for g in curr.beneficiary_groups if g and g.strip()}

        new_groups = sorted(list(curr_groups - prev_groups))
        removed_groups = sorted(list(prev_groups - curr_groups))

        prev_count = prev.beneficiary_count
        curr_count = curr.beneficiary_count

        abs_chg, pct_chg, chg_type = self.calculate_numeric_change(
            float(prev_count) if prev_count is not None else None,
            float(curr_count) if curr_count is not None else None,
        )

        int_abs_chg = int(abs_chg) if abs_chg is not None else None

        if chg_type == ChangeCategory.INSUFFICIENT_EVIDENCE:
            if new_groups and not removed_groups:
                chg_type = ChangeCategory.EXPANDED
            elif removed_groups and not new_groups:
                chg_type = ChangeCategory.CONTRACTED
            elif new_groups and removed_groups:
                chg_type = ChangeCategory.CHANGED_DIRECTION
            elif prev_groups and curr_groups:
                chg_type = ChangeCategory.UNCHANGED

        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("beneficiaries"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("beneficiaries"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        return BeneficiaryComparison(
            previous_groups=sorted(list(prev_groups)),
            current_groups=sorted(list(curr_groups)),
            new_groups=new_groups,
            removed_groups=removed_groups,
            previous_count=prev_count,
            current_count=curr_count,
            count_absolute_change=int_abs_chg,
            count_percentage_change=pct_chg,
            target_communities_change=None,
            change_type=chg_type,
            evidence=base_ev,
        )

    def compare_commitments(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> CommitmentComparison:
        """Evaluates multi-year commitments, ongoing programs, and recurring initiatives."""
        def _set(items: List[str]) -> Set[str]:
            return {i.strip().lower() for i in items if i and i.strip()}

        prev_commitments = _set(prev.multi_year_commitments)
        curr_commitments = _set(curr.multi_year_commitments)

        # Multi-year projects can also be inferred from project snapshots
        prev_my_projs = {p.project_name.lower().strip() for p in prev.projects if p.is_multi_year}
        curr_my_projs = {p.project_name.lower().strip() for p in curr.projects if p.is_multi_year}

        all_prev_comm = prev_commitments | prev_my_projs
        all_curr_comm = curr_commitments | curr_my_projs

        continued = sorted(list(all_prev_comm & all_curr_comm))
        new_comm = sorted(list(all_curr_comm - all_prev_comm))
        completed = sorted(list(all_prev_comm - all_curr_comm))

        ongoing_list = sorted(list(_set(curr.ongoing_projects) | curr_my_projs))
        recurring_list = sorted(list(_set(curr.recurring_programs)))
        plans_list = list(curr.stated_future_plans)

        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("commitments"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("commitments"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        if not all_prev_comm and not all_curr_comm and not ongoing_list:
            chg_type = ChangeCategory.INSUFFICIENT_EVIDENCE
        elif continued:
            chg_type = ChangeCategory.CONTINUED
        elif new_comm:
            chg_type = ChangeCategory.NEW
        elif completed:
            chg_type = ChangeCategory.DISCONTINUED
        else:
            chg_type = ChangeCategory.UNCHANGED

        return CommitmentComparison(
            continued_commitments=continued,
            new_commitments=new_comm,
            completed_commitments=completed,
            ongoing_projects=ongoing_list,
            recurring_programs=recurring_list,
            stated_future_plans=plans_list,
            change_type=chg_type,
            evidence=base_ev,
        )

    def compare_policy(
        self, prev: CSRDocumentProfile, curr: CSRDocumentProfile
    ) -> PolicyComparison:
        """Detects strategic CSR policy shifts and WASH priority status."""
        prev_p = {p.strip() for p in prev.policy_priorities if p and p.strip()}
        curr_p = {p.strip() for p in curr.policy_priorities if p and p.strip()}

        added = sorted(list(curr_p - prev_p))
        removed = sorted(list(prev_p - curr_p))
        unchanged = sorted(list(curr_p & prev_p))

        # Check for WASH in policy
        wash_keywords = {"water", "sanitation", "hygiene", "wash", "drinking water"}
        has_wash_prev = any(any(k in p.lower() for k in wash_keywords) for p in prev_p)
        has_wash_curr = any(any(k in p.lower() for k in wash_keywords) for p in curr_p)

        if not has_wash_prev and has_wash_curr:
            wash_status = "WASH newly introduced as strategic priority in CSR policy"
        elif has_wash_prev and not has_wash_curr:
            wash_status = "WASH removed or de-emphasized from stated strategic policy priorities"
        elif has_wash_prev and has_wash_curr:
            wash_status = "WASH maintained as strategic CSR policy priority"
        else:
            wash_status = "No explicit WASH focus stated in CSR policy priorities"

        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("policy"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("policy"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        if not prev_p and not curr_p:
            chg_type = ChangeCategory.INSUFFICIENT_EVIDENCE
        elif added and not removed:
            chg_type = ChangeCategory.EXPANDED
        elif removed and not added:
            chg_type = ChangeCategory.CONTRACTED
        elif added and removed:
            chg_type = ChangeCategory.CHANGED_DIRECTION
        else:
            chg_type = ChangeCategory.UNCHANGED

        return PolicyComparison(
            added_priorities=added,
            removed_priorities=removed,
            strengthened_priorities=[],
            reduced_priorities=[],
            unchanged_priorities=unchanged,
            wash_priority_status=wash_status,
            change_type=chg_type,
            evidence=base_ev,
        )

    def determine_wash_focus_and_direction(
        self,
        prev: CSRDocumentProfile,
        curr: CSRDocumentProfile,
        spending_comp: SpendingComparison,
        project_comp: ProjectComparison,
    ) -> Tuple[WASHFocusComparison, WASHDirection]:
        """
        Determines WASH focus shifts and synthesizes the overall WASH direction.

        Matrix:
        - No evidence anywhere -> INSUFFICIENT_EVIDENCE
        - Prev had NO wash, Curr HAS wash -> NEW_FOCUS
        - Prev HAD wash, Curr has NO wash -> LOST_FOCUS
        - Both have wash:
            - Spending increased & projects steady/up -> INCREASED
            - Spending decreased & projects dropped -> DECREASED
            - Mixed indicators (e.g. spend up, areas dropped) -> MIXED
            - Equal / steady -> STABLE
        - Neither had wash -> STABLE (unfocused)
        """
        prev_focus = set(prev.wash_focus_areas)
        curr_focus = set(curr.wash_focus_areas)

        added_f = sorted(list(curr_focus - prev_focus))
        removed_f = sorted(list(prev_focus - curr_focus))
        retained_f = sorted(list(prev_focus & curr_focus))

        # Check evidence of WASH activity
        prev_wash_projs = [p for p in prev.projects if p.is_wash]
        curr_wash_projs = [p for p in curr.projects if p.is_wash]

        prev_has_wash = bool(
            prev.has_wash_activity is True
            or (prev.wash_spend_crore is not None and prev.wash_spend_crore > 0)
            or prev_wash_projs
            or prev_focus
        )
        curr_has_wash = bool(
            curr.has_wash_activity is True
            or (curr.wash_spend_crore is not None and curr.wash_spend_crore > 0)
            or curr_wash_projs
            or curr_focus
        )

        # Check if there is literally zero information
        evidence_present = (
            prev.total_csr_spend_crore is not None
            or curr.total_csr_spend_crore is not None
            or prev.projects
            or curr.projects
            or prev.wash_focus_areas
            or curr.wash_focus_areas
            or prev.has_wash_activity is not None
            or curr.has_wash_activity is not None
        )

        prev_ev = _build_evidence_ref(prev, page=prev.raw_evidence_pages.get("wash"))
        curr_ev = _build_evidence_ref(curr, page=curr.raw_evidence_pages.get("wash"))
        base_ev = [e for e in (prev_ev, curr_ev) if e is not None]

        if not evidence_present:
            direction = WASHDirection.INSUFFICIENT_EVIDENCE
        elif not prev_has_wash and curr_has_wash:
            direction = WASHDirection.NEW_FOCUS
        elif prev_has_wash and not curr_has_wash:
            direction = WASHDirection.LOST_FOCUS
        elif prev_has_wash and curr_has_wash:
            # Both have WASH activity -> assess trajectory
            wash_spend_item = next(
                (m for m in spending_comp.metrics if m.metric == "wash_expenditure"), None
            )
            spend_chg = wash_spend_item.change_type if wash_spend_item else ChangeCategory.UNCHANGED

            new_wash_projs = [p for p in curr_wash_projs if p.project_name in project_comp.new_projects]
            disc_wash_projs = [p for p in prev_wash_projs if p.project_name in project_comp.discontinued_projects]

            if spend_chg == ChangeCategory.INCREASED or (new_wash_projs and not disc_wash_projs):
                direction = WASHDirection.INCREASED
            elif spend_chg == ChangeCategory.DECREASED or (disc_wash_projs and not new_wash_projs):
                direction = WASHDirection.DECREASED
            elif (new_wash_projs and disc_wash_projs) or (spend_chg == ChangeCategory.INCREASED and removed_f):
                direction = WASHDirection.MIXED
            else:
                direction = WASHDirection.STABLE
        else:
            # Neither had WASH activity
            direction = WASHDirection.STABLE

        wash_focus_comp = WASHFocusComparison(
            previous_focus=sorted(list(prev_focus)),
            current_focus=sorted(list(curr_focus)),
            added_focus=added_f,
            removed_focus=removed_f,
            retained_focus=retained_f,
            direction=direction,
            evidence=base_ev,
        )

        return wash_focus_comp, direction
