"""Live execution diagnostics kept outside immutable selected-run assessment."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.types import RunID
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)


def active_run_diagnostics(
    host: _HealthObservabilityRoutingHost, pipeline: str, run_id: str
) -> dict[str, object] | None:
    """Resolve an active run without confusing missing finalization with missing identity."""
    if host._run_manifest_port is None:
        return None
    selected_id = cast(RunID, UUID(run_id))
    manifest = host._run_manifest_port.get_by_run_id(selected_id)
    if manifest is None:
        return None
    if pipeline not in {
        manifest.pipeline_name,
        ".*",
        "All",
        "all",
        "*",
        "$__all",
        "__all",
    }:
        return {"verdict": "ERROR", "reason": "identity_mismatch"}
    entries = (
        host._run_ledger_port.list_entries_by_run_id(selected_id)
        if host._run_ledger_port
        else []
    )
    entries = [entry for entry in entries if entry.manifest_id == manifest.manifest_id]
    if not entries:
        return {"verdict": "INCOMPLETE", "reason": "ledger_missing"}
    if any(entry.occurred_at.utcoffset() is None for entry in entries):
        raise ValueError("ledger_timestamp_timezone_missing")
    latest = max(entries, key=lambda entry: entry.occurred_at)
    terminal = any(
        entry.event_type in {"run_finished", "run_failed", "run_shutdown"}
        for entry in entries
    )
    age = (current_utc_time() - latest.occurred_at).total_seconds()
    return {
        "verdict": "INCOMPLETE" if terminal else "RUNNING",
        "reason": "finalization_missing" if terminal else "active_run",
        "execution_state": "TERMINAL" if terminal else "RUNNING",
        "heartbeat_now": "STALE" if age > 900 else "RECENT LEDGER EVENT",
        "heartbeat_age_seconds": max(0, age),
        "run_type": manifest.run_type.value,
        "workflow_id": manifest.workflow_name,
        "pipeline": manifest.pipeline_name,
        "run_id": run_id,
    }


def scope_matches(payload: dict[str, object], query: dict[str, str]) -> bool:
    """A changed pipeline/workflow/run-type must never silently retain a foreign run."""
    for selector, field in (("run_type", "run_type"), ("workflow", "workflow_id")):
        selection = query.get(selector, "")
        if selection in {"", "All", "all", ".*", "$__all", "__all", "*"}:
            continue
        if payload.get(field) not in selection.split(","):
            return False
    return True
