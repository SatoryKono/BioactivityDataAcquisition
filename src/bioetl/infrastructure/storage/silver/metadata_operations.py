"""Metadata operations extracted from ``SilverWriterMetadataMixin``."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timedelta
from typing import Protocol

from deltalake import DeltaTable

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    LineageStorePort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverMetadataInput,
)
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)
from bioetl.infrastructure.storage.metadata.builder_base import (
    _parse_table_name,
    _resolve_metadata_timestamp,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _coerce_silver_metadata_write_request,
    _PreparedSilverMetadataWriteOperation,
    _PreparedSilverWriteFinalizationContext,
    _ResolvedSilverMetadataContext,
    _SilverMergedMetadataWriteRequest,
    _SilverMetadataWriteRequest,
)

__all__ = [
    "_PreparedSilverWriteFinalizationContext",
    "_SilverMergedMetadataWriteRequest",
    "_SilverMetadataWriteRequest",
    "_build_silver_write_result",
    "_coerce_silver_metadata_write_request",
    "_execute_silver_metadata_write",
    "_prepare_silver_merged_metadata_write",
    "_prepare_silver_metadata_write",
    "_prepare_silver_write_finalization_context",
    "_read_delta_version",
]


class _SilverMetadataWriteHostProtocol(Protocol):
    """Typed host contract for Silver metadata sidecar stages."""

    _metadata_coordinator: MetadataCoordinatorPort | None
    _lineage_store: LineageStorePort | None
    _metadata_writer: MetadataWriterPort
    _metrics: MetricsPort | None
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]

    async def _get_delta_version(self, table_path: str) -> int | None: ...

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


class _SilverWriteFinalizationHostProtocol(Protocol):
    """Host contract for DQ/version finalization before metadata persistence."""

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics: ...

    async def _get_delta_version(self, table_path: str) -> int | None: ...


def _emit_prepared_silver_metadata_metrics(
    host: _SilverMetadataWriteHostProtocol,
    prepared: _PreparedSilverMetadataWriteOperation,
) -> None:
    """Emit lineage/composite metrics for an already prepared metadata operation."""
    pipeline_name = f"{prepared.provider_name}_{prepared.entity_name}"
    if isinstance(prepared.request, _SilverMetadataWriteRequest):
        if not prepared.request.bronze_refs:
            emit_lineage_refs_missing_metric(
                getattr(host, "_metrics", None),
                pipeline_name=pipeline_name,
                layer="silver",
                ref_type="bronze_batch",
            )
        return
    emit_composite_source_selection_metrics(
        getattr(host, "_metrics", None),
        pipeline_name=pipeline_name,
        layer="silver",
        sources_used=prepared.request.sources_used,
        records=prepared.request.records,
    )


def _build_silver_write_result(
    *, table_name: str, table_path: str, version_after: int | None, records_count: int
) -> SilverWriteResult | None:
    return (
        None
        if version_after is None
        else SilverWriteResult(table_name, table_path, version_after, records_count)
    )


def _read_delta_version(table_path: str) -> int:
    """Read the current Delta table version synchronously."""
    return DeltaTable(table_path).version()


async def _resolve_silver_metadata_context(
    host: _SilverMetadataWriteHostProtocol,
    *,
    table_path: str,
    table_name: str,
    version_after: int | None = None,
) -> _ResolvedSilverMetadataContext:
    """Resolve shared provider/entity/version context for Silver metadata writes."""
    provider_name, entity_name = _parse_table_name(table_name)
    version = (
        version_after
        if version_after is not None
        else await host._get_delta_version(table_path)
    )
    return _ResolvedSilverMetadataContext(provider_name, entity_name, version)


async def _prepare_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build standard Silver metadata payload."""
    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
        version_after=request.version_after,
    )
    coordinator = host._metadata_coordinator
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=request.mode,
        bronze_refs=request.bronze_refs,
        dq_metrics=request.dq_metrics,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
        dq_report_path=request.dq_report_path,
        partition_by=request.partition_by,
        source_batch_ids=request.source_batch_ids,
        started_at=request.started_at,
        completed_at=request.completed_at,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name=None,
        input_data=silver_input,
        fallback_factory=lambda: _raise_missing_silver_metadata_bundle(
            table_path=request.table_path,
            table_name=request.table_name,
        ),
    )
    return _PreparedSilverMetadataWriteOperation(
        request=request,
        provider_name=context.provider_name,
        entity_name=context.entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


async def _prepare_silver_merged_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMergedMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build merged Silver metadata payload."""
    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
    )
    merged_completed_at = _resolve_metadata_timestamp(
        explicit=request.completed_at,
        records=request.records,
    )
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=SilverWriteMode.DELETE,
        started_at=merged_completed_at,
        completed_at=merged_completed_at,
        composite_run_id=request.run_id,
        lineage_created_at=merged_completed_at,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=host._metadata_coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name=None,
        input_data=silver_input,
        fallback_factory=lambda: _raise_missing_silver_metadata_bundle(
            table_path=request.table_path,
            table_name=request.table_name,
        ),
    )
    return _PreparedSilverMetadataWriteOperation(
        request=request,
        provider_name=context.provider_name,
        entity_name=context.entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


async def _execute_prepared_silver_metadata_write_operation(
    host: _SilverMetadataWriteHostProtocol,
    prepared: _PreparedSilverMetadataWriteOperation,
) -> None:
    """Execute one prepared Silver metadata operation via the writer handoff."""
    await host._write_silver_metadata_file(
        table_path=prepared.request.table_path,
        metadata=prepared.metadata,
        table_name=prepared.request.table_name,
        provider_name=prepared.provider_name,
        entity_name=prepared.entity_name,
    )
    await persist_lineage_fragment_if_present(
        lineage_store=getattr(host, "_lineage_store", None),
        lineage_fragment=prepared.lineage_fragment,
        metrics=getattr(host, "_metrics", None),
        pipeline_name=f"{prepared.provider_name}_{prepared.entity_name}",
        layer="silver",
    )
    _emit_prepared_silver_metadata_metrics(host, prepared)


async def _execute_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest,
    prepare: Callable[..., Awaitable[_PreparedSilverMetadataWriteOperation]],
) -> None:
    """Prepare and persist one Silver metadata write via the canonical lifecycle."""
    prepared = await prepare(host, request)
    await _execute_prepared_silver_metadata_write_operation(host, prepared)


def _raise_missing_silver_metadata_bundle(
    *,
    table_path: str,
    table_name: str,
) -> SilverMetadata:
    """Fail closed when canonical Silver metadata bundle construction is unavailable."""
    raise RuntimeError(
        "MetadataCoordinator with create_silver_metadata_bundle is required "
        f"for Silver metadata publication: table_name={table_name}, "
        f"table_path={table_path}"
    )


async def _prepare_silver_write_finalization_context(
    host: _SilverWriteFinalizationHostProtocol,
    *,
    table_name: str,
    records: list[BronzeRecord],
    table_path: str,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
    started_at: datetime,
    start_perf: float,
    perf_counter: Callable[[], float] = time.perf_counter,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    dq_metrics = await host._compute_dq_metrics(
        table_name,
        records,
        quarantined_count=quarantined_count or 0,
        validation_errors=validation_errors,
    )
    version_after = await host._get_delta_version(table_path)
    completed_at = started_at + timedelta(seconds=perf_counter() - start_perf)
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )
