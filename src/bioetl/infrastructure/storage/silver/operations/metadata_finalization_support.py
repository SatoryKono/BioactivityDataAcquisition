"""Finalization helpers for composition-backed Silver metadata operations."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from bioetl.domain.models.metadata import RunTypeEnum
from bioetl.domain.types import BatchID, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.operations.metadata_builders import (
    _build_silver_metadata,
    _SilverMetadataBuildRequest,
)


@dataclass(frozen=True, slots=True)
class _PreparedSilverWriteFinalizationContext:
    """Prepared metadata/result context for one completed Silver write."""

    dq_metrics: BatchDQMetrics
    version_after: int | None
    completed_at: datetime


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
        metadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None: ...

    def _resolve_manifest_id(self, *, records: list[BronzeRecord]) -> str | None: ...

    async def _prepare_silver_write_finalization_context(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        primary_keys: list[str],
        validated_mode,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
        started_at: datetime,
        start_perf: float,
    ) -> _PreparedSilverWriteFinalizationContext: ...


async def _prepare_silver_write_finalization_context(
    metadata_ops: _MetadataFinalizationOps,
    *,
    table_name: str,
    records: list[BronzeRecord],
    table_path: str,
    primary_keys: list[str],
    validated_mode,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
    started_at: datetime,
    start_perf: float,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    del primary_keys, validated_mode

    dq_metrics = await metadata_ops._resolve_finalization_dq_metrics(
        table_name=table_name,
        records=records,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
    )
    version_after = await metadata_ops._resolve_version_after(table_path)
    completed_at = started_at + timedelta(seconds=time.perf_counter() - start_perf)
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )


async def _finalize_silver_write_result(
    metadata_ops: _MetadataFinalizationOps,
    *,
    table_name: str,
    records: list[BronzeRecord],
    table_path: str,
    primary_keys: list[str],
    validated_mode,
    bronze_refs: list[BronzeWriteResult] | None,
    partition_cols: list[str] | None,
    source_batch_id: BatchID | None,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
    started_at: datetime,
    start_perf: float,
) -> SilverWriteResult | None:
    """Compute DQ metrics, write metadata, and build final result."""
    del partition_cols

    context = await metadata_ops._prepare_silver_write_finalization_context(
        table_name=table_name,
        records=records,
        table_path=table_path,
        primary_keys=primary_keys,
        validated_mode=validated_mode,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
        started_at=started_at,
        start_perf=start_perf,
    )
    run_id = (
        str(records[0]["_run_id"])
        if records and "_run_id" in records[0]
        else "test_run_id"
    )
    metadata = _build_silver_metadata(
        _SilverMetadataBuildRequest(
            table_name=table_name,
            table_path=table_path,
            records=records,
            dq_metrics=context.dq_metrics,
            mode="merge",
            runtime_started_at=started_at,
            runtime_completed_at=context.completed_at,
            run_id=run_id,
            manifest_id=metadata_ops._resolve_manifest_id(records=records),
            run_type=RunTypeEnum.INCREMENTAL,
            source_batch_id=source_batch_id,
            transform_version=None,
            transform_steps=None,
            bronze_refs=bronze_refs,
            primary_keys=primary_keys,
            version_after=context.version_after,
            hostname="test-host",
        )
    )
    await metadata_ops._persist_silver_metadata(
        metadata=metadata,
        table_name=table_name,
        table_path=table_path,
    )
    return SilverWriteResult(
        table_name=table_name,
        table_path=table_path,
        delta_version=context.version_after or 0,
        record_count=len(records),
    )
