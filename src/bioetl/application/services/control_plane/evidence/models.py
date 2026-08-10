"""Stable payload models for run-scoped control-plane validation evidence."""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence.types import (
    EvidenceCheck,
    EvidenceStatus,
)
from bioetl.domain.control_plane import RunManifest

CONTROL_PLANE_EVIDENCE_CONTRACT = "control_plane_validation_evidence_v1"

_STATUS_PRIORITY: dict[EvidenceStatus, int] = {
    "OK": 0,
    "UNKNOWN": 1,
    "WARNING": 2,
    "ERROR": 3,
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
    additional_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the shared bounded response envelope for validation endpoints."""
    counts = _status_counts(checks)
    pipeline, run_type, run_id, manifest_id = _scope_identity(
        manifest=manifest,
        requested_pipeline=requested_pipeline,
        selected_run_types=selected_run_types,
        selected_run_id=selected_run_id,
    )
    payload: dict[str, object] = {
        "contract": CONTROL_PLANE_EVIDENCE_CONTRACT,
        "endpoint": endpoint,
        "status": _overall_status(checks),
        "pipeline": pipeline,
        "run_type": run_type,
        "run_id": run_id,
        "manifest_id": manifest_id,
        "resolved_via": resolved_via,
        "summary": _summary(checks, counts),
        "rows": [check.to_dict() for check in checks],
    }
    if additional_fields:
        payload.update(additional_fields)
    return payload


def _overall_status(checks: tuple[EvidenceCheck, ...]) -> EvidenceStatus:
    if not checks:
        return "UNKNOWN"
    return max(checks, key=lambda check: _STATUS_PRIORITY[check.status]).status


def _status_counts(checks: tuple[EvidenceCheck, ...]) -> dict[str, int]:
    return {
        value: sum(check.status == value for check in checks)
        for value in ("OK", "WARNING", "ERROR", "UNKNOWN")
    }


def _scope_identity(
    *,
    manifest: RunManifest | None,
    requested_pipeline: str,
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
) -> tuple[str, str | None, str | None, str | None]:
    if manifest is not None:
        return (
            manifest.pipeline_name,
            manifest.run_type.value,
            str(manifest.run_id),
            manifest.manifest_id,
        )
    run_type = selected_run_types[0] if len(selected_run_types) == 1 else None
    return requested_pipeline, run_type, selected_run_id, None


def _summary(
    checks: tuple[EvidenceCheck, ...],
    counts: dict[str, int],
) -> dict[str, int]:
    return {
        "check_count": len(checks),
        "ok_count": counts["OK"],
        "warning_count": counts["WARNING"],
        "error_count": counts["ERROR"],
        "unknown_count": counts["UNKNOWN"],
    }


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
