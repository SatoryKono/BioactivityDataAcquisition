"""Stable payload models for run-scoped control-plane validation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.control_plane import RunManifest

EvidenceStatus = Literal["OK", "WARNING", "ERROR", "UNKNOWN"]
CONTROL_PLANE_EVIDENCE_CONTRACT = "control_plane_validation_evidence_v1"

_STATUS_PRIORITY: dict[EvidenceStatus, int] = {
    "OK": 0,
    "UNKNOWN": 1,
    "WARNING": 2,
    "ERROR": 3,
}


@dataclass(frozen=True, slots=True)
class EvidenceCheck:
    """One bounded validation result suitable for an operator table."""

    check: str
    status: EvidenceStatus
    reason: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe table row."""
        return {
            "check": self.check,
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
        }


def evidence_payload(
    *,
    endpoint: str,
    checks: tuple[EvidenceCheck, ...],
    requested_pipeline: str,
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
    manifest: RunManifest | None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the shared bounded response envelope for validation endpoints."""
    status = max(
        (check.status for check in checks),
        key=_STATUS_PRIORITY.__getitem__,
        default="UNKNOWN",
    )
    counts = {
        value: sum(check.status == value for check in checks)
        for value in ("OK", "WARNING", "ERROR", "UNKNOWN")
    }
    payload: dict[str, object] = {
        "contract": CONTROL_PLANE_EVIDENCE_CONTRACT,
        "endpoint": endpoint,
        "status": status,
        "pipeline": (
            manifest.pipeline_name if manifest is not None else requested_pipeline
        ),
        "run_type": (
            manifest.run_type.value
            if manifest is not None
            else (selected_run_types[0] if len(selected_run_types) == 1 else None)
        ),
        "run_id": str(manifest.run_id) if manifest is not None else selected_run_id,
        "manifest_id": manifest.manifest_id if manifest is not None else None,
        "resolved_via": resolved_via,
        "summary": {
            "check_count": len(checks),
            "ok_count": counts["OK"],
            "warning_count": counts["WARNING"],
            "error_count": counts["ERROR"],
            "unknown_count": counts["UNKNOWN"],
        },
        "rows": [check.to_dict() for check in checks],
    }
    if extra:
        payload.update(extra)
    return payload


def unresolved_scope_check(resolved_via: str) -> EvidenceCheck:
    """Return an explicit non-fabricated result for an unresolved run scope."""
    reason = (
        "selected_run_id_not_found"
        if resolved_via == "selected_run_id_not_found"
        else "manifest_not_found_for_scope"
    )
    return EvidenceCheck(
        check="scope_resolution",
        status="UNKNOWN",
        reason=reason,
        detail="No persisted run manifest resolved for the requested scope.",
    )


__all__ = [
    "CONTROL_PLANE_EVIDENCE_CONTRACT",
    "EvidenceCheck",
    "EvidenceStatus",
    "evidence_payload",
    "unresolved_scope_check",
]
