"""Runtime contracts and dependencies for Silver Delta operation services."""

from __future__ import annotations

from typing import Protocol

import pyarrow as pa
from deltalake import DeltaTable as DeltaTableType

from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.infrastructure.storage.delta.resilience import (
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest

__all__ = ["_SilverDeltaHostProtocol", "_load_deltalake_module"]


def _load_deltalake_module() -> object:
    """Return the root writer module that owns the Delta Lake compatibility seam."""
    from bioetl.infrastructure.storage import silver_writer

    return silver_writer


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
