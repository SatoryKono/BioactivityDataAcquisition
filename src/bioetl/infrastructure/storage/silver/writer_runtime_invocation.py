"""Invocation and compatibility helpers for the Silver writer runtime facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, cast

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.ports import SilverWriteRequest, coerce_silver_write_request
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
    _prepare_silver_merged_metadata_write,
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _build_silver_merged_metadata_write_request,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
    _SilverPayloadPreparationHostProtocol,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteInvocation,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _SilverWriterDispatchHost,
    _write_single_target_impl,
)

__all__ = [
    "_coerce_silver_write_invocation",
    "_prepare_silver_write_payload_via_validation",
    "_validate_single_target_compat",
    "_write_merged_metadata_via_operations",
    "_write_single_target_with_historical_trace",
]

_ExecuteWithTracing = Callable[..., Awaitable[SilverWriteResult | None]]


def _validate_single_target_compat(
    *,
    invocation: _SilverWriteInvocation,
    table_name: str | None,
    run_id: object | None,
    run_type: object | None,
    source_batch_id: object | None,
    ingestion_ts: object | None,
) -> None:
    """Validate legacy keyword compatibility for one-target writes."""
    if table_name is not None and table_name != invocation.table_name:
        raise TypeError("table_name does not match invocation.table_name")
    if run_id is not None and run_id != invocation.run_id:
        raise TypeError("run_id does not match invocation.run_id")
    if run_type is not None and run_type != invocation.run_type:
        raise TypeError("run_type does not match invocation.run_type")
    if source_batch_id is not None and source_batch_id != invocation.source_batch_id:
        raise TypeError("source_batch_id does not match invocation.source_batch_id")
    if ingestion_ts is not None and ingestion_ts != invocation.ingestion_ts:
        raise TypeError("ingestion_ts does not match invocation.ingestion_ts")


async def _write_single_target_with_historical_trace(
    writer: object,
    *,
    invocation: _SilverWriteInvocation,
    execute_with_tracing: _ExecuteWithTracing,
) -> SilverWriteResult | None:
    """Execute one physical Silver write target with the historical trace name."""
    return await _write_single_target_impl(
        cast(_SilverWriterDispatchHost, writer),
        invocation=invocation,
        execute_with_tracing=execute_with_tracing,
        module_name="bioetl.infrastructure.storage.silver_writer",
    )


async def _prepare_silver_write_payload_via_validation(
    writer: object,
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
) -> _PreparedSilverWritePayload:
    """Prepare a validated Silver payload through the validation service."""
    return await _prepare_silver_write_payload_impl(
        cast(_SilverPayloadPreparationHostProtocol, writer),
        table_name=table_name,
        records=records,
        primary_keys=primary_keys,
        schema=schema,
        mode=mode,
        on_schema_mismatch=on_schema_mismatch,
        column_order=column_order,
        partition_cols=partition_cols,
        key_nullability_rules=key_nullability_rules,
    )


def _coerce_silver_write_invocation(
    request: SilverWriteRequest | str | None,
    *,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> _SilverWriteInvocation:
    """Normalize public write_silver args into one runtime invocation object."""
    write_request = coerce_silver_write_request(request, args=args, kwargs=kwargs)
    return _SilverWriteInvocation(
        table_name=write_request.table_name,
        records=write_request.records,
        primary_keys=write_request.primary_keys,
        schema=write_request.schema,
        mode=write_request.mode,
        partition_cols=write_request.partition_cols,
        on_schema_mismatch=write_request.on_schema_mismatch,
        column_order=write_request.column_order,
        bronze_refs=write_request.bronze_refs,
        key_nullability_rules=write_request.key_nullability_rules,
        run_id=write_request.run_id,
        run_type=write_request.run_type,
        source_batch_id=write_request.source_batch_id,
        ingestion_ts=write_request.ingestion_ts,
        quarantined_count=write_request.quarantined_count,
        validation_errors=write_request.validation_errors,
    )


def _resolve_completed_at(value: str | datetime | None) -> datetime | None:
    """Normalize merged-metadata completion timestamps."""
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, str)
        else value
    )


async def _write_merged_metadata_via_operations(
    writer: object,
    *,
    table_path: str,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str],
    completed_at: str | datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
) -> None:
    """Write merged Silver metadata through the canonical metadata operation path."""
    if getattr(writer, "_metadata", None) is None:
        raise RuntimeError("Silver metadata operations are required")
    if writer._should_skip_silver_metadata_write(records=records):  # type: ignore[attr-defined]
        return
    await _execute_silver_metadata_write(
        cast(_SilverMetadataWriteHostProtocol, writer),
        request=_build_silver_merged_metadata_write_request(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=_resolve_completed_at(completed_at),
            run_id=run_id,
            sources_used=sources_used,
        ),
        prepare=_prepare_silver_merged_metadata_write,
    )
