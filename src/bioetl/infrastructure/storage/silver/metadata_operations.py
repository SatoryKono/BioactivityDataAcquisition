"""Metadata operations extracted from ``SilverWriterMetadataMixin``."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol

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
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)
from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

if TYPE_CHECKING:
    from bioetl.domain.lineage import LineageGraphFragment

__all__ = [
    "_PreparedSilverWriteFinalizationContext",
    "_SilverMergedMetadataWriteRequest",
    "_SilverMetadataWriteRequest",
    "_build_silver_write_result",
    "_execute_silver_metadata_write",
    "_prepare_silver_merged_metadata_write",
    "_prepare_silver_metadata_write",
    "_prepare_silver_write_finalization_context",
    "_read_delta_version",
]


@dataclass(frozen=True, slots=True)
class _SilverMetadataWriteRequest:
    """Normalized request payload for one standard Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None = None
    dq_metrics: BatchDQMetrics | None = None
    dq_report_path: str | None = None
    partition_by: list[str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    version_after: int | None = None


@dataclass(frozen=True, slots=True)
class _SilverMergedMetadataWriteRequest:
    """Normalized request payload for one merged Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    run_id: str | None = None
    sources_used: list[str] | None = None


@dataclass(frozen=True, slots=True)
class _PreparedSilverMetadataWriteOperation:
    """Prepared Silver metadata operation carried into sidecar execution."""

    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: SilverMetadata
    lineage_fragment: LineageGraphFragment | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedSilverMetadataContext:
    """Shared provider/entity/version context for Silver metadata preparation."""

    provider_name: str
    entity_name: str
    version_after: int | None


@dataclass(frozen=True, slots=True)
class _PreparedSilverWriteFinalizationContext:
    """Prepared metadata/result context for one completed Silver write."""

    dq_metrics: BatchDQMetrics
    version_after: int | None
    completed_at: datetime


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
    ) -> BatchDQMetrics: ...

    async def _get_delta_version(self, table_path: str) -> int | None: ...


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
    assert coordinator is not None
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
        started_at=request.started_at,
        completed_at=request.completed_at,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name="create_silver_metadata",
        input_data=silver_input,
        fallback_factory=lambda: coordinator.create_silver_metadata(silver_input),
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
    from bioetl.infrastructure.storage.metadata_builder import SilverMetadataBuilder

    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
    )
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=SilverWriteMode.DELETE,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    builder = SilverMetadataBuilder(
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=host._metadata_coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name="create_silver_metadata",
        input_data=silver_input,
        fallback_factory=lambda: builder.build_merged_metadata(
            table_path=request.table_path,
            table_name=request.table_name,
            records=request.records,
            primary_keys=request.primary_keys,
            run_id=request.run_id,
            sources_used=request.sources_used,
            version_after=context.version_after,
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


async def _execute_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest,
    prepare: Callable[..., Awaitable[_PreparedSilverMetadataWriteOperation]],
) -> None:
    """Prepare and persist one Silver metadata write via the canonical lifecycle."""
    prepared = await prepare(host, request)
    await _execute_prepared_silver_metadata_write_operation(host, prepared)


async def _prepare_silver_write_finalization_context(
    host: _SilverWriteFinalizationHostProtocol,
    *,
    table_name: str,
    records: list[BronzeRecord],
    table_path: str,
    started_at: datetime,
    start_perf: float,
    perf_counter: Callable[[], float] = time.perf_counter,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    dq_metrics = await host._compute_dq_metrics(table_name, records)
    version_after = await host._get_delta_version(table_path)
    completed_at = started_at + timedelta(seconds=perf_counter() - start_perf)
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )
