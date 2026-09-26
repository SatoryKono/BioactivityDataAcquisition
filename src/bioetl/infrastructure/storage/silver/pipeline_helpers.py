"""Pipeline helper objects for Silver write orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import _NoOpSpan
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
    _SilverWritePreparationRequest,
)

__all__ = [
    "_SilverWriteExecutionContext",
    "_SilverWriteInvocation",
    "build_delta_write_request",
    "build_silver_write_execution_context",
    "dispatch_prepared_silver_write",
    "execute_silver_write_pipeline",
    "execute_silver_write_with_tracing",
    "set_silver_write_span_attributes",
]


@dataclass(frozen=True, slots=True)
class _SilverWriteExecutionContext:
    """Immutable execution context carried through the Silver write pipeline."""

    table_name: str
    primary_keys: list[str]
    schema: pa.Schema
    mode: str
    partition_cols: list[str] | None
    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    column_order: list[str] | None
    bronze_refs: list[BronzeWriteResult] | None
    key_nullability_rules: list[KeyNullabilityRule] | None
    run_id: RunID | None
    run_type: RunType | None
    source_batch_id: BatchID | None
    ingestion_ts: datetime | None
    started_at: datetime
    start_perf: float
    span: Any  # Any: OpenTelemetry span interface is runtime-dependent
    quarantined_count: int | None = None
    validation_errors: Sequence[str] | None = None


@dataclass(frozen=True, slots=True)
class _SilverWriteInvocation(_SilverWritePreparationRequest):
    """Immutable write request shared across tracing and pipeline stages."""

    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    bronze_refs: list[BronzeWriteResult] | None
    run_id: RunID | None
    run_type: RunType | None
    source_batch_id: BatchID | None
    ingestion_ts: datetime | None
    quarantined_count: int | None = None
    validation_errors: Sequence[str] | None = None


class _PreparedSilverWriteDispatcher(Protocol):
    """Callable contract for dispatching prepared Silver write payloads."""

    def __call__(
        self,
        *,
        table_name: str,
        request: _DeltaWriteRequest,
    ) -> Awaitable[None]: ...


class _PreparedSilverWritePayloadBuilder(Protocol):
    """Async contract for Silver payload preparation."""

    def __call__(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> Awaitable[_PreparedSilverWritePayload]: ...


class _SilverWritePipelineCompleter(Protocol):
    """Async contract for finalizing one prepared Silver write."""

    def __call__(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        payload: _PreparedSilverWritePayload,
    ) -> Awaitable[SilverWriteResult | None]: ...


class _SilverWritePipelineRunner(Protocol):
    """Async contract for running one Silver write pipeline within a span."""

    def __call__(
        self,
        *,
        invocation: _SilverWriteInvocation,
        ctx: _SilverWriteExecutionContext,
    ) -> Awaitable[SilverWriteResult | None]: ...


def _parse_table_identity(table_name: str) -> tuple[str | None, str | None]:
    """Extract provider/entity identity from common Silver table-name formats."""
    for separator in ("/", ".", "_"):
        if separator not in table_name:
            continue
        provider, entity_type = table_name.split(separator, 1)
        if provider and entity_type:
            return provider, entity_type
    return None, None


def set_silver_write_span_attributes(
    span: Any,  # Any: OpenTelemetry span type varies by backend
    *,
    table_name: str,
    mode: str,
    record_count: int,
    run_id: RunID | None,
    run_type: RunType | None,
) -> None:
    """Populate core tracing attributes for a Silver write span."""
    provider, entity_type = _parse_table_identity(table_name)
    pipeline_run_id = str(run_id) if run_id is not None else None
    normalized_run_type = (
        str(getattr(run_type, "value", run_type)) if run_type is not None else None
    )

    span.set_attribute("table_name", table_name)
    span.set_attribute("mode", mode)
    span.set_attribute("record_count", record_count)
    span.set_attribute("bioetl.table_name", table_name)
    span.set_attribute("bioetl.write_mode", mode)
    span.set_attribute("bioetl.record_count", record_count)
    if provider is not None:
        span.set_attribute("bioetl.provider", provider)
    if entity_type is not None:
        span.set_attribute("bioetl.entity_type", entity_type)
    if pipeline_run_id is not None:
        span.set_attribute("bioetl.pipeline_run_id", pipeline_run_id)
    if normalized_run_type is not None:
        span.set_attribute("bioetl.run_type", normalized_run_type)


def build_silver_write_execution_context(
    *,
    invocation: _SilverWriteInvocation,
    started_at: datetime,
    start_perf: float,
    span: Any,  # Any: OpenTelemetry span type varies by backend
) -> _SilverWriteExecutionContext:
    """Build immutable execution context for the Silver write pipeline."""
    return _SilverWriteExecutionContext(
        table_name=invocation.table_name,
        primary_keys=invocation.primary_keys,
        schema=invocation.schema,
        mode=invocation.mode,
        partition_cols=invocation.partition_cols,
        on_schema_mismatch=invocation.on_schema_mismatch,
        column_order=invocation.column_order,
        bronze_refs=invocation.bronze_refs,
        key_nullability_rules=invocation.key_nullability_rules,
        run_id=invocation.run_id,
        run_type=invocation.run_type,
        source_batch_id=invocation.source_batch_id,
        ingestion_ts=invocation.ingestion_ts,
        quarantined_count=invocation.quarantined_count,
        validation_errors=invocation.validation_errors,
        started_at=started_at,
        start_perf=start_perf,
        span=span,
    )


def build_delta_write_request(
    *,
    ctx: _SilverWriteExecutionContext,
    payload: _PreparedSilverWritePayload,
) -> _DeltaWriteRequest:
    """Create the Delta dispatch request from prepared payload and execution context."""
    return _DeltaWriteRequest(
        validated_mode=payload.validated_mode,
        table_path=payload.table_path,
        arrow_data=payload.arrow_data,
        primary_keys=ctx.primary_keys,
        partition_cols=ctx.partition_cols,
        schema_mode=payload.schema_mode,
        merge_schema=payload.merge_schema,
        operation_id=f"{payload.table_path}:{payload.validated_mode.value}",
    )


async def dispatch_prepared_silver_write(
    *,
    ctx: _SilverWriteExecutionContext,
    payload: _PreparedSilverWritePayload,
    dispatch_write: _PreparedSilverWriteDispatcher,
) -> None:
    """Record payload size on the span and dispatch the prepared Delta write."""
    ctx.span.set_attribute("record_count", len(payload.records))
    await dispatch_write(
        table_name=ctx.table_name,
        request=build_delta_write_request(
            ctx=ctx,
            payload=payload,
        ),
    )


async def execute_silver_write_pipeline(
    *,
    invocation: _SilverWriteInvocation,
    ctx: _SilverWriteExecutionContext,
    prepare_payload: _PreparedSilverWritePayloadBuilder,
    dispatch_write: _PreparedSilverWriteDispatcher,
    complete_pipeline: _SilverWritePipelineCompleter,
) -> SilverWriteResult | None:
    """Execute prepare, dispatch, and finalize stages for one Silver write."""
    payload = await prepare_payload(
        table_name=invocation.table_name,
        records=invocation.records,
        primary_keys=invocation.primary_keys,
        schema=invocation.schema,
        mode=invocation.mode,
        on_schema_mismatch=invocation.on_schema_mismatch,
        column_order=invocation.column_order,
        partition_cols=invocation.partition_cols,
        key_nullability_rules=invocation.key_nullability_rules,
    )
    await dispatch_prepared_silver_write(
        ctx=ctx,
        payload=payload,
        dispatch_write=dispatch_write,
    )
    return await complete_pipeline(
        ctx=ctx,
        payload=payload,
    )


async def execute_silver_write_with_tracing(
    *,
    tracing: TracingPort | None,
    module_name: str,
    invocation: _SilverWriteInvocation,
    started_at: datetime,
    start_perf: float,
    execute_pipeline: _SilverWritePipelineRunner,
) -> SilverWriteResult | None:
    """Create the tracing span/context and delegate the Silver write pipeline."""
    span_context = (
        tracing.get_tracer(module_name).start_as_current_span("write_silver")
        if tracing is not None
        else _NoOpSpan()
    )
    with span_context as span:
        set_silver_write_span_attributes(
            span,
            table_name=invocation.table_name,
            mode=invocation.mode,
            record_count=len(invocation.records),
            run_id=invocation.run_id,
            run_type=invocation.run_type,
        )
        ctx = build_silver_write_execution_context(
            invocation=invocation,
            started_at=started_at,
            start_perf=start_perf,
            span=span,
        )
        return await execute_pipeline(
            invocation=invocation,
            ctx=ctx,
        )
