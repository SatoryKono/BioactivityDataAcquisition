"""Delta operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import pyarrow as pa

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

if TYPE_CHECKING:
    from deltalake import DeltaTable as DeltaTableType

    from bioetl.domain.ports import LoggerPort, MetricsPort


class _SilverDeltaHostProtocol(Protocol):
    """Shared Delta host contract for mixin and operations implementations."""

    @property
    def _logger(self) -> LoggerPort: ...

    @property
    def _metrics(self) -> MetricsPort | None: ...

    @property
    def _merge_resilience_policy(self) -> SilverMergeResiliencePolicy: ...

    def _load_silver_writer_module(self) -> object: ...

    async def _write_append(
        self,
        request: _DeltaWriteRequest,
    ) -> None: ...

    async def _write_delete(
        self,
        request: _DeltaWriteRequest,
    ) -> None: ...

    async def _write_merge(
        self,
        request: _DeltaWriteRequest,
    ) -> None: ...

    async def _merge_records(
        self,
        dt: DeltaTableType,
        records: pa.Table | pa.RecordBatchReader,
        primary_keys: list[str],
        table_path: str,
        *,
        timeout_seconds: float,
        merge_schema: bool = False,
    ) -> None: ...

    def _emit_merge_retry_telemetry(
        self,
        *,
        table_path: str,
        retry_type: str,
        attempt: int,
        max_retries: int,
        delay_seconds: float,
    ) -> None: ...

    def _emit_merge_final_telemetry(
        self, *, table_path: str, final_reason: str
    ) -> None: ...

    async def _dispatch_write(
        self,
        request: _DeltaWriteRequest,
    ) -> None: ...


async def _write_delete_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data in delete mode (overwrite table)."""
    await _write_plain_delta_request(
        load_module=host._load_silver_writer_module,
        request=request,
        mode="overwrite",
        schema_mode="overwrite",
    )


async def _write_append_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data in append mode."""
    await _write_plain_delta_request(
        load_module=host._load_silver_writer_module,
        request=request,
        mode="append",
        schema_mode=request.schema_mode,
    )


async def _write_merge_impl(
    host: _SilverDeltaHostProtocol,
    request: _DeltaWriteRequest,
) -> None:
    """Write data using merge/upsert strategy with conflict retry."""
    await _execute_merge_write_request(
        request=request,
        policy=getattr(
            host,
            "_merge_resilience_policy",
            DEFAULT_SILVER_MERGE_POLICY,
        )
        or DEFAULT_SILVER_MERGE_POLICY,
        load_module=host._load_silver_writer_module,
        write_append=host._write_append,
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


class _SilverDeltaOperationFacade:
    """Shared Delta lifecycle facade for mixin and composition service paths."""

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
        import bioetl.infrastructure.storage.silver_writer as silver_writer_module

        return silver_writer_module

    async def _write_delete(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data in delete mode (overwrite table)."""
        await _write_delete_impl(self, request)

    async def _write_append(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data in append mode."""
        await _write_append_impl(self, request)

    async def _write_merge(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Write data using merge/upsert strategy with conflict retry."""
        await _write_merge_impl(self, request)

    async def _dispatch_write(
        self,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch write call by mode."""
        await _dispatch_write_impl(self, request)

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
        await _merge_records_impl(
            self,
            dt,
            records,
            primary_keys,
            table_path,
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
        _emit_merge_retry_telemetry_impl(
            self,
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
        _emit_merge_final_telemetry_impl(
            self,
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
        await _dispatch_write_with_domain_errors_impl(
            self,
            table_name=table_name,
            request=request,
        )


@dataclass(slots=True)
class SilverDeltaOperations(_SilverDeltaOperationFacade):
    """Delta operations service for Silver layer writes.

    This service encapsulates all Delta Lake write/merge operations previously in SilverWriterDeltaMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    logger: LoggerPort
    _metrics: MetricsPort | None
    _merge_resilience_policy: SilverMergeResiliencePolicy
