"""Canonical input-snapshot payload builders owned by the domain layer."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest, RunSourceRef
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint


def serialize_snapshot_captured_at(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def input_snapshot_payload(
    snapshot: RunInputSnapshotRef,
    *,
    serialize_captured_at: bool,
) -> dict[str, object]:
    captured_at: datetime | str | None = snapshot.captured_at
    if serialize_captured_at:
        captured_at = serialize_snapshot_captured_at(snapshot.captured_at)
    return {
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
        "captured_at": captured_at,
    }


def source_ref_payload(source_ref: RunSourceRef) -> dict[str, object]:
    return {
        "provider": source_ref.provider,
        "entity": source_ref.entity,
        "pipeline_name": source_ref.pipeline_name,
        "query": source_ref.query,
        "input_snapshots": [
            input_snapshot_payload(snapshot, serialize_captured_at=False)
            for snapshot in source_ref.input_snapshots
        ],
    }


def source_refs_payload(
    source_refs: tuple[RunSourceRef, ...],
) -> list[dict[str, object]]:
    return [source_ref_payload(source_ref) for source_ref in source_refs]


def _trace_ref_sort_key(item: Mapping[str, object]) -> tuple[str, str, str, str]:
    """Return the deterministic ordering key for snapshot trace refs."""
    return (
        str(item.get("provider") or ""),
        str(item.get("entity") or ""),
        str(item.get("pipeline_name") or ""),
        str(item.get("snapshot_id") or ""),
    )


def manifest_input_snapshot_trace_refs(
    manifest: RunManifest,
) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for source_ref in manifest.source_refs:
        for snapshot in source_ref.input_snapshots:
            refs.append(_trace_ref_row(source_ref, snapshot))
    refs.sort(key=_trace_ref_sort_key)
    return refs


def _trace_ref_row(
    source_ref: RunSourceRef,
    snapshot: RunInputSnapshotRef,
) -> dict[str, object]:
    """Build one flattened snapshot trace ref row."""
    return {
        "provider": source_ref.provider,
        "entity": source_ref.entity,
        "pipeline_name": source_ref.pipeline_name,
        "query": source_ref.query,
        **input_snapshot_payload(snapshot, serialize_captured_at=True),
    }


def _trace_ref_sort_key(item: dict[str, object]) -> tuple[str, str, str, str]:
    """Return the deterministic ordering key for snapshot trace refs."""
    return (
        str(item.get("provider") or ""),
        str(item.get("entity") or ""),
        str(item.get("pipeline_name") or ""),
        str(item.get("snapshot_id") or ""),
    )


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


def compute_snapshot_identity_fingerprint(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Compute the same stable replay-anchor fingerprint shape used by checkpoints."""
    return compute_input_snapshot_identity_fingerprint(list(input_snapshots))


__all__ = [
    "collect_input_snapshot_content_hashes",
    "collect_input_snapshot_ids",
    "collect_input_snapshot_refs",
    "compute_snapshot_identity_fingerprint",
    "input_snapshot_payload",
    "manifest_input_snapshot_trace_refs",
    "serialize_snapshot_captured_at",
    "source_ref_payload",
    "source_refs_payload",
]
