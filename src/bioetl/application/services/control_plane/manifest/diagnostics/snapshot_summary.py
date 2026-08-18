"""Input-snapshot summary merge helpers for manifest diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_ledger import (
    collect_ledger_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_refs import (
    collect_input_snapshot_content_hashes,
    collect_input_snapshot_ids,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.control_plane import RunLedgerEntry


def _index_existing_snapshots(
    snapshots: object,
) -> dict[str, dict[str, object]]:
    """Index well-formed existing snapshot mappings by snapshot ID."""
    if not isinstance(snapshots, list):
        return {}
    return {
        str(snapshot["snapshot_id"]): dict(snapshot)
        for snapshot in snapshots
        if isinstance(snapshot, Mapping) and snapshot.get("snapshot_id") is not None
    }


def _merge_ledger_snapshots_by_id(
    snapshots_by_id: dict[str, dict[str, object]],
    ledger_snapshots: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Merge ledger snapshots without silently replacing divergent hashes."""
    conflicts: list[dict[str, object]] = []
    for snapshot in ledger_snapshots:
        snapshot_id = str(snapshot["snapshot_id"])
        existing = snapshots_by_id.get(snapshot_id)
        if existing is None:
            snapshots_by_id[snapshot_id] = snapshot
            continue
        existing_hash = existing.get("content_hash")
        ledger_hash = snapshot.get("content_hash")
        if existing_hash == ledger_hash:
            continue
        conflicts.append(
            {
                "snapshot_id": snapshot_id,
                "manifest_content_hash": existing_hash,
                "ledger_content_hash": ledger_hash,
            }
        )
    return conflicts


def merge_ledger_input_snapshots_into_summary(
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Merge ledger-derived input snapshots into diagnostics without mutating manifest."""
    ledger_snapshots = collect_ledger_input_snapshot_refs(ledger_entries)
    if not ledger_snapshots:
        return summary
    merged = dict(summary)
    snapshots_by_id = _index_existing_snapshots(merged.get("input_snapshots", []))
    identity_conflicts = _merge_ledger_snapshots_by_id(
        snapshots_by_id,
        ledger_snapshots,
    )
    input_snapshots = [snapshots_by_id[key] for key in sorted(snapshots_by_id)]
    merged["input_snapshots"] = input_snapshots
    if identity_conflicts:
        merged["input_snapshot_identity_conflicts"] = identity_conflicts
    merged["input_snapshot_count"] = len(input_snapshots)
    merged["input_snapshot_ids"] = collect_input_snapshot_ids(input_snapshots)
    merged["input_snapshot_content_hashes"] = collect_input_snapshot_content_hashes(
        input_snapshots
    )
    merged["input_snapshot_identity_fingerprint"] = (
        compute_input_snapshot_identity_fingerprint(input_snapshots)
    )
    merged["input_snapshot_materialization_mode"] = (
        resolve_post_manifest_input_snapshot_materialization_mode(input_snapshots)
    )
    if merged.get("source_posture") == "live_or_unknown_inputs":
        merged["source_posture"] = str(
            merged.get("input_snapshot_materialization_mode") or "ledger_derived"
        )
    if merged.get("snapshot_status") == "none":
        merged["snapshot_status"] = "ledger_derived"
    return merged


__all__ = [
    "merge_ledger_input_snapshots_into_summary",
    "resolve_post_manifest_input_snapshot_materialization_mode",
]
