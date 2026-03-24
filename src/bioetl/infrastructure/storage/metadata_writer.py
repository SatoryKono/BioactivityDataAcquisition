"""Atomic sidecar metadata writer for Bronze, Silver, and Gold layers."""

from __future__ import annotations

__all__ = ["METADATA_FILENAME", "MetadataWriter"]

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from bioetl.domain.lineage import DatasetRef
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)
from bioetl.infrastructure.storage.metadata import writer_operations as _operations
from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _build_retry_callback,
    _emit_atomic_write_final_telemetry,
    _MetadataWriteRequest,
    _MetadataWriteRetryState,
    _MetadataWriteTelemetryContext,
    _prepare_metadata_write_operation,
    _PreparedMetadataWrite,
    _PreparedMetadataWriteOperation,
)
from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    atomic_write_text,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort


_get_metadata_filename = _operations._get_metadata_filename
ArtifactPublicationRecorder = Callable[[str, str, dict[str, object] | None], object]


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


class MetadataWriter:
    """Writer for metadata sidecar files across Bronze/Silver/Gold layers."""

    def __init__(
        self,
        logger: LoggerPort,
        *,
        atomic_replace_retry_policy: AdaptiveRetryPolicy | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize metadata writer (logger is mandatory per DI rules)."""
        self._logger = logger
        self._metrics = metrics
        self._artifact_recorder: ArtifactPublicationRecorder | None = None
        self._atomic_replace_retry_policy = (
            atomic_replace_retry_policy or DEFAULT_ATOMIC_REPLACE_RETRY_POLICY
        )

    def attach_artifact_recorder(
        self,
        recorder: ArtifactPublicationRecorder | None,
    ) -> None:
        """Attach an optional callback for control-plane artifact publication."""
        self._artifact_recorder = recorder

    def _build_metadata_write_request(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> _MetadataWriteRequest:
        """Build a normalized metadata sidecar request for the canonical write path."""
        return _MetadataWriteRequest(
            base_path=base_path,
            metadata=metadata,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def _finalize_existing_layer_metadata(
        self,
        *,
        base_path: str | Path,
        layer: str,
        apply_finalization: Callable[[SilverMetadata | GoldMetadata], None],
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str | None:
        """Load, patch, and atomically rewrite an existing Silver/Gold sidecar."""
        metadata_path = _resolve_existing_metadata_path(
            base_path=base_path,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )
        existing_metadata = await asyncio.to_thread(
            _load_existing_metadata_model,
            metadata_path,
            layer=layer,
        )
        if existing_metadata is None:
            return None

        apply_finalization(existing_metadata)
        return await self._write_metadata(
            self._build_metadata_write_request(
                base_path=base_path,
                metadata=existing_metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )

    async def _write_layer_metadata(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Build and execute one normalized metadata write request."""
        metadata_path = await self._write_metadata(
            self._build_metadata_write_request(
                base_path=base_path,
                metadata=metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )
        _record_artifact_publication(
            recorder=self._artifact_recorder,
            layer=layer,
            base_path=base_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )
        return metadata_path

    async def write_bronze_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Bronze layer metadata sidecar file.

        Args:
            base_path: Base path where Bronze data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Bronze metadata model with lineage and source info.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="bronze",
            provider=provider,
            entity=entity,
        )

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base path where Silver Delta table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def finalize_silver_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
        delta_version_after: int | None = None,
    ) -> str | None:
        """Finalize an existing Silver sidecar in place without republishing artifacts."""
        def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
            _apply_silver_metadata_finalization(
                metadata=cast("SilverMetadata", metadata),
                dq_report_path=dq_report_path,
                completed_at=completed_at,
                delta_version_after=delta_version_after,
            )

        return await self._finalize_existing_layer_metadata(
            base_path=base_path,
            layer="silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
            apply_finalization=apply_finalization,
        )

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base path where Gold Delta/Parquet table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Gold metadata model with lineage, schema contract, and SCD info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def finalize_gold_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
    ) -> str | None:
        """Finalize an existing Gold sidecar in place without republishing artifacts."""
        def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
            _apply_gold_metadata_finalization(
                metadata=cast("GoldMetadata", metadata),
                dq_report_path=dq_report_path,
                completed_at=completed_at,
            )

        return await self._finalize_existing_layer_metadata(
            base_path=base_path,
            layer="gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
            apply_finalization=apply_finalization,
        )

    async def _write_metadata(self, request: _MetadataWriteRequest) -> str:
        """Write sidecar metadata for Bronze/Silver/Gold layers and return file path."""
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._atomic_replace_retry_policy,
            operation=operation,
            metadata=request.metadata,
        )

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer."""
