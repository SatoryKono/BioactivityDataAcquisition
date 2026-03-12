"""Delta operation helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterDeltaMixin"]

from typing import TYPE_CHECKING, Any

import pyarrow as pa
from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.infrastructure.storage.silver_writer_delta_helpers import (
    _build_dispatch_policy,
    _DeltaWriteRequest,
    _dispatch_request_by_mode,
    _dispatch_request_with_domain_errors,
    _emit_merge_final_event,
    _emit_merge_recovered_after_retry,
    _emit_merge_retry_event,
    _handle_commit_retry,
    _handle_timeout_retry,
    _load_delta_table,
    _merge_records_with_timeout,
    _MergeExecutionTimeoutError,
    _raise_domain_write_error,
    _select_dispatch_handler,
    _write_plain_delta_request,
)
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort, MetricsPort


class SilverWriterDeltaMixin:
    """Mixin with Delta write/merge operations."""

    logger: LoggerPort
    _metrics: MetricsPort | None
    _merge_resilience_policy: SilverMergeResiliencePolicy

    @property
    def _logger(self) -> LoggerPort:
        """Access logger via private convention for delegation pattern compliance."""
        return self.logger

    @staticmethod
    def _load_silver_writer_module() -> Any:  # Any: return type varies at runtime
        """Load silver_writer module for backward-compatible patch points."""
        from bioetl.infrastructure.storage import silver_writer as silver_writer_module

        return silver_writer_module

    async def _write_delete(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data in delete mode (overwrite table)."""
        await _write_plain_delta_request(
            load_module=self._load_silver_writer_module,
            request=request,
            mode="overwrite",
            schema_mode="overwrite",
        )

    async def _write_append(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data in append mode."""
        await _write_plain_delta_request(
            load_module=self._load_silver_writer_module,
            request=request,
            mode="append",
        )

    async def _write_merge(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data using merge/upsert strategy with conflict retry."""
        policy = getattr(
            self,
            "_merge_resilience_policy",
            DEFAULT_SILVER_MERGE_POLICY,
        )
        commit_retry_count = 0
        timeout_retry_count = 0

        while True:
            try:
                table = await _load_delta_table(
                    load_module=self._load_silver_writer_module,
                    table_path=request.table_path,
                )
                await self._merge_records(
                    table,
                    request.arrow_data,
                    request.primary_keys,
                    request.table_path,
                    timeout_seconds=policy.execution_timeout_seconds,
                )
                _emit_merge_recovered_after_retry(
                    logger=self._logger,
                    table_path=request.table_path,
                    commit_retry_count=commit_retry_count,
                    timeout_retry_count=timeout_retry_count,
                )
                return
            except DeltaTableNotFoundError:
                await self._write_append(request)
                return
            except CommitFailedError:
                next_commit_retry_count = await _handle_commit_retry(
                    table_path=request.table_path,
                    policy=policy,
                    retry_count=commit_retry_count,
                    emit_final=self._emit_merge_final_telemetry,
                    emit_retry=self._emit_merge_retry_telemetry,
                )
                if next_commit_retry_count is None:
                    raise
                commit_retry_count = next_commit_retry_count
            except _MergeExecutionTimeoutError as exc:
                timeout_retry_count = await _handle_timeout_retry(
                    table_path=request.table_path,
                    policy=policy,
                    retry_count=timeout_retry_count,
                    cause=exc,
                    emit_final=self._emit_merge_final_telemetry,
                    emit_retry=self._emit_merge_retry_telemetry,
                )

    async def _dispatch_write(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch write call by mode."""
        await _dispatch_request_by_mode(
            request=request,
            policy=_build_dispatch_policy(
                write_delete=self._write_delete,
                write_append=self._write_append,
                write_merge=self._write_merge,
            ),
        )

    async def _merge_records(
        self,
        dt: DeltaTableType,
        records: pa.Table | pa.RecordBatchReader,
        primary_keys: list[str],
        table_path: str,
        *,
        timeout_seconds: float,
    ) -> None:
        """Merge records into an existing Delta table."""
        await _merge_records_with_timeout(
            logger=self._logger,
            dt=dt,
            records=records,
            primary_keys=primary_keys,
            table_path=table_path,
            timeout_seconds=timeout_seconds,
        )

    def _emit_merge_retry_telemetry(
        self,
        *,
        table_path: str,
        retry_type: str,
        attempt: int,
        max_retries: int,
        delay_seconds: float,
    ) -> None:
        """Emit telemetry for a merge retry attempt."""
        _emit_merge_retry_event(
            logger=self._logger,
            metrics=self._metrics,
            table_path=table_path,
            retry_type=retry_type,
            attempt=attempt,
            max_retries=max_retries,
            delay_seconds=delay_seconds,
        )

    def _emit_merge_final_telemetry(
        self, *, table_path: str, final_reason: str
    ) -> None:
        """Emit telemetry when merge retries are exhausted."""
        _emit_merge_final_event(
            logger=self._logger,
            metrics=self._metrics,
            table_path=table_path,
            final_reason=final_reason,
        )

    async def _dispatch_write_with_domain_errors(
        self,
        *,
        table_name: str,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch write and translate infrastructure errors to domain errors."""
        await _dispatch_request_with_domain_errors(
            table_name=table_name,
            request=request,
            dispatch_write=self._dispatch_write,
        )
