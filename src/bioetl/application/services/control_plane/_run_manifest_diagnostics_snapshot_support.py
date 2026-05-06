"""Nested-config and input-snapshot support helpers for replay diagnostics."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.normalization import serialize_json_canonical


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
    refs: list[dict[str, object]] = []
    for source_ref in manifest.source_refs:
        for snapshot in source_ref.input_snapshots:
            refs.append(
                {
                    "provider": source_ref.provider,
                    "entity": source_ref.entity,
                    "pipeline_name": source_ref.pipeline_name,
                    "query": source_ref.query,
                    "snapshot_id": snapshot.snapshot_id,
                    "content_hash": snapshot.content_hash,
                    "immutable_uri": snapshot.immutable_uri,
                    "query_fingerprint": snapshot.query_fingerprint,
                    "storage_provider": snapshot.storage_provider,
                    "object_bucket": snapshot.object_bucket,
                    "object_key": snapshot.object_key,
                    "object_version_id": snapshot.object_version_id,
                    "etag": snapshot.etag,
                    "last_modified": snapshot.last_modified,
                    "captured_at": snapshot.captured_at.isoformat()
                    if snapshot.captured_at is not None
                    else None,
                }
            )
    refs.sort(
        key=lambda item: (
            str(item.get("provider") or ""),
            str(item.get("entity") or ""),
            str(item.get("pipeline_name") or ""),
            str(item.get("snapshot_id") or ""),
        )
    )
    return refs


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
    snapshot_ids = collect_input_snapshot_ids(input_snapshots)
    if not snapshot_ids:
        return None
    encoded = serialize_json_canonical(snapshot_ids)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Compatibility aliases retained while helper imports are migrated incrementally.
_lookup_mapping_path = lookup_mapping_path
_collect_input_snapshot_refs = collect_input_snapshot_refs
_collect_input_snapshot_ids = collect_input_snapshot_ids
_collect_input_snapshot_content_hashes = collect_input_snapshot_content_hashes
_compute_input_snapshot_identity_fingerprint = (
    compute_input_snapshot_identity_fingerprint
)
