"""Diagnostics helpers for run manifest inspection service.

Static fan-in is kept off leaf modules via importlib (ARCH-REF-04 / #6818).
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunLedgerEntry, RunManifest

__all__ = ["build_diagnostics_summary"]


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    base = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics.base"
    )
    finalization = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics.finalization"
    )
    replay_context = base._resolve_base_summary_replay_context(manifest)
    summary = base._build_base_summary_payload(manifest, replay_context)
    finalization.attach_base_summary_runtime_views(manifest, summary)
    return cast(dict[str, object], summary)


def build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    artifact_support = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics.artifact_support"
    )
    finalization = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics.finalization"
    )
    replay_refresh = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics"
        ".replay_refresh_support"
    )
    base_summary = _build_base_summary(manifest)

    if not ledger_entries:
        base_summary = artifact_support.apply_artifact_publication_closure_policy(
            base_summary
        )
        finalization.attach_summary_reproducibility_views(base_summary)
        return cast(dict[str, object], base_summary)
    return cast(
        dict[str, object],
        finalization.build_final_diagnostics_summary(
            manifest=manifest,
            base_summary=base_summary,
            ledger_entries=ledger_entries,
            refresh_replay_summary_fn=(
                replay_refresh._refresh_replay_summary_from_materialized_snapshots
            ),
        ),
    )
