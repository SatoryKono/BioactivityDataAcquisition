"""Stable payload models for run-scoped control-plane validation evidence."""

from __future__ import annotations

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
    EvidenceFreshness,
    EvidenceStatus,
    ProcessingStatus,
    ScopeKind,
    TrustStatus,
    aggregate_trust_status,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)

CONTROL_PLANE_EVIDENCE_CONTRACT = "control_plane_validation_evidence_v1"
FIRST_SCREEN_TRUST_REASONS_CAP = 3


_STATUS_PRIORITY: dict[EvidenceStatus, int] = {
    "OK": 0,
    "UNKNOWN": 1,
    "WARNING": 2,
    "ERROR": 3,
}


def evidence_payload(
    *,
    endpoint: str,
    checks: tuple[EvidenceCheckResult, ...],
    requested_pipeline: str,
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
    manifest: RunManifest | None,
    additional_fields: dict[str, object] | None = None,
    ledger_entries: tuple[RunLedgerEntry, ...] = (),
) -> dict[str, object]:
    """Build the shared bounded response envelope for validation endpoints."""
    counts = _status_counts(checks)
    pipeline, run_type, run_id, manifest_id = _scope_identity(
        manifest=manifest,
        requested_pipeline=requested_pipeline,
        selected_run_types=selected_run_types,
        selected_run_id=selected_run_id,
    )
    trust_status = aggregate_trust_status(checks)
    processing_status = _processing_status(manifest, ledger_entries)
    scope_kind = _scope_kind(resolved_via=resolved_via, manifest=manifest)
    evidence_freshness = _evidence_freshness(manifest)
    reasons = _trust_reasons(checks, trust_status)
    reasons_text, reasons_truncated = _trust_reasons_display(reasons)
    payload: dict[str, object] = {
        "contract": CONTROL_PLANE_EVIDENCE_CONTRACT,
        "endpoint": endpoint,
        "status": _overall_status(checks),
        "processing_status": processing_status,
        "trust_status": trust_status,
        "scope_kind": scope_kind,
        "evidence_freshness": evidence_freshness,
        "pipeline": pipeline,
        "run_type": run_type,
        "run_id": run_id,
        "manifest_id": manifest_id,
        "resolved_via": resolved_via,
        "summary": _summary(checks, counts),
        "trust": {
            "trust_status": trust_status,
            "processing_status": processing_status,
            "scope_kind": scope_kind,
            "evidence_freshness": evidence_freshness,
            "reasons": reasons,
            "reasons_text": reasons_text,
            "reasons_truncated": reasons_truncated,
            "evidence_observed_at": (
                manifest.created_at.isoformat() if manifest is not None else None
            ),
        },
        "rows": [check.to_dict() for check in checks],
    }
    if additional_fields:
        payload.update(additional_fields)
    return payload


def _processing_status(
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> ProcessingStatus:
    if manifest is None:
        return "unknown"
    for entry in reversed(ledger_entries):
        if entry.event_type == RUN_FINISHED_EVENT:
            return "success"
        if entry.event_type == RUN_FAILED_EVENT:
            return "failed"
        if entry.event_type == RUN_SHUTDOWN_EVENT:
            return "shutdown"
    launch_status = manifest.launch_context.get("processing_status")
    if launch_status in {"success", "failed", "shutdown"}:
        return launch_status
    return "unknown"


def _scope_kind(*, resolved_via: str, manifest: RunManifest | None) -> ScopeKind:
    if manifest is None:
        return "unresolved"
    if resolved_via in {"selected_run_id", "selected_run_id_not_found"}:
        return "exact_run" if resolved_via == "selected_run_id" else "unresolved"
    if "latest" in resolved_via or resolved_via == "pipeline_scope":
        return "pipeline_current"
    return "exact_run"


def _evidence_freshness(manifest: RunManifest | None) -> EvidenceFreshness:
    return "observed" if manifest is not None else "unknown"


def _trust_reasons(
    checks: tuple[EvidenceCheckResult, ...],
    trust_status: TrustStatus,
) -> list[str]:
    if trust_status == "OK":
        return []
    wanted: set[EvidenceStatus]
    if trust_status == "ERROR":
        wanted = {"ERROR"}
    elif trust_status == "WARNING":
        wanted = {"WARNING"}
    else:
        wanted = {"UNKNOWN"}
    return [check.reason for check in checks if check.status in wanted][:12]


def _trust_reasons_display(reasons: list[str]) -> tuple[str, bool]:
    """First-screen multiline view: top-N codes, flag if the list is longer."""
    return (
        "\n".join(reasons[:FIRST_SCREEN_TRUST_REASONS_CAP]),
        len(reasons) > FIRST_SCREEN_TRUST_REASONS_CAP,
    )


def _overall_status(checks: tuple[EvidenceCheckResult, ...]) -> EvidenceStatus:
    if not checks:
        return "UNKNOWN"
    return max(checks, key=lambda check: _STATUS_PRIORITY[check.status]).status


def _status_counts(checks: tuple[EvidenceCheckResult, ...]) -> dict[str, int]:
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
    checks: tuple[EvidenceCheckResult, ...],
    counts: dict[str, int],
) -> dict[str, int]:
    return {
        "check_count": len(checks),
        "ok_count": counts["OK"],
        "warning_count": counts["WARNING"],
        "error_count": counts["ERROR"],
        "unknown_count": counts["UNKNOWN"],
    }


def unresolved_scope_check(resolved_via: str) -> EvidenceCheckResult:
    """Return an explicit non-fabricated result for an unresolved run scope."""
    reason = (
        "selected_run_id_not_found"
        if resolved_via == "selected_run_id_not_found"
        else "manifest_not_found_for_scope"
    )
    return EvidenceCheckResult(
        check="scope_resolution",
        status="UNKNOWN",
        reason=reason,
        detail="No persisted run manifest resolved for the requested scope.",
    )


__all__ = [
    "CONTROL_PLANE_EVIDENCE_CONTRACT",
    "FIRST_SCREEN_TRUST_REASONS_CAP",
    "EvidenceCheckResult",
    "EvidenceStatus",
    "evidence_payload",
    "unresolved_scope_check",
]
