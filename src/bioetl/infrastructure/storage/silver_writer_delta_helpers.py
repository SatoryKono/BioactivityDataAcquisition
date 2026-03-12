"""Helper utilities for Silver Delta write dispatch and merge orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn

import pyarrow as pa
from deltalake.exceptions import DeltaError, SchemaMismatchError

from bioetl.domain.exceptions import (
    DeltaTransactionError,
    MergeConflictError,
    SchemaViolationError,
)
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.write_resilience import SilverMergeResiliencePolicy

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort, MetricsPort


class _MergeExecutionTimeoutError(RuntimeError):
    """Internal timeout marker used for merge retry orchestration."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Merge execution timed out after {timeout_seconds}s")


@dataclass(frozen=True, slots=True)
class _DeltaWriteRequest:
    """Normalized request object for a single Silver Delta write dispatch."""

    validated_mode: SilverWriteMode
    table_path: str
    arrow_data: pa.Table
    primary_keys: list[str]
    partition_cols: list[str] | None


_DeltaWriteHandler = Callable[[_DeltaWriteRequest], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class _DeltaWriteDispatchPolicy:
    """Mode-to-handler policy for a normalized Delta write request."""

    write_delete: _DeltaWriteHandler
    write_append: _DeltaWriteHandler
    write_merge: _DeltaWriteHandler


_RUN_TYPE_PRECEDENCE_PREDICATE = (
    "CASE "
    "WHEN source._run_type = 'rebuild' THEN 3 "
    "WHEN source._run_type = 'backfill' THEN 2 "
    "ELSE 1 END >= "
    "CASE "
    "WHEN target._run_type = 'rebuild' THEN 3 "
    "WHEN target._run_type = 'backfill' THEN 2 "
    "ELSE 1 END"
)


def _build_merge_condition(primary_keys: list[str]) -> str:
    """Build Delta merge predicate from primary key columns."""
    return " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)


def _build_merge_execute_callable(
    *,
    dt: DeltaTableType,
    records: pa.Table | pa.RecordBatchReader,
    merge_condition: str,
) -> Callable[[], Any]:
    """Build the blocking Delta merge callable for ``run_in_executor``."""

    def _execute() -> Any:  # Any: Delta merge returns heterogeneous result
        return (
            dt.merge(
                source=records,
                predicate=merge_condition,
                source_alias="source",
                target_alias="target",
            )
            .when_matched_update_all(predicate=_RUN_TYPE_PRECEDENCE_PREDICATE)
            .when_not_matched_insert_all()
            .execute()
        )

    return _execute


def _build_plain_delta_write_kwargs(
    request: _DeltaWriteRequest,
    *,
    mode: str,
    schema_mode: str | None = None,
) -> dict[str, Any]:  # Any: Delta Lake write kwargs are heterogeneous
    """Build keyword arguments for a non-merge Delta write."""
    kwargs: dict[str, Any] = {  # Any: heterogeneous kwargs dict
        "table_or_uri": request.table_path,
        "data": request.arrow_data,
        "mode": mode,
        "partition_by": request.partition_cols,
    }
    if schema_mode is not None:
        kwargs["schema_mode"] = schema_mode
    return kwargs


def _raise_domain_write_error(
    *,
    table_name: str,
    exc: SchemaMismatchError | pa.ArrowTypeError | DeltaError,
) -> NoReturn:
    """Translate Delta-layer write failures to domain errors when applicable."""
    if isinstance(exc, (SchemaMismatchError, pa.ArrowTypeError)):
        raise SchemaViolationError(table_name, errors=[str(exc)]) from exc
    if "Merge-conflict" in str(exc):
        raise MergeConflictError(table_name, conflicts=1) from exc
    raise exc


def _build_dispatch_policy(
    *,
    write_delete: _DeltaWriteHandler,
    write_append: _DeltaWriteHandler,
    write_merge: _DeltaWriteHandler,
) -> _DeltaWriteDispatchPolicy:
    """Build the Delta write dispatch policy for a writer instance."""
    return _DeltaWriteDispatchPolicy(
        write_delete=write_delete,
        write_append=write_append,
        write_merge=write_merge,
    )


def _select_dispatch_handler(
    *,
    validated_mode: SilverWriteMode,
    policy: _DeltaWriteDispatchPolicy,
) -> _DeltaWriteHandler:
    """Select the mode-specific write handler from the dispatch policy."""
    if validated_mode == SilverWriteMode.DELETE:
        return policy.write_delete
    if validated_mode == SilverWriteMode.APPEND:
        return policy.write_append
    return policy.write_merge


async def _dispatch_request_by_mode(
    *,
    request: _DeltaWriteRequest,
    policy: _DeltaWriteDispatchPolicy,
) -> None:
    """Dispatch a normalized Delta write request to the mode-specific handler."""
    handler = _select_dispatch_handler(
        validated_mode=request.validated_mode,
        policy=policy,
    )
    await handler(request)


async def _dispatch_request_with_domain_errors(
    *,
    table_name: str,
    request: _DeltaWriteRequest,
    dispatch_write: _DeltaWriteHandler,
) -> None:
    """Execute a Delta write dispatch and translate storage exceptions."""
    try:
        await dispatch_write(request)
    except (SchemaMismatchError, pa.ArrowTypeError, DeltaError) as exc:
        _raise_domain_write_error(table_name=table_name, exc=exc)


async def _write_plain_delta_request(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    request: _DeltaWriteRequest,
    mode: str,
    schema_mode: str | None = None,
) -> None:
    """Execute a non-merge Delta write for an already prepared request."""
    kwargs = _build_plain_delta_write_kwargs(
        request,
        mode=mode,
        schema_mode=schema_mode,
    )
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: load_module().write_deltalake(**kwargs),
    )


async def _load_delta_table(
    *,
    load_module: Callable[[], Any],  # Any: lazy-loaded deltalake module
    table_path: str,
) -> DeltaTableType:
    """Load a Delta table asynchronously for merge execution."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: load_module().DeltaTable(table_path),
    )


def _emit_merge_recovered_after_retry(
    *,
    logger: LoggerPort,
    table_path: str,
    commit_retry_count: int,
    timeout_retry_count: int,
) -> None:
    """Log successful merge recovery after one or more retry attempts."""
    if commit_retry_count == 0 and timeout_retry_count == 0:
        return
    logger.info(
        "silver_merge_recovered_after_retry",
        table_path=table_path,
        commit_retry_count=commit_retry_count,
        timeout_retry_count=timeout_retry_count,
        final_reason="success_after_retry",
    )


async def _handle_commit_retry(
    *,
    table_path: str,
    policy: SilverMergeResiliencePolicy,
    retry_count: int,
    emit_final: Callable[..., None],
    emit_retry: Callable[..., None],
) -> int | None:
    """Emit commit-conflict retry telemetry and sleep before next attempt."""
    if not policy.commit_retry.should_retry(retry_count):
        emit_final(
            table_path=table_path,
            final_reason="commit_conflict_retries_exhausted",
        )
        return None
    delay = policy.commit_retry.calculate_delay(retry_count)
    next_retry_count = retry_count + 1
    emit_retry(
        table_path=table_path,
        retry_type="commit_conflict",
        attempt=next_retry_count,
        max_retries=policy.commit_retry.max_retries,
        delay_seconds=delay,
    )
    if delay > 0.0:
        await asyncio.sleep(delay)
    return next_retry_count


async def _handle_timeout_retry(
    *,
    table_path: str,
    policy: SilverMergeResiliencePolicy,
    retry_count: int,
    cause: _MergeExecutionTimeoutError,
    emit_final: Callable[..., None],
    emit_retry: Callable[..., None],
) -> int:
    """Emit timeout retry telemetry and sleep before next merge attempt."""
    if not policy.timeout_retry.should_retry(retry_count):
        emit_final(
            table_path=table_path,
            final_reason="timeout_retries_exhausted",
        )
        raise DeltaTransactionError(
            table_path=table_path,
            reason=(
                "Delta merge_execute timed out after "
                f"{cause.timeout_seconds} seconds "
                f"(timeout_retries={retry_count})"
            ),
        ) from cause
    delay = policy.timeout_retry.calculate_delay(retry_count)
    next_retry_count = retry_count + 1
    emit_retry(
        table_path=table_path,
        retry_type="timeout",
        attempt=next_retry_count,
        max_retries=policy.timeout_retry.max_retries,
        delay_seconds=delay,
    )
    if delay > 0.0:
        await asyncio.sleep(delay)
    return next_retry_count


def _emit_merge_retry_event(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    table_path: str,
    retry_type: str,
    attempt: int,
    max_retries: int,
    delay_seconds: float,
) -> None:
    """Emit retry telemetry for a merge attempt."""
    logger.warning(
        "silver_merge_retry",
        table_path=table_path,
        retry_type=retry_type,
        attempt=attempt,
        max_retries=max_retries,
        delay_seconds=delay_seconds,
    )
    if metrics is not None:
        metrics.increment_counter(
            "observability_events_total",
            1,
            {
                "event": "silver_merge_retry",
                "provider": "storage",
                "pipeline": table_path,
                "severity": "warning",
                "error_type": retry_type,
            },
        )


def _emit_merge_final_event(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    table_path: str,
    final_reason: str,
) -> None:
    """Emit telemetry when merge retries are exhausted."""
    logger.error(
        "silver_merge_failed",
        table_path=table_path,
        final_reason=final_reason,
    )
    if metrics is not None:
        metrics.increment_counter(
            "observability_events_total",
            1,
            {
                "event": "silver_merge_final",
                "provider": "storage",
                "pipeline": table_path,
                "severity": "error",
                "error_type": final_reason,
            },
        )


async def _merge_records_with_timeout(
    *,
    logger: LoggerPort,
    dt: DeltaTableType,
    records: pa.Table | pa.RecordBatchReader,
    primary_keys: list[str],
    table_path: str,
    timeout_seconds: float,
) -> None:
    """Execute Delta merge with timeout handling and structured timeout telemetry."""
    merge_condition = _build_merge_condition(primary_keys)
    loop = asyncio.get_running_loop()
    merge_future = loop.run_in_executor(
        None,
        _build_merge_execute_callable(
            dt=dt,
            records=records,
            merge_condition=merge_condition,
        ),
    )
    try:
        await asyncio.wait_for(
            merge_future,
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        logger.warning(
            "silver_merge_timeout",
            table_path=table_path,
            timeout_seconds=timeout_seconds,
            primary_keys=primary_keys,
        )
        raise _MergeExecutionTimeoutError(timeout_seconds) from exc
