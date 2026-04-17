"""Delta operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pyarrow as pa

from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _DeltaWriteRequest,
    _build_dispatch_policy,
    _dispatch_request_by_mode,
    _dispatch_request_with_domain_errors,
    _merge_records_with_timeout,
    _write_plain_delta_request,
)
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _execute_merge_write_request,
)
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _emit_merge_final_event,
    _emit_merge_retry_event,
)

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort, MetricsPort


@dataclass(frozen=True, slots=True)
class SilverDeltaOperations:
    """Delta operations service for Silver layer writes.

    This service encapsulates all Delta Lake write/merge operations previously in SilverWriterDeltaMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    logger: LoggerPort
    _metrics: MetricsPort | None
    _merge_resilience_policy: SilverMergeResiliencePolicy

    def _load_silver_writer_module(self) -> Any:  # Any: return type varies at runtime
        """Load silver_writer module for backward-compatible patch points."""
        from bioetl.infrastructure.storage import silver_writer as silver_writer_module

        return silver_writer_module

    @property
    def _logger(self) -> LoggerPort:
        """Access logger via private convention for delegation pattern compliance."""
        return self.logger

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
            schema_mode=request.schema_mode,
        )

    async def _write_merge(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data using merge/upsert strategy with conflict retry."""
        await _execute_merge_write_request(
            request=request,
            policy=self._merge_resilience_policy or DEFAULT_SILVER_MERGE_POLICY,
            load_module=self._load_silver_writer_module,
            write_append=self._write_append,
            merge_records=self._merge_records,
            emit_final=self._emit_merge_final_telemetry,
            emit_retry=self._emit_merge_retry_telemetry,
            logger=self._logger,
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
        merge_schema: bool = False,
    ) -> None:
        """Merge records into an existing Delta table."""
        await _merge_records_with_timeout(
            logger=self._logger,
            dt=dt,
            records=records,
            primary_keys=primary_keys,
            table_path=table_path,
            timeout_seconds=timeout_seconds,
            merge_schema=merge_schema,
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
