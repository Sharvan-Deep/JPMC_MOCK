"""
Verification Cycle Management for Task 10: CSR Freshness System.

Provides deterministic verification cycle identifiers (e.g. '2026-09')
and separates retrieval timestamps from verification timestamps.
"""

from datetime import datetime, timezone
import re
from typing import Optional

CYCLE_REGEX = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


def get_current_verification_cycle() -> str:
    """Returns deterministic verification cycle ID based on current UTC month (e.g. '2026-09')."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def is_valid_cycle(cycle_id: str) -> bool:
    """Validates if cycle identifier matches YYYY-MM or structured cycle pattern."""
    if not cycle_id or not isinstance(cycle_id, str):
        return False
    return bool(CYCLE_REGEX.match(cycle_id)) or len(cycle_id.strip()) >= 4


def format_iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Generates standard ISO-8601 UTC timestamp string."""
    target_dt = dt or datetime.now(timezone.utc)
    return target_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
