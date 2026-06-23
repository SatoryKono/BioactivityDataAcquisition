"""Protocol contracts for Gold write operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

__all__ = [
    "_GoldMergedMetadataWriterProtocol",
    "_GoldMergedWriteHostProtocol",
    "_GoldWriteDispatchTargetProtocol",
]


class _GoldMergedMetadataWriterProtocol(Protocol):
    """Typed contract for merged-metadata writer implementation."""

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, object]],
        completed_at: object | None = None,
        run_id: str | None = None,
        schema: object | None = None,
    ) -> None: ...


class _GoldWriteDispatchTargetProtocol(Protocol):
    """Protocol for dispatch targets implemented by concrete write mixins."""

    async def _write_scd2(
        self,
        table_path: str,
        records: list[dict[str, object]],
        scd_config: object,
        partition_cols: list[str] | None,
        ingestion_ts: object,
        column_order: list[str] | None = None,
    ) -> None: ...

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, object]],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: object | None = None,
        column_order: list[str] | None = None,
    ) -> None: ...


class _GoldMergedWriteHostProtocol(Protocol):
    """Structural host contract for merged Gold write helpers."""

    logger: object
    csv_exporter: object | None
    _resolve_table_path: Callable[[str], str]
    _validate_records_against_schema: Callable[
        [list[dict[str, object]], object], Awaitable[None]
    ]
    _validate_schema_strict: Callable[[object], None]

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...
