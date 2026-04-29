"""Finalization helpers for composition-backed Silver metadata operations."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Protocol

from bioetl.domain.models import SilverMetadata
from bioetl.domain.models.metadata import RunTypeEnum
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _PreparedSilverWriteFinalizationContext,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter import (
    _build_silver_sidecar_metadata,
    _SilverMetadataSidecarRequest,
)

__all__ = [
    "_PreparedSilverWriteFinalizationContext",
    "_build_direct_legacy_silver_metadata",
    "_finalize_silver_write_result",
    "_prepare_silver_write_finalization_context",
]


class _MetadataFinalizationOps(Protocol):
    """Minimal host surface needed by finalization helpers."""

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


def _build_direct_legacy_silver_metadata(
    *,
    table_name: str,
    table_path: str,
    records: list[BronzeRecord],
    started_at: datetime,
    completed_at: datetime,
    run_id: str,
    manifest_id: str | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
) -> SilverMetadata:
    """Build metadata for the isolated direct-writer compatibility fallback."""
    return _build_silver_sidecar_metadata(
        _SilverMetadataSidecarRequest(
            table_name=table_name,
            table_path=table_path,
            records=records,
            dq_metrics=None,
            mode="merge",
            runtime_started_at=started_at,
            runtime_completed_at=completed_at,
            run_id=run_id or "legacy-direct-metadata-writer",
            manifest_id=manifest_id,
            run_type="incremental",
            source_batch_id=None,
            transform_version=transform_version,
            transform_steps=transform_steps,
            bronze_refs=None,
            version_after=None,
        )
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
    run_id = (
        str(request.records[0]["_run_id"])
        if request.records and "_run_id" in request.records[0]
        else "test_run_id"
    )
    metadata = _build_silver_sidecar_metadata(
        _SilverMetadataSidecarRequest(
            table_name=request.table_name,
            table_path=request.table_path,
            records=request.records,
            dq_metrics=context.dq_metrics,
            mode="merge",
            runtime_started_at=request.started_at,
            runtime_completed_at=context.completed_at,
            run_id=run_id,
            manifest_id=metadata_ops._resolve_manifest_id(records=request.records),
            run_type=RunTypeEnum.INCREMENTAL,
            source_batch_id=request.source_batch_id,
            transform_version=None,
            transform_steps=None,
            bronze_refs=request.bronze_refs,
            primary_keys=request.primary_keys,
            version_after=context.version_after,
            hostname="test-host",
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
