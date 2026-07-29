# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Delta operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

import pyarrow as pa
from deltalake import DeltaTable as DeltaTableType

from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.infrastructure.storage.delta.resilience import (
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.operations.delta_operation_impls import (
    _dispatch_write_impl,
    _dispatch_write_with_domain_errors_impl,
    _emit_merge_final_telemetry_impl,
    _emit_merge_retry_telemetry_impl,
    _merge_records_impl,
    _write_append_impl,
    _write_delete_impl,
    _write_merge_impl,
)
from bioetl.infrastructure.storage.silver.operations.delta_operation_protocols import (
    _load_deltalake_module,
)

__all__ = [
    "SilverDeltaOperations",
    "_SilverDeltaOperationFacade",
    "_load_deltalake_module",
]


class _SilverDeltaOperationFacade:
    """Shared Delta lifecycle facade for mixin and composition service paths."""

    logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _merge_resilience_policy: SilverMergeResiliencePolicy = cast(Any, None)  # Any: host attr default (PD3)

    @property
    def _logger(self) -> LoggerPort:
        """Access logger via private convention for delegation pattern compliance."""
        return self.logger

    def _load_silver_writer_module(self) -> object:
        """Load the Delta module through an injected compatibility seam."""
        load_delta_module = getattr(self, "_load_delta_module", None)
        if callable(load_delta_module):
            return load_delta_module()
        return _load_deltalake_module()

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
    """Delta operations service for Silver layer writes."""

    logger: LoggerPort
    _metrics: MetricsPort | None = None
    # Align with facade host contract (non-optional policy surface; host sets real policy).
    _merge_resilience_policy: SilverMergeResiliencePolicy = field(
        default=cast(Any, None),  # Any: host attr default (PD5 product zero hold)
    )
    _load_delta_module: Callable[[], object] | None = _load_deltalake_module
