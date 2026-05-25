"""Artifact-publication helpers for metadata sidecar writers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from bioetl.domain.lineage import DatasetRef
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    GoldMetadata,
    InputSnapshotRef,
    SilverMetadata,
)
from bioetl.domain.ports import MetricsPort

ArtifactPublicationRecorder = Callable[[str, str, dict[str, object] | None], object]


def _derive_dataset_ref(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str | None:
    """Return canonical dataset ref when the sidecar represents a dataset artifact."""
    artifact_id = str(getattr(metadata.output, "artifact_id", "") or "").strip()
    if artifact_id.startswith(("bronze_batch:", "silver:", "gold:")):
        return artifact_id
    layer = str(getattr(metadata, "layer", ""))
    if layer == "silver":
        output_ext = getattr(metadata, "output_ext", None)
        dataset_ref = DatasetRef(
            layer="silver",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            version=getattr(output_ext, "delta_version_after", None),
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        )
        return str(dataset_ref.node_id)
    if layer == "gold":
        dataset_ref = DatasetRef(
            layer="gold",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        )
        return str(dataset_ref.node_id)
    return None


def _resolve_lineage_log_context(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> dict[str, object]:
    """Resolve optional lineage anchors for control-plane and log emission."""
    return {
        "dataset_ref": _derive_dataset_ref(metadata),
        "lineage_fragment_id": metadata.output.lineage_fragment_id,
    }


def _artifact_publication_metric_labels(
    *,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
    status: str,
) -> dict[str, str]:
    """Build canonical labels for artifact-publication outcome metrics."""
    return {
        "pipeline": metadata.pipeline.name,
        "stage": layer,
        "status": status,
    }


def _record_artifact_publication_metric(
    *,
    metrics: MetricsPort | None,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
    status: str,
) -> None:
    """Emit one bounded artifact-publication status counter when metrics exist."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_output_artifact_publication_events_total",
        1,
        _artifact_publication_metric_labels(
            metadata=metadata,
            layer=layer,
            status=status,
        ),
    )


def _require_artifact_publication_identifier(
    *,
    raw_value: object | None,
    missing_message: str,
    metrics: MetricsPort | None,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    layer: str,
) -> str:
    """Return a required publication identifier or raise a contract error."""
    value = str(raw_value or "").strip()
    if value:
        return value
    _record_artifact_publication_metric(
        metrics=metrics,
        metadata=metadata,
        layer=layer,
        status="failed",
    )
    raise RuntimeError(missing_message)


def _build_artifact_publication_details(
    *,
    metadata_path: str,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
    manifest_id: str,
    artifact_id: str,
    layer: str,
) -> dict[str, object]:
    """Build callback payload for one published output artifact."""
    lineage_context = _resolve_lineage_log_context(metadata)
    execution_fingerprint = getattr(metadata.pipeline, "execution_fingerprint", None)
    details: dict[str, object] = {
        "artifact_kind": "layer_output",
        "artifact_semantics": _resolve_artifact_semantics(
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
    _attach_input_snapshot_details(details=details, metadata=metadata)
    return details


def _resolve_artifact_semantics(
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


def _attach_input_snapshot_details(
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
        _serialize_input_snapshot_ref(snapshot) for snapshot in input_snapshots
    ]


def _serialize_input_snapshot_ref(snapshot: InputSnapshotRef) -> dict[str, object]:
    """Return the bounded input snapshot evidence persisted in run ledger."""
    captured_at = getattr(snapshot, "captured_at", None)
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
        "last_modified": getattr(snapshot, "last_modified", None),
        "captured_at": captured_at.isoformat()
        if isinstance(captured_at, datetime)
        else None,
    }


def _record_artifact_publication(
    *,
    recorder: ArtifactPublicationRecorder | None,
    metrics: MetricsPort | None,
    layer: str,
    base_path: str | Path,
    metadata_path: str,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> None:
    """Emit the optional control-plane artifact publication callback."""
    if recorder is None:
        _record_artifact_publication_metric(
            metrics=metrics,
            metadata=metadata,
            layer=layer,
            status="disabled",
        )
        return
    manifest_id = _require_artifact_publication_identifier(
        raw_value=metadata.runtime.manifest_id,
        missing_message=(
            "Control-plane artifact publication requires metadata.runtime.manifest_id"
        ),
        metrics=metrics,
        metadata=metadata,
        layer=layer,
    )
    artifact_id = _require_artifact_publication_identifier(
        raw_value=metadata.output.artifact_id,
        missing_message=(
            "Control-plane artifact publication requires metadata.output.artifact_id"
        ),
        metrics=metrics,
        metadata=metadata,
        layer=layer,
    )
    details = _build_artifact_publication_details(
        metadata_path=metadata_path,
        metadata=metadata,
        manifest_id=manifest_id,
        artifact_id=artifact_id,
        layer=layer,
    )
    try:
        recorder(layer, str(Path(base_path).resolve()), details)
    except RuntimeError:
        _record_artifact_publication_metric(
            metrics=metrics,
            metadata=metadata,
            layer=layer,
            status="failed",
        )
        raise
    _record_artifact_publication_metric(
        metrics=metrics,
        metadata=metadata,
        layer=layer,
        status="success",
    )


__all__ = [
    "ArtifactPublicationRecorder",
    "_record_artifact_publication",
    "_resolve_lineage_log_context",
]
