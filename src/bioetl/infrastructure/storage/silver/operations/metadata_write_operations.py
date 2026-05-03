"""Write-path helper bindings for Silver metadata operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol, cast

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _coerce_silver_metadata_write_request,
    _prepare_silver_merged_metadata_write,
    _prepare_silver_metadata_write,
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _build_silver_merged_metadata_write_request,
    _SilverMergedMetadataWriteRequest,
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _SilverMetadataWriteSupportRequest,
    _write_silver_metadata,
)


class _SilverMetadataWriteOps(Protocol):
    """Minimal facade surface needed by Silver metadata write helpers."""

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool: ...


_ExecuteSilverMetadataWrite = Callable[
    [
        _SilverMetadataWriteHostProtocol,
        _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest,
        Callable[..., Awaitable[object]],
    ],
    Awaitable[None],
]


async def write_silver_metadata_via_support_request(
    metadata_ops: _SilverMetadataWriteOps,
    *,
    table_name: str,
    dq_metrics: BatchDQMetrics,
    records: list[BronzeRecord],
    bronze_refs: list[BronzeWriteResult] | None = None,
    mode: str = "merge",
    validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
    run_id: RunID | None = None,
    run_type: RunType | None = None,
    source_batch_id: BatchID | None = None,
    ingestion_ts: datetime | None = None,
    transform_version: str | None = None,
    transform_steps: tuple[str, ...] | None = None,
) -> SilverWriteResult | None:
    """Write Silver metadata through the canonical support request adapter."""
    return await _write_silver_metadata(
        metadata_ops,
        _SilverMetadataWriteSupportRequest(
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        ),
    )


async def write_internal_silver_metadata_operation(
    metadata_ops: _SilverMetadataWriteOps,
    request: _SilverMetadataWriteRequest | str | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
    execute_silver_metadata_write: _ExecuteSilverMetadataWrite,
) -> None:
    """Canonical Silver metadata publication path for composition-backed ops."""
    resolved_request = _coerce_silver_metadata_write_request(
        request,
        args=args,
        kwargs=kwargs or {},
    )
    if metadata_ops._should_skip_silver_metadata_write(
        records=resolved_request.records,
        table_path=resolved_request.table_path,
        event_name="silver_metadata_skipped",
    ):
        return
    await execute_silver_metadata_write(
        cast(_SilverMetadataWriteHostProtocol, metadata_ops),
        resolved_request,
        _prepare_silver_metadata_write,
    )


async def write_silver_merged_metadata_operation(
    metadata_ops: _SilverMetadataWriteOps,
    *,
    table_path: str,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str],
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
    execute_silver_metadata_write: _ExecuteSilverMetadataWrite,
) -> None:
    """Canonical Silver metadata publication path for merged composite writes."""
    if metadata_ops._should_skip_silver_metadata_write(
        records=records,
        table_path=table_path,
        event_name="silver_merged_metadata_skipped",
    ):
        return
    await execute_silver_metadata_write(
        cast(_SilverMetadataWriteHostProtocol, metadata_ops),
        _build_silver_merged_metadata_write_request(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
        ),
        _prepare_silver_merged_metadata_write,
    )
