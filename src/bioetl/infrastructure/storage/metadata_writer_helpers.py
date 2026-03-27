"""Shared helpers for metadata sidecar writing."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import yaml

from bioetl.domain.lineage import DatasetRef
from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata
from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy
from bioetl.infrastructure.storage.metadata import writer_operations as _operations
from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _build_retry_callback,
    _emit_atomic_write_final_telemetry,
    _MetadataWriteRetryState,
    _MetadataWriteTelemetryContext,
    _PreparedMetadataWrite,
    _PreparedMetadataWriteOperation,
)
from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    atomic_write_text,
)

_get_metadata_filename = _operations._get_metadata_filename
ArtifactPublicationRecorder = Callable[[str, str, dict[str, object] | None], object]

__all__ = [
    "_execute_prepared_metadata_write_operation",
    "_get_metadata_filename",
    "atomic_write_text",
]


def _derive_dataset_ref(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str | None:
    """Return canonical dataset ref when the sidecar represents a dataset artifact."""
    layer = str(getattr(metadata, "layer", ""))
    if layer == "silver":
        output_ext = getattr(metadata, "output_ext", None)
        return DatasetRef(
            layer="silver",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            version=getattr(output_ext, "delta_version_after", None),
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        ).node_id
    if layer == "gold":
        return DatasetRef(
            layer="gold",
            logical_name=f"{metadata.pipeline.provider}.{metadata.pipeline.entity}",
            provider=metadata.pipeline.provider,
            entity=metadata.pipeline.entity,
        ).node_id
    return None


def _resolve_lineage_log_context(
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> dict[str, object]:
    """Resolve optional lineage anchors for control-plane and log emission."""
    return {
        "dataset_ref": _derive_dataset_ref(metadata),
        "lineage_fragment_id": metadata.output.lineage_fragment_id,
    }


def _apply_common_metadata_finalization(
    *,
    metadata: SilverMetadata | GoldMetadata,
    dq_report_path: str | None,
    completed_at: datetime | None,
) -> None:
    """Apply shared postrun finalization fields to one sidecar model."""
    if dq_report_path is not None:
        metadata.dq_report_path = dq_report_path
    if completed_at is not None:
        metadata.runtime.completed_at_utc = completed_at
        metadata.output.write_completed_at = completed_at


def _apply_silver_metadata_finalization(
    *,
    metadata: SilverMetadata,
    dq_report_path: str | None,
    completed_at: datetime | None,
    delta_version_after: int | None,
) -> None:
    """Apply Silver-specific postrun finalization fields."""
    _apply_common_metadata_finalization(
        metadata=metadata,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
    )
    if delta_version_after is not None:
        metadata.delta.version_after = delta_version_after
        metadata.output_ext.delta_version_after = delta_version_after


def _apply_gold_metadata_finalization(
    *,
    metadata: GoldMetadata,
    dq_report_path: str | None,
    completed_at: datetime | None,
) -> None:
    """Apply Gold-specific postrun finalization fields."""
    _apply_common_metadata_finalization(
        metadata=metadata,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
    )


def _load_existing_metadata_model(
    metadata_path: Path,
    *,
    layer: str,
) -> SilverMetadata | GoldMetadata | None:
    """Load an existing Silver/Gold sidecar model from disk when present."""
    if not metadata_path.exists():
        return None

    payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    output_payload = payload.get("output")
    if isinstance(output_payload, dict):
        output_payload.pop("write_duration_ms", None)

    from bioetl.domain.models.metadata import GoldMetadata, SilverMetadata

    if layer == "silver":
        return SilverMetadata.model_validate(payload)
    return GoldMetadata.model_validate(payload)


def _resolve_existing_metadata_path(
    *,
    base_path: str | Path,
    layer: str,
    table_name: str | None = None,
    flat_structure: bool = False,
    provider: str | None = None,
    entity: str | None = None,
) -> Path:
    """Resolve an existing sidecar path without requiring a metadata payload."""
    path = Path(base_path)
    if provider and entity:
        return path / _get_metadata_filename(provider, entity)
    if flat_structure and table_name:
        return path / f"{table_name}_metadata.yaml"
    return path / METADATA_FILENAME


async def _execute_atomic_metadata_write(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    prepared_write: _PreparedMetadataWrite,
    retry_policy: AdaptiveRetryPolicy,
    context: _MetadataWriteTelemetryContext,
) -> int:
    """Write prepared metadata atomically and emit retry/final telemetry."""
    retry_state = _MetadataWriteRetryState()
    on_retry = _build_retry_callback(
        logger=logger,
        metrics=metrics,
        context=context,
        retry_state=retry_state,
    )

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: atomic_write_text(
                prepared_write.metadata_path,
                prepared_write.yaml_content,
                retry_policy=retry_policy,
                on_retry=on_retry,
            ),
        )
    except AtomicWriteError as exc:
        _emit_atomic_write_final_telemetry(
            logger=logger,
            metrics=metrics,
            context=context,
            retry_state=retry_state,
            status="failed",
            final_reason=exc.reason or "atomic_write_error",
        )
        raise

    _emit_atomic_write_final_telemetry(
        logger=logger,
        metrics=metrics,
        context=context,
        retry_state=retry_state,
        status="succeeded",
        final_reason=(
            "success_after_retry" if retry_state.count > 0 else "success_without_retry"
        ),
    )
    return retry_state.count


def _finalize_metadata_write_operation(
    *,
    logger: LoggerPort,
    operation: _PreparedMetadataWriteOperation,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str:
    """Emit final write log and return the resolved metadata sidecar path."""
    lineage_context = _resolve_lineage_log_context(metadata)
    logger.info(
        "metadata_written",
        layer=operation.telemetry_context.layer,
        path=str(operation.prepared_write.metadata_path),
        run_id=operation.run_id,
        dataset_ref=lineage_context["dataset_ref"],
        lineage_fragment_id=lineage_context["lineage_fragment_id"],
    )
    return str(operation.prepared_write.metadata_path.resolve())


def _record_artifact_publication(
    *,
    recorder: ArtifactPublicationRecorder | None,
    layer: str,
    base_path: str | Path,
    metadata_path: str,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> None:
    """Emit the optional control-plane artifact publication callback."""
    if recorder is None:
        return
    lineage_context = _resolve_lineage_log_context(metadata)
    details: dict[str, object] = {
        "artifact_kind": "layer_output",
        "metadata_path": metadata_path,
        "record_count": int(metadata.output.record_count),
        "total_bytes": int(metadata.output.total_bytes),
        "pipeline_name": metadata.pipeline.name,
        "provider": metadata.pipeline.provider,
        "entity": metadata.pipeline.entity,
        "dataset_ref": lineage_context["dataset_ref"],
        "lineage_fragment_id": lineage_context["lineage_fragment_id"],
    }
    recorder(layer, str(Path(base_path).resolve()), details)


async def _execute_prepared_metadata_write_operation(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    retry_policy: AdaptiveRetryPolicy,
    operation: _PreparedMetadataWriteOperation,
    metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
) -> str:
    """Execute one prepared metadata write operation end-to-end."""
    await _execute_atomic_metadata_write(
        logger=logger,
        metrics=metrics,
        prepared_write=operation.prepared_write,
        retry_policy=retry_policy,
        context=operation.telemetry_context,
    )
    return _finalize_metadata_write_operation(
        logger=logger,
        operation=operation,
        metadata=metadata,
    )
