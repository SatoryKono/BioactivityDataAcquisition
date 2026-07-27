"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.artifact_support import (
    apply_artifact_publication_closure_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base import (
    _build_base_summary_payload,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    attach_base_summary_runtime_views as _attach_base_summary_runtime_views,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    attach_summary_reproducibility_views as _attach_summary_reproducibility_views,
)
from bioetl.application.services.control_plane.manifest.diagnostics.finalization import (
    build_final_diagnostics_summary as _build_final_diagnostics_summary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support import (
    _refresh_replay_summary_from_materialized_snapshots,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    replay_context = _resolve_base_summary_replay_context(manifest)
    summary = _build_base_summary_payload(manifest, replay_context)
    _attach_base_summary_runtime_views(manifest, summary)
    return summary


def build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    base_summary = _build_base_summary(manifest)

    if not ledger_entries:
        base_summary = apply_artifact_publication_closure_policy(base_summary)
        _attach_summary_reproducibility_views(base_summary)
        return base_summary
    return _build_final_diagnostics_summary(
        manifest=manifest,
        base_summary=base_summary,
        ledger_entries=ledger_entries,
        refresh_replay_summary_fn=_refresh_replay_summary_from_materialized_snapshots,
    )


__all__ = ["build_diagnostics_summary"]
