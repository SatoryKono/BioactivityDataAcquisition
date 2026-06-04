"""Protocol contracts for Gold write operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol

from pandera.polars import DataFrameSchema

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import GoldRecord, ScdConfig
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol

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
        records: list[GoldRecord],
        completed_at: datetime | None = None,
        run_id: str | None = None,
        schema: DataFrameSchema | None = None,
    ) -> None: ...


class _GoldWriteDispatchTargetProtocol(Protocol):
    """Protocol for dispatch targets implemented by concrete write mixins."""

    async def _write_scd2(
        self,
        table_path: str,
        records: list[GoldRecord],
        scd_config: ScdConfig,
        partition_cols: list[str] | None,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: DataFrameSchema | None = None,
        column_order: list[str] | None = None,
    ) -> None: ...


class _GoldMergedWriteHostProtocol(Protocol):
    """Structural host contract for merged Gold write helpers."""

    logger: LoggerPort
    csv_exporter: CsvExporterProtocol | None
    _resolve_table_path: Callable[[str], str]
    _validate_records_against_schema: Callable[
        [list[GoldRecord], DataFrameSchema], Awaitable[None]
    ]
    _validate_schema_strict: Callable[[DataFrameSchema], None]

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...
