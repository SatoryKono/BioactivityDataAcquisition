# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Merged operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

import pyarrow as pa

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.silver.merged_operations import (
    _build_merged_silver_write_request,
    _execute_merged_silver_write_flow,
    _export_silver_merged_csv,
    _MergedSilverMetadataWriterProtocol,
    _MergedSilverWriteExecutorProtocol,
    _MergedSilverWriteRequest,
    _prepare_merged_silver_write,
    _PreparedMergedSilverWrite,
    _SilverWriterMergedHostProtocol,
    _write_silver_merged_delta,
)

__all__ = [
    "SilverMergedOperations",
]


class _MergedWriteFacade:
    """Shared merged-write facade used by mixin and composition service paths."""

    logger: LoggerPort
    csv_exporter: CsvExporterProtocol | None
    _arrow_converter: ArrowDataConverter
    _resolve_table_path: Callable[[str], str]
    _write_silver_merged_metadata: _MergedSilverMetadataWriterProtocol

    def _prepare_merged_silver_write(
        self,
        request: _MergedSilverWriteRequest,
    ) -> _PreparedMergedSilverWrite:
        """Prepare normalized Arrow payload and resolved table path for merged writes."""
        return _prepare_merged_silver_write(
            cast(_SilverWriterMergedHostProtocol, self),
            request,
        )

    async def _write_silver_merged_delta(
        self,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None:
        """Write merged Arrow table into Delta Lake."""
        await _write_silver_merged_delta(
            table_path=table_path,
            arrow_table=arrow_table,
        )

    async def _export_silver_merged_csv(
        self,
        *,
        table_name: str,
        arrow_table: pa.Table,
    ) -> None:
        """Export merged table to CSV when exporter is configured."""
        await _export_silver_merged_csv(
            cast(_SilverWriterMergedHostProtocol, self),
            table_name=table_name,
            arrow_table=arrow_table,
        )

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        schema: object | None = None,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer with optional core-schema validation."""
        await _execute_merged_silver_write_flow(
            cast(_MergedSilverWriteExecutorProtocol, self),
            _build_merged_silver_write_request(
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                schema=schema,
                completed_at=completed_at,
                run_id=run_id,
                sources_used=sources_used,
                preserve_column_order=preserve_column_order,
            ),
        )


@dataclass(slots=True)
class SilverMergedOperations(_MergedWriteFacade):
    """Merged operations service for Silver layer writes.

    This service encapsulates merged write logic previously in SilverWriterMergedMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    logger: LoggerPort
    csv_exporter: CsvExporterProtocol | None
    _arrow_converter: ArrowDataConverter
    _resolve_table_path: Callable[[str], str]
    _write_silver_merged_metadata: _MergedSilverMetadataWriterProtocol
