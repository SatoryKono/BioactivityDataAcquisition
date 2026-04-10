"""Merged-write operations extracted from ``SilverWriterMergedMixin``."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

import pyarrow as pa
from deltalake import write_deltalake

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)

__all__ = [
    "_MergedSilverWriteRequest",
    "_PreparedMergedSilverWrite",
    "_export_silver_merged_csv",
    "_prepare_merged_silver_write",
    "_write_silver_merged_delta",
]


@dataclass(frozen=True, slots=True)
class _MergedSilverWriteRequest:
    """Normalized request carried through one merged Silver write flow."""

    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str] | None = None
    run_id: str | None = None
    sources_used: list[str] | None = None
    preserve_column_order: bool = False


@dataclass(frozen=True, slots=True)
class _PreparedMergedSilverWrite:
    """Prepared merged Silver payload shared across write stages."""

    request: _MergedSilverWriteRequest
    table_path: str
    arrow_table: pa.Table


class _SilverWriterMergedHostProtocol(Protocol):
    """Structural type for merged-write helper dependencies."""

    logger: LoggerPort
    csv_exporter: CsvExporter | None
    _arrow_converter: ArrowDataConverter

    def _resolve_table_path(self, table_name: str) -> str: ...


def _prepare_merged_silver_write(
    host: _SilverWriterMergedHostProtocol,
    request: _MergedSilverWriteRequest,
) -> _PreparedMergedSilverWrite:
    """Prepare normalized Arrow payload and resolved table path for merged writes."""
    arrow_table = host._arrow_converter.convert_records_to_arrow(
        request.records,
        primary_keys=request.primary_keys,
        apply_column_order=not request.preserve_column_order,
    )
    return _PreparedMergedSilverWrite(
        request=request,
        table_path=host._resolve_table_path(request.table_name),
        arrow_table=drop_nondeterministic_persisted_fields(arrow_table),
    )


async def _write_silver_merged_delta(*, table_path: str, arrow_table: pa.Table) -> None:
    """Write merged Arrow table into Delta Lake."""
    await asyncio.to_thread(
        write_deltalake,
        table_path,
        arrow_table,
        mode="overwrite",
        schema_mode="overwrite",
    )


async def _export_silver_merged_csv(
    host: _SilverWriterMergedHostProtocol,
    *,
    table_name: str,
    arrow_table: pa.Table,
) -> None:
    """Export merged table to CSV when exporter is configured."""
    if host.csv_exporter:
        await host.csv_exporter.export(
            table_name,
            arrow_table,
            append=False,
        )
