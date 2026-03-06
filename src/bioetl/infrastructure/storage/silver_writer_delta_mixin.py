"""Delta operation helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterDeltaMixin"]

import asyncio
from typing import TYPE_CHECKING, Any

import pyarrow as pa
from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import DeltaTransactionError
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort, MetricsPort


class _MergeExecutionTimeoutError(RuntimeError):
    """Internal timeout marker used for merge retry orchestration."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Merge execution timed out after {timeout_seconds}s")


class SilverWriterDeltaMixin:
    """Mixin with Delta write/merge operations."""

    logger: LoggerPort
    _metrics: MetricsPort | None
    _merge_resilience_policy: SilverMergeResiliencePolicy

    @staticmethod
    def _load_silver_writer_module() -> Any:  # Any: return type varies at runtime
        """Load silver_writer module for backward-compatible patch points."""
        from bioetl.infrastructure.storage import silver_writer as silver_writer_module

        return silver_writer_module

    async def _write_delete(
        self,
        table_path: str,
        data: pa.Table,
        partition_cols: list[str] | None,
    ) -> None:
        """Write data in delete mode (overwrite table)."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._load_silver_writer_module().write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="overwrite",
                partition_by=partition_cols,
                schema_mode="overwrite",
            ),
        )

    async def _write_append(
        self,
        table_path: str,
        data: pa.Table,
        partition_cols: list[str] | None,
    ) -> None:
        """Write data in append mode."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._load_silver_writer_module().write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="append",
                partition_by=partition_cols,
            ),
        )

    async def _write_merge(
        self,
        table_path: str,
        data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        """Write data using merge/upsert strategy with conflict retry."""
        policy = getattr(
            self,
            "_merge_resilience_policy",
            DEFAULT_SILVER_MERGE_POLICY,
        )
        loop = asyncio.get_running_loop()
        commit_retry_count = 0
        timeout_retry_count = 0

        while True:
            try:
                table = await loop.run_in_executor(
                    None,
                    lambda: self._load_silver_writer_module().DeltaTable(table_path),
                )
                await self._merge_records(
                    table,
                    data,
                    primary_keys,
                    table_path,
                    timeout_seconds=policy.execution_timeout_seconds,
                )
                if commit_retry_count > 0 or timeout_retry_count > 0:
                    self.logger.info(
                        "silver_merge_recovered_after_retry",
                        table_path=table_path,
                        commit_retry_count=commit_retry_count,
                        timeout_retry_count=timeout_retry_count,
                        final_reason="success_after_retry",
                    )
                return
            except DeltaTableNotFoundError:
                await self._write_append(table_path, data, partition_cols)
                return
            except CommitFailedError:
                if not policy.commit_retry.should_retry(commit_retry_count):
                    self._emit_merge_final_telemetry(
                        table_path=table_path,
                        final_reason="commit_conflict_retries_exhausted",
                    )
                    raise
                delay = policy.commit_retry.calculate_delay(commit_retry_count)
                commit_retry_count += 1
                self._emit_merge_retry_telemetry(
                    table_path=table_path,
                    retry_type="commit_conflict",
                    attempt=commit_retry_count,
                    max_retries=policy.commit_retry.max_retries,
                    delay_seconds=delay,
                )
                if delay > 0.0:
                    await asyncio.sleep(delay)
            except _MergeExecutionTimeoutError as exc:
                if not policy.timeout_retry.should_retry(timeout_retry_count):
                    self._emit_merge_final_telemetry(
                        table_path=table_path,
                        final_reason="timeout_retries_exhausted",
                    )
                    raise DeltaTransactionError(
                        table_path=table_path,
                        reason=(
                            "Delta merge_execute timed out after "
                            f"{exc.timeout_seconds} seconds "
                            f"(timeout_retries={timeout_retry_count})"
                        ),
                    ) from exc
                delay = policy.timeout_retry.calculate_delay(timeout_retry_count)
                timeout_retry_count += 1
                self._emit_merge_retry_telemetry(
                    table_path=table_path,
                    retry_type="timeout",
                    attempt=timeout_retry_count,
                    max_retries=policy.timeout_retry.max_retries,
                    delay_seconds=delay,
                )
                if delay > 0.0:
                    await asyncio.sleep(delay)

    async def _dispatch_write(
        self,
        validated_mode: SilverWriteMode,
        table_path: str,
        arrow_data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        """Dispatch write call by mode."""
        if validated_mode == SilverWriteMode.DELETE:
            await self._write_delete(table_path, arrow_data, partition_cols)
        elif validated_mode == SilverWriteMode.APPEND:
            await self._write_append(table_path, arrow_data, partition_cols)
        else:
            await self._write_merge(
                table_path, arrow_data, primary_keys, partition_cols
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
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )
        loop = asyncio.get_running_loop()
        merge_future = loop.run_in_executor(
            None,
            lambda: (
                dt.merge(
                    source=records,
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update_all(
                    predicate=(
                        "CASE "
                        "WHEN source._run_type = 'rebuild' THEN 3 "
                        "WHEN source._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END >= "
                        "CASE "
                        "WHEN target._run_type = 'rebuild' THEN 3 "
                        "WHEN target._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END"
                    )
                )
                .when_not_matched_insert_all()
                .execute()
            ),
        )
        try:
            await asyncio.wait_for(
                merge_future,
                timeout=timeout_seconds,
            )
        except TimeoutError as exc:
            self.logger.warning(
                "silver_merge_timeout",
                table_path=table_path,
                timeout_seconds=timeout_seconds,
                primary_keys=primary_keys,
            )
            raise _MergeExecutionTimeoutError(timeout_seconds) from exc

    def _emit_merge_retry_telemetry(
        self,
        *,
        table_path: str,
        retry_type: str,
        attempt: int,
        max_retries: int,
        delay_seconds: float,
    ) -> None:
        self.logger.warning(
            "silver_merge_retry",
            table_path=table_path,
            retry_type=retry_type,
            attempt=attempt,
            max_retries=max_retries,
            delay_seconds=delay_seconds,
        )
        if self._metrics is not None:
            self._metrics.increment_counter(
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

    def _emit_merge_final_telemetry(
        self, *, table_path: str, final_reason: str
    ) -> None:
        self.logger.error(
            "silver_merge_failed",
            table_path=table_path,
            final_reason=final_reason,
        )
        if self._metrics is not None:
            self._metrics.increment_counter(
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
