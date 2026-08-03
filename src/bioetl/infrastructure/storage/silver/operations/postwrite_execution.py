"""Postwrite request builders and shared execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyarrow as pa

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_protocols import (
    _SilverPostwriteExecutorProtocol,
    _SilverPostwriteFinalizerProtocol,
    _SilverPostwriteHostProtocol,
    _SilverWritePostwriteContext,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

__all__ = [
    "_SilverPostwriteAuditHookRequest",
    "_SilverPostwriteExportHookRequest",
    "_build_postwrite_audit_hook_request",
    "_build_postwrite_export_hook_request",
    "_complete_silver_write_pipeline_impl",
    "_finalize_silver_postwrite_result",
    "_run_postwrite_audit_via_host_hook",
    "_run_postwrite_export_via_host_hook",
]


@dataclass(frozen=True, slots=True)
class _SilverPostwriteExportHookRequest:
    """Normalized host-hook request for postwrite export delegation."""

    table_name: str
    arrow_data: pa.Table
    mode: str
    validated_mode: SilverWriteMode
    primary_keys: list[str]


@dataclass(frozen=True, slots=True)
class _SilverPostwriteAuditHookRequest:
    """Normalized host-hook request for postwrite audit delegation."""

    table_name: str
    records: list[BronzeRecord]
    mode: SilverWriteMode
    run_id: RunID | None
    run_type: RunType | None
    source_batch_id: BatchID | None
    ingestion_ts: datetime | None


def _build_postwrite_export_hook_request(
    *,
    ctx: _SilverWritePostwriteContext,
    payload: _PreparedSilverWritePayload,
) -> _SilverPostwriteExportHookRequest:
    """Build the normalized export request from postwrite ctx/payload."""
    return _SilverPostwriteExportHookRequest(
        table_name=ctx.table_name,
        arrow_data=payload.arrow_data,
        mode=ctx.mode,
        validated_mode=payload.validated_mode,
        primary_keys=ctx.primary_keys,
    )


def _build_postwrite_audit_hook_request(
    *,
    ctx: _SilverWritePostwriteContext,
    payload: _PreparedSilverWritePayload,
) -> _SilverPostwriteAuditHookRequest:
    """Build the normalized audit request from postwrite ctx/payload."""
    return _SilverPostwriteAuditHookRequest(
        table_name=ctx.table_name,
        records=payload.records,
        mode=payload.validated_mode,
        run_id=ctx.run_id,
        run_type=ctx.run_type,
        source_batch_id=ctx.source_batch_id,
        ingestion_ts=ctx.ingestion_ts,
    )


async def _run_postwrite_export_via_host_hook(
    host: _SilverPostwriteHostProtocol,
    *,
    request: _SilverPostwriteExportHookRequest,
) -> None:
    """Delegate postwrite export through the host hook."""
    await host._maybe_export_csv(
        table_name=request.table_name,
        arrow_data=request.arrow_data,
        mode=request.mode,
        validated_mode=request.validated_mode,
        primary_keys=request.primary_keys,
    )


async def _run_postwrite_audit_via_host_hook(
    host: _SilverPostwriteHostProtocol,
    *,
    request: _SilverPostwriteAuditHookRequest,
) -> None:
    """Delegate postwrite audit through the host hook."""
    await host._maybe_log_silver_audit(
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        run_id=request.run_id,
        run_type=request.run_type,
        source_batch_id=request.source_batch_id,
        ingestion_ts=request.ingestion_ts,
    )


async def _complete_silver_write_pipeline_impl(
    executor: _SilverPostwriteExecutorProtocol,
    *,
    ctx: _SilverWritePostwriteContext,
    payload: _PreparedSilverWritePayload,
) -> SilverWriteResult | None:
    """Run the shared postwrite sequence."""
    await executor._run_postwrite_export(
        ctx=ctx,
        payload=payload,
    )
    await executor._run_postwrite_audit(
        ctx=ctx,
        payload=payload,
    )
    return await executor._finalize_postwrite_result(
        ctx=ctx,
        payload=payload,
    )


async def _finalize_silver_postwrite_result(
    finalizer: _SilverPostwriteFinalizerProtocol,
    *,
    ctx: _SilverWritePostwriteContext,
    payload: _PreparedSilverWritePayload,
) -> SilverWriteResult | None:
    """Finalize a postwrite payload using the shared ctx/payload contract."""
    validation_errors = getattr(ctx, "validation_errors", None)
    return await finalizer(
        _SilverWriteResultFinalizationRequest(
            table_name=ctx.table_name,
            records=payload.records,
            table_path=payload.table_path,
            primary_keys=ctx.primary_keys,
            validated_mode=payload.validated_mode,
            bronze_refs=ctx.bronze_refs,
            partition_cols=ctx.partition_cols,
            source_batch_id=ctx.source_batch_id,
            started_at=ctx.started_at,
            start_perf=ctx.start_perf,
            quarantined_count=getattr(ctx, "quarantined_count", None),
            validation_errors=(
                tuple(validation_errors) if validation_errors is not None else None
            ),
        )
    )
