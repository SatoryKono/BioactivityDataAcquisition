"""Merged-write operations extracted from ``SilverWriterMergedMixin``."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandera as pandera
import pyarrow as pa
from deltalake import write_deltalake

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.silver.merged_request_support import (
    _build_merged_write_request_from_mapping,
)
from bioetl.infrastructure.validation.pandera_validator import PanderaSilverValidator

__all__ = [
    "_MergedSilverMetadataWriterProtocol",
    "_MergedSilverWriteExecutorProtocol",
    "_MergedSilverWriteRequest",
    "_PreparedMergedSilverWrite",
    "_build_merged_silver_write_request",
    "_execute_merged_silver_write_flow",
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
    completed_at: datetime | None = None
    run_id: str | None = None
    sources_used: list[str] | None = None
    preserve_column_order: bool = False
    schema: object | None = None


def _build_merged_silver_write_request(
    *,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str] | None = None,
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
    preserve_column_order: bool = False,
    schema: object | None = None,
) -> _MergedSilverWriteRequest:
    """Build the canonical merged-write request from keyword arguments."""
    return _build_merged_write_request_from_mapping(
        _MergedSilverWriteRequest,
        locals(),
        preserve_column_order=preserve_column_order,
        schema=schema,
    )


@dataclass(frozen=True, slots=True)
class _PreparedMergedSilverWrite:
    """Prepared merged Silver payload shared across write stages."""

    request: _MergedSilverWriteRequest
    table_path: str
    arrow_table: pa.Table


class _MergedSilverMetadataWriterProtocol(Protocol):
    """Keyword-oriented contract for merged-write metadata finalization."""

    def __call__(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: datetime | None,
        run_id: str | None,
        sources_used: list[str] | None,
    ) -> Awaitable[None]: ...


class _SilverWriterMergedHostProtocol(Protocol):
    """Structural type for merged-write helper dependencies."""

    logger: LoggerPort
    csv_exporter: CsvExporterProtocol | None
    _arrow_converter: ArrowDataConverter

    def _resolve_table_path(self, table_name: str) -> str: ...


class _MergedSilverWriteExecutorProtocol(Protocol):
    """Lifecycle strategy for merged Silver write orchestration."""

    logger: LoggerPort
    _write_silver_merged_metadata: _MergedSilverMetadataWriterProtocol

    def _prepare_merged_silver_write(
        self,
        request: _MergedSilverWriteRequest,
    ) -> _PreparedMergedSilverWrite: ...

    async def _write_silver_merged_delta(
        self,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None: ...

    async def _export_silver_merged_csv(
        self,
        *,
        table_name: str,
        arrow_table: pa.Table,
    ) -> None: ...


def _prepare_merged_silver_write(
    host: _SilverWriterMergedHostProtocol,
    request: _MergedSilverWriteRequest,
) -> _PreparedMergedSilverWrite:
    """Prepare normalized Arrow payload and resolved table path for merged writes."""
    if request.schema is not None:
        schema = request.schema
        if hasattr(schema, "to_schema"):
            schema = schema.to_schema()
        if not isinstance(schema, pandera.DataFrameSchema):
            raise TypeError("Merged Silver schema must resolve to DataFrameSchema")
        result = PanderaSilverValidator(schema=schema, strict=False).validate(
            request.records
        )
        if not result.valid:
            raise SchemaViolationError(request.table_name, result.errors)

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


async def _execute_merged_silver_write_flow(
    executor: _MergedSilverWriteExecutorProtocol,
    request: _MergedSilverWriteRequest,
) -> None:
    """Run the common merged Silver lifecycle through executor strategies."""
    if not request.records:
        executor.logger.warning(
            "No records to write for merged Silver",
            table_name=request.table_name,
        )
        return

    prepared = executor._prepare_merged_silver_write(request)
    executor.logger.info(
        "Writing merged Silver records",
        table_name=prepared.request.table_name,
        path=prepared.table_path,
        records=len(request.records),
    )
    await executor._write_silver_merged_delta(
        table_path=prepared.table_path,
        arrow_table=prepared.arrow_table,
    )
    await executor._export_silver_merged_csv(
        table_name=prepared.request.table_name,
        arrow_table=prepared.arrow_table,
    )
    await executor._write_silver_merged_metadata(
        table_path=prepared.table_path,
        table_name=prepared.request.table_name,
        records=prepared.request.records,
        primary_keys=prepared.request.primary_keys or [],
        completed_at=prepared.request.completed_at,
        run_id=prepared.request.run_id,
        sources_used=prepared.request.sources_used,
    )
