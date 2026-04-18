"""Helper utilities for Silver merge retry and telemetry orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import DeltaTransactionError
from bioetl.domain.observability_contract import normalize_observability_pipeline_label
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _DeltaWriteRequest,
    _evolve_delta_schema_with_empty_append,
    _is_duplicate_field_name_schema_error,
    _load_delta_table,
    _MergeExecutionTimeoutError,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


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


async def _pre_evolve_existing_table_schema(
    *,
    request: _DeltaWriteRequest,
    load_module: Callable[[], Any],  # Any: silver_writer module is loaded lazily
) -> tuple[_DeltaWriteRequest, bool]:
    """Pre-evolve schema only when merge-schema targets an existing table."""
    if not request.merge_schema:
        return request, False
    try:
        await _load_delta_table(
            load_module=load_module,
            table_path=request.table_path,
        )
    except DeltaTableNotFoundError:
        return request, False
    evolved_request = await _evolve_delta_schema_with_empty_append(
        load_module=load_module,
        request=request,
    )
    return evolved_request, True


async def _maybe_pre_evolve_on_duplicate_field_error(
    *,
    exc: BaseException,
    request: _DeltaWriteRequest,
    schema_pre_evolved: bool,
    load_module: Callable[[], Any],  # Any: silver_writer module is loaded lazily
) -> tuple[_DeltaWriteRequest, bool] | None:
    """Pre-evolve schema on the known duplicate-field merge quirk."""
    if (
        not request.merge_schema
        or schema_pre_evolved
        or not _is_duplicate_field_name_schema_error(exc)
    ):
        return None
    evolved_request = await _evolve_delta_schema_with_empty_append(
        load_module=load_module,
        request=request,
    )
    return evolved_request, True


async def _handle_merge_execution_error(
    *,
    exc: Exception,
    active_request: _DeltaWriteRequest,
    schema_pre_evolved: bool,
    timeout_retry_count: int,
    policy: SilverMergeResiliencePolicy,
    load_module: Callable[[], Any],
    emit_final: Callable[..., None],
    emit_retry: Callable[..., None],
) -> tuple[_DeltaWriteRequest, bool, int]:
    """Handle timeout retries and duplicate-field schema recovery."""
    if isinstance(exc, _MergeExecutionTimeoutError):
        next_timeout_retry_count = await _handle_timeout_retry(
            table_path=active_request.table_path,
            policy=policy,
            retry_count=timeout_retry_count,
            cause=exc,
            emit_final=emit_final,
            emit_retry=emit_retry,
        )
        return active_request, schema_pre_evolved, next_timeout_retry_count

    evolved = await _maybe_pre_evolve_on_duplicate_field_error(
        exc=exc,
        request=active_request,
        schema_pre_evolved=schema_pre_evolved,
        load_module=load_module,
    )
    if evolved is None:
        raise exc
    next_request, next_schema_pre_evolved = evolved
    return next_request, next_schema_pre_evolved, timeout_retry_count


async def _execute_merge_write_request(
    *,
    request: _DeltaWriteRequest,
    policy: SilverMergeResiliencePolicy,
    load_module: Callable[[], Any],  # Any: silver_writer module varies at runtime
    write_append: Callable[[_DeltaWriteRequest], Awaitable[None]],
    merge_records: Callable[..., Awaitable[None]],
    emit_final: Callable[..., None],
    emit_retry: Callable[..., None],
    logger: LoggerPort,
) -> None:
    """Execute merge/upsert with retry, timeout, and append-fallback orchestration."""
    active_request, schema_pre_evolved = await _pre_evolve_existing_table_schema(
        request=request,
        load_module=load_module,
    )
    commit_retry_count = 0
    timeout_retry_count = 0

    while True:
        try:
            table = await _load_delta_table(
                load_module=load_module,
                table_path=active_request.table_path,
            )
            await merge_records(
                table,
                active_request.arrow_data,
                active_request.primary_keys,
                active_request.table_path,
                timeout_seconds=policy.execution_timeout_seconds,
                merge_schema=active_request.merge_schema,
            )
            _emit_merge_recovered_after_retry(
                logger=logger,
                table_path=active_request.table_path,
                commit_retry_count=commit_retry_count,
                timeout_retry_count=timeout_retry_count,
            )
            return
        except DeltaTableNotFoundError:
            await write_append(active_request)
            return
        except CommitFailedError:
            next_commit_retry_count = await _handle_commit_retry(
                table_path=active_request.table_path,
                policy=policy,
                retry_count=commit_retry_count,
                emit_final=emit_final,
                emit_retry=emit_retry,
            )
            if next_commit_retry_count is None:
                raise
            commit_retry_count = next_commit_retry_count
        except Exception as exc:
            (
                active_request,
                schema_pre_evolved,
                timeout_retry_count,
            ) = await _handle_merge_execution_error(
                exc=exc,
                active_request=active_request,
                schema_pre_evolved=schema_pre_evolved,
                timeout_retry_count=timeout_retry_count,
                policy=policy,
                load_module=load_module,
                emit_final=emit_final,
                emit_retry=emit_retry,
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
    pipeline_label = normalize_observability_pipeline_label(table_path)
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
            "bioetl_silver_merge_retries_total",
            1,
            {
                "pipeline": pipeline_label,
                "retry_type": retry_type,
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
    pipeline_label = normalize_observability_pipeline_label(table_path)
    logger.error(
        "silver_merge_failed",
        table_path=table_path,
        final_reason=final_reason,
    )
    if metrics is not None:
        metrics.increment_counter(
            "bioetl_silver_merge_failures_total",
            1,
            {
                "pipeline": pipeline_label,
                "final_reason": final_reason,
            },
        )
