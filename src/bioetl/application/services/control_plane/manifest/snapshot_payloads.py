"""Canonical input-snapshot payload builders owned by the manifest package."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest, RunSourceRef


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


def manifest_input_snapshot_trace_refs(
    manifest: RunManifest,
) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for source_ref in manifest.source_refs:
        for snapshot in source_ref.input_snapshots:
            refs.append(
                {
                    "provider": source_ref.provider,
                    "entity": source_ref.entity,
                    "pipeline_name": source_ref.pipeline_name,
                    "query": source_ref.query,
                    **input_snapshot_payload(snapshot, serialize_captured_at=True),
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
