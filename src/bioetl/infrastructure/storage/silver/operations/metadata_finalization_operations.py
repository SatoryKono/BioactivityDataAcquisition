"""Finalization helper bindings for Silver metadata operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_support import (
    _build_silver_write_result,
    _prepare_silver_write_finalization_context,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)


class _SilverMetadataFinalizationOps(Protocol):
    """Minimal facade surface needed by Silver metadata finalization helpers."""

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
        *,
        perf_counter: Callable[[], float] | None = None,
    ) -> _PreparedSilverWriteFinalizationContext: ...

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None: ...


async def prepare_silver_write_finalization_context_with_default_perf_counter(
    metadata_ops: _SilverMetadataFinalizationOps,
    request: _SilverWriteFinalizationPreparationRequest,
    *,
    perf_counter: Callable[[], float] | None = None,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare finalization context using the canonical perf-counter fallback."""
    resolved_perf_counter = perf_counter
    if resolved_perf_counter is None:
        from bioetl.infrastructure.storage.silver import metadata_mixin

        resolved_perf_counter = metadata_mixin.time.perf_counter
    return await _prepare_silver_write_finalization_context(
        metadata_ops,
        request,
        perf_counter=resolved_perf_counter,
    )


async def prepare_silver_write_finalization_context_operation(
    metadata_ops: _SilverMetadataFinalizationOps,
    request: _SilverWriteFinalizationPreparationRequest,
    *,
    perf_counter: Callable[[], float] | None = None,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    return await prepare_silver_write_finalization_context_with_default_perf_counter(
        metadata_ops,
        request,
        perf_counter=perf_counter,
    )


async def finalize_silver_write_result_from_request(
    metadata_ops: _SilverMetadataFinalizationOps,
    request: _SilverWriteResultFinalizationRequest,
) -> SilverWriteResult | None:
    """Compute DQ metrics, write metadata, and build one final Silver result."""
    context = await metadata_ops._prepare_silver_write_finalization_context(
        _SilverWriteFinalizationPreparationRequest(
            table_name=request.table_name,
            records=request.records,
            table_path=request.table_path,
            quarantined_count=request.quarantined_count,
            validation_errors=request.validation_errors,
            started_at=request.started_at,
            start_perf=request.start_perf,
        )
    )

    await metadata_ops._write_silver_metadata(
        _SilverMetadataWriteRequest(
            table_path=request.table_path,
            table_name=request.table_name,
            records=request.records,
            primary_keys=request.primary_keys,
            mode=request.validated_mode,
            bronze_refs=request.bronze_refs,
            dq_metrics=context.dq_metrics,
            partition_by=request.partition_cols,
            source_batch_ids=(
                [str(request.source_batch_id)]
                if request.source_batch_id is not None
                else None
            ),
            started_at=request.started_at,
            completed_at=context.completed_at,
            version_after=context.version_after,
        )
    )
    return _build_silver_write_result(
        table_name=request.table_name,
        table_path=request.table_path,
        version_after=context.version_after,
        records_count=len(request.records),
    )


async def finalize_silver_write_result_operation(
    metadata_ops: _SilverMetadataFinalizationOps,
    request: _SilverWriteResultFinalizationRequest,
) -> SilverWriteResult | None:
    """Compute DQ metrics, write metadata, and build final result."""
    return await finalize_silver_write_result_from_request(
        metadata_ops,
        request,
    )
