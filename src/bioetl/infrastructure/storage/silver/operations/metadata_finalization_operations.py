"""Finalization helper bindings for Silver metadata operations."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverWriteFinalizationHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_result_finalization import (
    _build_silver_write_result,
    _prepare_silver_write_finalization_context,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)


class _SilverMetadataFinalizationOps(
    _SilverWriteFinalizationHostProtocol,
    Protocol,
):
    """Minimal facade surface needed by Silver metadata finalization helpers."""

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
    ) -> _PreparedSilverWriteFinalizationContext: ...

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None: ...


async def prepare_silver_write_finalization_context_operation(
    metadata_ops: _SilverMetadataFinalizationOps,
    request: _SilverWriteFinalizationPreparationRequest,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/provenance context using the injected clock."""
    return await _prepare_silver_write_finalization_context(metadata_ops, request)


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
            duration_seconds=context.duration_seconds,
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
