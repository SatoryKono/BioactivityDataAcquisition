"""Implementation helpers for Silver Delta operation facades."""

from __future__ import annotations

import pyarrow as pa
from deltalake import DeltaTable as DeltaTableType

from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _build_dispatch_policy,
    _DeltaWriteRequest,
    _dispatch_request_by_mode,
    _dispatch_request_with_domain_errors,
    _merge_records_with_timeout,
    _write_plain_delta_request,
)
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _emit_merge_final_event,
    _emit_merge_retry_event,
    _execute_merge_write_request,
)
from bioetl.infrastructure.storage.silver.operations.delta_operation_protocols import (
    _SilverDeltaHostProtocol,
)

__all__ = [
    "_dispatch_write_impl",
    "_dispatch_write_with_domain_errors_impl",
    "_emit_merge_final_telemetry_impl",
    "_emit_merge_retry_telemetry_impl",
    "_merge_records_impl",
    "_write_append_impl",
    "_write_delete_impl",
    "_write_merge_impl",
]


def _resolve_merge_policy(
    host: _SilverDeltaHostProtocol,
) -> SilverMergeResiliencePolicy:
    """Resolve the configured merge policy with the canonical default fallback."""
    return (
        getattr(
            host,
            "_merge_resilience_policy",
            DEFAULT_SILVER_MERGE_POLICY,
        )
        or DEFAULT_SILVER_MERGE_POLICY
    )


async def _write_delete_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data in delete mode (overwrite table)."""
    policy = _resolve_merge_policy(host)
    await _write_plain_delta_request(
        load_module=host._load_silver_writer_module,
        request=request,
        mode="overwrite",
        schema_mode="overwrite",
        timeout_seconds=policy.execution_timeout_seconds,
        process_isolation=policy.plain_write_process_isolation,
    )


async def _write_append_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data in append mode."""
    policy = _resolve_merge_policy(host)
    await _write_plain_delta_request(
        load_module=host._load_silver_writer_module,
        request=request,
        mode="append",
        schema_mode=request.schema_mode,
        timeout_seconds=policy.execution_timeout_seconds,
        process_isolation=policy.plain_write_process_isolation,
    )


async def _write_create_table_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Create a missing Delta table for merge fallback without append semantics."""
    policy = _resolve_merge_policy(host)
    await _write_plain_delta_request(
        load_module=host._load_silver_writer_module,
        request=request,
        mode="overwrite",
        schema_mode="overwrite",
        timeout_seconds=policy.execution_timeout_seconds,
        process_isolation=policy.plain_write_process_isolation,
    )


async def _write_merge_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data using merge/upsert strategy with conflict retry."""
    await _execute_merge_write_request(
        request=request,
        policy=_resolve_merge_policy(host),
        load_module=host._load_silver_writer_module,
        write_append=host._write_append,
        write_create=lambda active_request: _write_create_table_impl(
            host,
            active_request,
        ),
        merge_records=host._merge_records,
        emit_final=host._emit_merge_final_telemetry,
        emit_retry=host._emit_merge_retry_telemetry,
        logger=host._logger,
    )


async def _dispatch_write_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Dispatch write call by mode."""
    await _dispatch_request_by_mode(
        request=request,
        policy=_build_dispatch_policy(
            write_delete=host._write_delete,
            write_append=host._write_append,
            write_merge=host._write_merge,
        ),
    )


async def _merge_records_impl(
    host: _SilverDeltaHostProtocol,
    dt: DeltaTableType,
    records: pa.Table | pa.RecordBatchReader,
    primary_keys: list[str],
    table_path: str,
    *,
    timeout_seconds: float,
    merge_schema: bool = False,
) -> None:
    """Merge records into an existing Delta table."""
    await _merge_records_with_timeout(
        logger=host._logger,
        dt=dt,
        records=records,
        primary_keys=primary_keys,
        table_path=table_path,
        timeout_seconds=timeout_seconds,
        merge_schema=merge_schema,
    )


def _emit_merge_retry_telemetry_impl(
    host: _SilverDeltaHostProtocol,
    *,
    table_path: str,
    retry_type: str,
    attempt: int,
    max_retries: int,
    delay_seconds: float,
) -> None:
    """Emit telemetry for a merge retry attempt."""
    _emit_merge_retry_event(
        logger=host._logger,
        metrics=host._metrics,
        table_path=table_path,
        retry_type=retry_type,
        attempt=attempt,
        max_retries=max_retries,
        delay_seconds=delay_seconds,
    )


def _emit_merge_final_telemetry_impl(
    host: _SilverDeltaHostProtocol,
    *,
    table_path: str,
    final_reason: str,
) -> None:
    """Emit telemetry when merge retries are exhausted."""
    _emit_merge_final_event(
        logger=host._logger,
        metrics=host._metrics,
        table_path=table_path,
        final_reason=final_reason,
    )


async def _dispatch_write_with_domain_errors_impl(
    host: _SilverDeltaHostProtocol,
    *,
    table_name: str,
    request: _DeltaWriteRequest,
) -> None:
    """Dispatch write and translate infrastructure errors to domain errors."""
    await _dispatch_request_with_domain_errors(
        table_name=table_name,
        request=request,
        dispatch_write=host._dispatch_write,
    )
