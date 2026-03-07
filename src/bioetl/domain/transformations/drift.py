"""Schema drift detection transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.2 — Schema Drift Detection.
REQ-SCHEMA-001..004.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

from ..types import DriftLevel


def detect_schema_drift(
    old_schema: set[str],
    new_schema: set[str],
    required_fields: set[str] | None = None,
) -> tuple[DriftLevel, JsonDict]:
    """Detect schema drift between two schemas.

    Args:
        old_schema: Set of field names in the previous schema version.
        new_schema: Set of field names in the current schema version.
        required_fields: Set of fields that must not be removed (triggers CRITICAL drift).

    Returns:
        Tuple of (drift_level, details_dict) with added/removed fields info.
    """
    added = sorted(new_schema - old_schema)
    removed = sorted(old_schema - new_schema)
    missing_required = sorted((required_fields or set()) & set(removed))

    level = DriftLevel.INFO
    if missing_required:
        level = DriftLevel.CRITICAL

    details: JsonDict = {
        "added_fields": added,
        "removed_fields": removed,
        "field_count_delta": len(added) - len(removed),
    }
    if missing_required:
        details["missing_required"] = missing_required

    return level, details
