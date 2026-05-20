"""Nested-config and input-snapshot support helpers for replay diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane._historical_replay_certification import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
    MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION,
)
from bioetl.application.services.control_plane._run_manifest_snapshot_payloads import (
    manifest_input_snapshot_trace_refs,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT
from bioetl.domain.normalization import (
    compute_input_snapshot_identity_fingerprint as compute_snapshot_identity_fingerprint,
)


def lookup_mapping_path(
    mapping: Mapping[str, object],
    *path: str,
) -> object | None:
    """Read one nested mapping path using only mapping-shaped objects."""
    current: object = mapping
    for component in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(component)
    return current


def collect_input_snapshot_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return deterministic flattened snapshot provenance extracted from source refs."""
    return manifest_input_snapshot_trace_refs(manifest)


def collect_input_snapshot_ids(input_snapshots: list[dict[str, object]]) -> list[str]:
    """Return deterministic snapshot identities for resume/exact-replay anchors."""
    return [
        str(snapshot_id)
        for snapshot_id in (snapshot.get("snapshot_id") for snapshot in input_snapshots)
        if snapshot_id is not None
    ]


def collect_input_snapshot_content_hashes(
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return deterministic snapshot content hashes for operator inspection."""
    return [
        str(content_hash)
        for content_hash in (
            snapshot.get("content_hash") for snapshot in input_snapshots
        )
        if content_hash is not None
    ]


def compute_input_snapshot_identity_fingerprint(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Compute the same stable replay-anchor fingerprint shape used by checkpoints."""
    return compute_snapshot_identity_fingerprint(list(input_snapshots))


def collect_ledger_input_snapshot_refs(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[dict[str, object]]:
    """Return input snapshots materialized after manifest creation via ledger."""
    refs: dict[str, dict[str, object]] = {}
    for entry in ledger_entries:
        if entry.event_type != INPUT_SNAPSHOT_PUBLISHED_EVENT:
            continue
        details = entry.details if isinstance(entry.details, Mapping) else {}
        snapshot_id = _snapshot_required_text(details.get("snapshot_id"))
        content_hash = _snapshot_required_text(details.get("content_hash"))
        immutable_uri = _snapshot_required_text(details.get("immutable_uri"))
        if snapshot_id is None or content_hash is None or immutable_uri is None:
            continue
        refs[snapshot_id] = {
            "provider": _snapshot_required_text(details.get("provider")),
            "entity": _snapshot_required_text(details.get("entity")),
            "pipeline_name": _snapshot_required_text(details.get("pipeline_name")),
            "query": _snapshot_required_text(details.get("query")),
            "snapshot_id": snapshot_id,
            "content_hash": content_hash,
            "immutable_uri": immutable_uri,
            "query_fingerprint": _snapshot_required_text(
                details.get("query_fingerprint")
            ),
            "storage_provider": _snapshot_required_text(
                details.get("storage_provider")
            ),
            "object_bucket": _snapshot_required_text(details.get("object_bucket")),
            "object_key": _snapshot_required_text(details.get("object_key")),
            "object_version_id": _snapshot_required_text(
                details.get("object_version_id")
            ),
            "etag": _snapshot_required_text(details.get("etag")),
            "last_modified": _snapshot_required_text(details.get("last_modified")),
            "captured_at": _snapshot_required_text(details.get("captured_at")),
            "materialization_mode": _snapshot_required_text(
                details.get("materialization_mode")
            )
            or LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
            "certification_scope": _snapshot_required_text(
                details.get("certification_scope")
            ),
            "certification_basis": _snapshot_required_text(
                details.get("certification_basis")
            ),
            "certification_artifact_ref": _snapshot_required_text(
                details.get("certification_artifact_ref")
            ),
            "upstream_run_id": _snapshot_required_text(details.get("upstream_run_id")),
            "upstream_manifest_id": _snapshot_required_text(
                details.get("upstream_manifest_id")
            ),
            "source_event_id": entry.entry_id,
        }
    return [refs[key] for key in sorted(refs)]


def resolve_post_manifest_input_snapshot_materialization_mode(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Return the deterministic post-manifest materialization mode summary."""
    modes = sorted(
        {
            str(snapshot.get("materialization_mode") or "").strip()
            for snapshot in input_snapshots
            if isinstance(snapshot, Mapping)
            and str(snapshot.get("materialization_mode") or "").strip()
        }
    )
    if not modes:
        return None
    if len(modes) == 1:
        return modes[0]
    return MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION


def merge_ledger_input_snapshots_into_summary(
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Merge ledger-derived input snapshots into diagnostics without mutating manifest."""
    ledger_snapshots = collect_ledger_input_snapshot_refs(ledger_entries)
    if not ledger_snapshots:
        return summary
    merged = dict(summary)
    snapshots_by_id = {
        str(snapshot.get("snapshot_id")): dict(snapshot)
        for snapshot in merged.get("input_snapshots", [])
        if isinstance(snapshot, Mapping) and snapshot.get("snapshot_id") is not None
    }
    for snapshot in ledger_snapshots:
        snapshots_by_id[str(snapshot["snapshot_id"])] = snapshot
    input_snapshots = [snapshots_by_id[key] for key in sorted(snapshots_by_id)]
    merged["input_snapshots"] = input_snapshots
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


def _snapshot_required_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# Compatibility aliases retained while helper imports are migrated incrementally.
_lookup_mapping_path = lookup_mapping_path
_collect_input_snapshot_refs = collect_input_snapshot_refs
_collect_input_snapshot_ids = collect_input_snapshot_ids
_collect_input_snapshot_content_hashes = collect_input_snapshot_content_hashes
_compute_input_snapshot_identity_fingerprint = (
    compute_input_snapshot_identity_fingerprint
)
