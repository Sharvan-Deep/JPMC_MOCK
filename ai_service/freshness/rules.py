"""
Deterministic Freshness Decision Rules for Task 10: CSR Freshness System.

Decouples:
1. Data Age (Reporting period / Financial Year recency)
2. Verification Status (Current cycle verification vs unverified/older check)
3. WASH Direction (Strategic trajectory from Task 9)

Implements exact rules:
- RED: Verified current evidence confirms company moved away from WASH (LOST_FOCUS).
       NEVER assign RED merely because information is old or missing.
- GREEN: Verified in current cycle against latest available disclosure AND evidence confirms WASH active.
- YELLOW: Older financial year, unverified current cycle, missing document, or insufficient evidence.
"""

from typing import Optional, Tuple
from ai_service.schemas.freshness import FreshnessStatus
from ai_service.schemas.verification import WASHDirection


class FreshnessRulesEngine:
    """Pure, deterministic evaluation rules for CSR/WASH freshness classification."""

    @staticmethod
    def evaluate(
        is_verified_current_cycle: bool,
        is_current_reporting_cycle: bool,
        wash_direction: Optional[WASHDirection],
        has_wash_evidence: bool,
        document_available: bool = True,
        is_insufficient_evidence: bool = False,
    ) -> Tuple[FreshnessStatus, str]:
        """
        Evaluates company freshness status and generates a deterministic reason.

        Returns (FreshnessStatus, reason_str).
        """
        # Rule 1: Verified evidence of lost WASH focus -> RED
        if wash_direction == WASHDirection.LOST_FOCUS:
            return (
                FreshnessStatus.RED,
                "Latest verified disclosure provides evidence that company has discontinued/lost WASH focus.",
            )

        # Rule 2: Document is missing for current period -> YELLOW (NOT RED)
        if not document_available:
            return (
                FreshnessStatus.YELLOW,
                "Current reporting cycle document is unavailable; cannot confirm continuation of WASH priorities.",
            )

        # Rule 3: Insufficient evidence in verification -> YELLOW (NOT RED)
        if is_insufficient_evidence or wash_direction == WASHDirection.INSUFFICIENT_EVIDENCE:
            return (
                FreshnessStatus.YELLOW,
                "Verification yielded insufficient evidence to confirm active WASH focus; requires re-verification.",
            )

        # Rule 4: Verified in current cycle, current reporting year, and active WASH confirmed -> GREEN
        if (
            is_verified_current_cycle
            and is_current_reporting_cycle
            and has_wash_evidence
            and wash_direction in (WASHDirection.INCREASED, WASHDirection.STABLE, WASHDirection.NEW_FOCUS, WASHDirection.MIXED)
        ):
            direction_label = wash_direction.value.lower() if wash_direction else "active"
            return (
                FreshnessStatus.GREEN,
                f"Information verified in current cycle against latest disclosure; WASH relevance confirmed ({direction_label}).",
            )

        # Rule 5: Information is older (prior financial year) without newer verification -> YELLOW (NOT RED)
        if not is_current_reporting_cycle:
            return (
                FreshnessStatus.YELLOW,
                "Information is based on an older financial year; latest cycle disclosure has not yet been verified.",
            )

        # Rule 6: Document retrieved but not yet verified in current cycle -> YELLOW
        if not is_verified_current_cycle:
            return (
                FreshnessStatus.YELLOW,
                "Document retrieved for current period but has not yet completed current-cycle verification.",
            )

        # Rule 7: Fallback for unverified or neutral states -> YELLOW
        return (
            FreshnessStatus.YELLOW,
            "Awaiting re-verification or supplemental evidence under current cycle.",
        )
