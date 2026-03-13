# mypy: disable-error-code=attr-defined
"""Merged-write helpers for ``SilverWriter``."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import pyarrow as pa
from deltalake import write_deltalake

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class _MergedArrowConverterProtocol(Protocol):
    """Minimal converter contract needed by merged Silver writes."""

    def convert_records_to_arrow(
        self,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        column_order: list[str] | None = None,
        apply_column_order: bool = True,
    ) -> pa.Table: ...


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


class _SilverWriterMergedContext(Protocol):
    """Structural type for mixin self dependencies."""

    _arrow_converter: _MergedArrowConverterProtocol
    logger: LoggerPort
    csv_exporter: CsvExporter | None

    def _resolve_table_path(self, table_name: str) -> str: ...

    async def _write_silver_merged_metadata(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        run_id: str | None,
        sources_used: list[str] | None,
    ) -> None: ...


class SilverWriterMergedMixin:
    """Merged write path extracted from ``SilverWriter`` class body."""

    def _prepare_merged_silver_write(
        self: _SilverWriterMergedContext,
        request: _MergedSilverWriteRequest,
    ) -> _PreparedMergedSilverWrite:
        """Prepare normalized Arrow payload and resolved table path for merged writes.

        Args:
            request: Normalized merged write request.

        Returns:
            Prepared write payload with resolved table path and normalized Arrow table.
        """
        return _PreparedMergedSilverWrite(
            request=request,
            table_path=self._resolve_table_path(request.table_name),
            arrow_table=self._arrow_converter.convert_records_to_arrow(
                request.records,
                primary_keys=request.primary_keys,
                apply_column_order=not request.preserve_column_order,
            ),
        )

    async def _write_silver_merged_delta(
        self: _SilverWriterMergedContext,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None:
        """Write merged Arrow table into Delta Lake.

        Args:
            table_path: File system path to the Delta table target.
            arrow_table: PyArrow Table to write in overwrite mode.
        """
        await asyncio.to_thread(
            write_deltalake,
            table_path,
            arrow_table,
            mode="overwrite",
            schema_mode="overwrite",
        )

    async def _export_silver_merged_csv(
        self: _SilverWriterMergedContext,
        *,
        table_name: str,
        arrow_table: pa.Table,
    ) -> None:
        """Export merged table to CSV when exporter is configured.

        Args:
            table_name: Logical table name used as the CSV export target.
            arrow_table: PyArrow Table containing the merged records to export.
        """
        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_table,
                append=False,
            )

    async def write_silver_merged(
        self: _SilverWriterMergedContext,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Args:
            table_name: Logical table name for the Silver target.
            records: List of Bronze record dicts to write.
            primary_keys: Optional list of column names used for sorting.
            run_id: Optional run identifier written to metadata sidecar.
            sources_used: Optional list of source identifiers contributing to the merge.
            preserve_column_order: If True, skip canonical column reordering.
        """
        if not records:
            self.logger.warning(
                "No records to write for merged Silver",
                table_name=table_name,
            )
            return

        prepared = self._prepare_merged_silver_write(
            _MergedSilverWriteRequest(
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                run_id=run_id,
                sources_used=sources_used,
                preserve_column_order=preserve_column_order,
            )
        )
        self.logger.info(
            "Writing merged Silver records",
            table_name=prepared.request.table_name,
            path=prepared.table_path,
            records=len(records),
        )
        await self._write_silver_merged_delta(
            table_path=prepared.table_path,
            arrow_table=prepared.arrow_table,
        )
        await self._export_silver_merged_csv(
            table_name=prepared.request.table_name,
            arrow_table=prepared.arrow_table,
        )
        await self._write_silver_merged_metadata(
            table_path=prepared.table_path,
            table_name=prepared.request.table_name,
            records=prepared.request.records,
            primary_keys=prepared.request.primary_keys or [],
            run_id=prepared.request.run_id,
            sources_used=prepared.request.sources_used,
        )
