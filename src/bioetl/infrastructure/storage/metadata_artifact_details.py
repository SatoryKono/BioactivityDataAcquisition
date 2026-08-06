"""Callback detail payload helpers for metadata artifact publication."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.models.metadata import (
    BronzeMetadata,
    GoldMetadata,
    InputSnapshotRef,
    SilverMetadata,
)
from bioetl.infrastructure.storage.metadata_artifact_dataset import (
    resolve_lineage_log_context,
)


def build_artifact_publication_details(
    *,
    metadata_path: str,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    manifest_id: str,
    artifact_id: str,
    layer: str,
) -> dict[str, object]:
    """Build callback payload for one published output artifact."""
    lineage_context = resolve_lineage_log_context(metadata)
    execution_fingerprint = getattr(metadata.pipeline, "execution_fingerprint", None)
    details: dict[str, object] = {
        "artifact_kind": "layer_output",
        "artifact_semantics": resolve_artifact_semantics(
            metadata=metadata,
            layer=layer,
        ),
        "artifact_id": artifact_id,
        "metadata_path": metadata_path,
        "record_count": int(metadata.output.record_count),
        "total_bytes": int(metadata.output.total_bytes),
        "content_hash": metadata.output.content_hash,
        "hash_algorithm": "sha256",
        "run_id": str(metadata.runtime.run_id),
        "manifest_id": manifest_id,
        "pipeline_name": metadata.pipeline.name,
        "provider": metadata.pipeline.provider,
        "entity": metadata.pipeline.entity,
        "exact_replay": getattr(metadata.runtime, "exact_replay", None),
        "replay_of_run_id": getattr(metadata.runtime, "replay_of_run_id", None),
        "replay_of_manifest_id": getattr(
            metadata.runtime, "replay_of_manifest_id", None
        ),
        "input_snapshot_fingerprint": getattr(
            metadata.runtime, "input_snapshot_fingerprint", None
        ),
        "effective_config_artifact_id": getattr(
            metadata.pipeline, "effective_config_artifact_id", None
        ),
        "contract_ref": getattr(metadata.pipeline, "contract_ref", None),
        "contract_version": getattr(metadata.pipeline, "contract_version", None),
        "dataset_ref": lineage_context["dataset_ref"],
        "lineage_fragment_id": lineage_context["lineage_fragment_id"],
    }
    if execution_fingerprint is not None:
        details["execution_fingerprint"] = str(execution_fingerprint)
    attach_input_snapshot_details(details=details, metadata=metadata)
    return details


def resolve_artifact_semantics(
    *,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
) -> str:
    """Return the replay semantics for one published layer artifact."""
    if isinstance(metadata, BronzeMetadata):
        input_snapshots = getattr(metadata.source, "input_snapshots", [])
        if input_snapshots:
            return "immutable_input_snapshot"
        return "occurrence_append"
    if layer == "silver":
        return "semantic_table"
    if layer == "gold":
        return "derived_dataset"
    return "unknown"


def attach_input_snapshot_details(
    *,
    details: dict[str, object],
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> None:
    """Attach Bronze input snapshot references when present."""
    if not isinstance(metadata, BronzeMetadata):
        return
    input_snapshots = getattr(metadata.source, "input_snapshots", [])
    if not input_snapshots:
        return
    details["input_snapshot_count"] = len(input_snapshots)
    details["input_snapshot_ids"] = [
        snapshot.snapshot_id for snapshot in input_snapshots
    ]
    details["input_snapshot_content_hashes"] = [
        snapshot.content_hash for snapshot in input_snapshots
    ]
    details["input_snapshots"] = [
        serialize_input_snapshot_ref(snapshot) for snapshot in input_snapshots
    ]


def _normalize_optional_datetime(value: object) -> object:
    """Normalize datetime values to ISO-8601; preserve non-datetime contracts."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_input_snapshot_ref(snapshot: InputSnapshotRef) -> dict[str, object]:
    """Return the bounded input snapshot evidence persisted in run ledger."""
    captured_at = getattr(snapshot, "captured_at", None)
    last_modified = getattr(snapshot, "last_modified", None)
    return {
        "snapshot_id": str(snapshot.snapshot_id),
        "content_hash": str(snapshot.content_hash),
        "immutable_uri": getattr(snapshot, "immutable_uri", None),
        "query_fingerprint": getattr(snapshot, "query_fingerprint", None),
        "storage_provider": getattr(snapshot, "storage_provider", None),
        "object_bucket": getattr(snapshot, "object_bucket", None),
        "object_key": getattr(snapshot, "object_key", None),
        "object_version_id": getattr(snapshot, "object_version_id", None),
        "etag": getattr(snapshot, "etag", None),
        "last_modified": _normalize_optional_datetime(last_modified),
        "captured_at": _normalize_optional_datetime(captured_at),
    }


__all__ = ["build_artifact_publication_details"]
