"""Composite-run projection helpers for manifest diagnostics."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)


class _CompositeSummaryRequest(Protocol):
    """Subset of final summary request fields needed for composite projection."""

    @property
    def manifest(self) -> RunManifest: ...

    @property
    def ledger_entries(self) -> tuple[RunLedgerEntry, ...]: ...

    @property
    def correlation_anchor_gaps(self) -> dict[str, int]: ...

    @property
    def resume_diagnostics(self) -> dict[str, object] | None: ...


def _composite_run_id_from_entry(entry: RunLedgerEntry) -> object:
    details = entry.details or {}
    raw_diagnostic = details.get("_diagnostic")
    if not isinstance(raw_diagnostic, dict):
        return None
    return raw_diagnostic.get("composite_run_id")


def build_composite_dossier_projection(
    request: _CompositeSummaryRequest,
    *,
    persistence_profile: dict[str, object],
) -> dict[str, object]:
    """Return a bounded composite-run projection for operator dossiers."""
    composite_run_ids = sorted(
        {
            str(composite_run_id)
            for entry in request.ledger_entries
            if (composite_run_id := _composite_run_id_from_entry(entry)) is not None
        }
    )
    composite_gap_count = request.correlation_anchor_gaps.get("composite_run_id", 0)
    is_composite_run = (
        _is_composite_execution_context(request.manifest)
        or bool(composite_run_ids)
        or composite_gap_count > 0
    )
    return {
        "is_composite_run": is_composite_run,
        "primary_composite_run_id": (
            composite_run_ids[0] if len(composite_run_ids) == 1 else None
        ),
        "composite_run_ids": composite_run_ids,
        "composite_run_id_consistent": len(composite_run_ids) <= 1
        and composite_gap_count == 0,
        "correlation_policy": {
            "required_anchor": "composite_run_id",
            "required_event_families": ["checkpoint", "composite"],
            "semantic_anchor": "execution_fingerprint",
            "occurrence_anchor": "run_id",
            "status": "satisfied" if composite_gap_count == 0 else "gap",
        },
        "correlation_anchor_gaps": {"composite_run_id": composite_gap_count},
        "resume_diagnostics": request.resume_diagnostics,
        "resume_reconstructability": persistence_profile.get(
            "composite_resume_reconstructability"
        ),
    }
