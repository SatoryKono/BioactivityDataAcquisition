"""Finalization helpers for composition-backed Silver metadata operations."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Protocol

from bioetl.domain.models import SilverMetadata
from bioetl.domain.ports import MetadataCoordinatorPort, SilverMetadataInput
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)

__all__ = [
    "_PreparedSilverWriteFinalizationContext",
    "_build_silver_write_result",
    "_finalize_silver_write_result",
    "_prepare_silver_write_finalization_context",
]


class _MetadataFinalizationOps(Protocol):
    """Minimal host surface needed by finalization helpers."""

    @property
    def _metadata_coordinator(self) -> MetadataCoordinatorPort | None: ...

    async def _resolve_finalization_dq_metrics(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics: ...

    async def _resolve_version_after(self, table_path: str) -> int | None: ...

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None: ...

    def _resolve_manifest_id(self, *, records: list[BronzeRecord]) -> str | None: ...

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
    ) -> _PreparedSilverWriteFinalizationContext: ...


def _require_metadata_coordinator(
    metadata_coordinator: MetadataCoordinatorPort | None,
) -> MetadataCoordinatorPort:
    """Resolve the canonical metadata coordinator for Silver finalization."""
    if metadata_coordinator is None:
        raise RuntimeError(
            "MetadataCoordinatorPort is required for Silver metadata publication"
        )
    return metadata_coordinator


def _source_batch_ids(source_batch_id: object | None) -> list[str] | None:
    """Normalize optional source batch identity for SilverMetadataInput."""
    if source_batch_id is None:
        return None
    return [str(source_batch_id)]


def _build_silver_write_result(
    *,
    table_name: str,
    table_path: str,
    version_after: int | None,
    records_count: int,
) -> SilverWriteResult | None:
    """Build one Silver write result only when a Delta version is available."""
    return (
        None
        if version_after is None
        else SilverWriteResult(table_name, table_path, version_after, records_count)
    )


async def _prepare_silver_write_finalization_context(
    metadata_ops: _MetadataFinalizationOps,
    request: _SilverWriteFinalizationPreparationRequest,
    *,
    perf_counter: Callable[[], float] = time.perf_counter,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    _ = request.primary_keys, request.validated_mode

    dq_metrics = await metadata_ops._resolve_finalization_dq_metrics(
        table_name=request.table_name,
        records=request.records,
        quarantined_count=request.quarantined_count,
        validation_errors=request.validation_errors,
    )
    version_after = await metadata_ops._resolve_version_after(request.table_path)
    completed_at = request.started_at + timedelta(
        seconds=perf_counter() - request.start_perf
    )
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )


async def _finalize_silver_write_result(
    metadata_ops: _MetadataFinalizationOps,
    request: _SilverWriteResultFinalizationRequest,
) -> SilverWriteResult | None:
    """Compute DQ metrics, write metadata, and build final result."""
    _ = request.partition_cols

    context = await metadata_ops._prepare_silver_write_finalization_context(
        _SilverWriteFinalizationPreparationRequest(
            table_name=request.table_name,
            records=request.records,
            table_path=request.table_path,
            primary_keys=request.primary_keys,
            validated_mode=request.validated_mode,
            quarantined_count=request.quarantined_count,
            validation_errors=request.validation_errors,
            started_at=request.started_at,
            start_perf=request.start_perf,
        )
    )
    metadata_coordinator = _require_metadata_coordinator(
        metadata_ops._metadata_coordinator
    )
    metadata = metadata_coordinator.create_silver_metadata(
        SilverMetadataInput(
            table_path=request.table_path,
            primary_keys=request.primary_keys,
            mode=request.validated_mode,
            records=request.records,
            dq_metrics=context.dq_metrics,
            total_records=len(request.records),
            source_batch_ids=_source_batch_ids(request.source_batch_id),
            bronze_refs=request.bronze_refs,
            version_after=context.version_after,
            partition_by=request.partition_cols,
            started_at=request.started_at,
            completed_at=context.completed_at,
        )
    )
    await metadata_ops._persist_silver_metadata(
        metadata=metadata,
        table_name=request.table_name,
        table_path=request.table_path,
    )
    return SilverWriteResult(
        table_name=request.table_name,
        table_path=request.table_path,
        delta_version=context.version_after or 0,
        record_count=len(request.records),
    )
