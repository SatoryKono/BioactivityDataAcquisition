"""Operator-facing aliases for control-plane reason codes."""

from __future__ import annotations

REASON_ALIASES: dict[str, str] = {
    "archive_evidence_not_recorded": "Archive missing",
    "archive_restore_verified": "Archive verified",
    "archive_not_applicable": "N/A: policy",
    "reproducibility_evidence_floor_satisfied": "Evidence floor met",
    "reproducibility_evidence_within_retention": "Within retention",
    "snapshot_evidence_not_required": "Snapshots not required",
    "snapshot_lifecycle_evidence_incomplete": "Snapshot incomplete",
    "snapshot_lifecycle_evidence_present": "Snapshots present",
    "required_evidence_surfaces_present": "Evidence present",
    "retention_policy_satisfied": "Retained by policy",
    "lineage_closure_gap": "Lineage closure gap",
    "lineage_closure_complete": "Lineage closed",
    "selected_run_id_not_found": "Run not found",
    "deadline_exceeded": "Deadline exceeded",
    "capacity_exhausted": "At capacity",
}


def display_reason(code: str) -> str:
    """Return the operator alias, or the original code when unmapped."""
    token = code.strip()
    if not token:
        return code
    return REASON_ALIASES.get(token, token)


def display_reasons_text(text: str) -> str:
    """Map each newline-separated reason code; preserve blank lines."""
    return "\n".join(
        display_reason(part) if part.strip() else part for part in text.split("\n")
    )
