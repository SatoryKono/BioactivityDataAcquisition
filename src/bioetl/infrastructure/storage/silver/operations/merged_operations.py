"""Merged operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pyarrow as pa

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.silver.merged_operations import (
    _export_silver_merged_csv,
    _MergedSilverWriteRequest,
    _prepare_merged_silver_write,
    _PreparedMergedSilverWrite,
    _write_silver_merged_delta,
)


class _MergedSilverMetadataWriterProtocol(Protocol):
    """Keyword-friendly contract for merged-write metadata finalization."""

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


@dataclass(slots=True)
class SilverMergedOperations:
    """Merged operations service for Silver layer writes.

    This service encapsulates merged write logic previously in SilverWriterMergedMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    logger: LoggerPort
    csv_exporter: CsvExporter | None
    _arrow_converter: ArrowDataConverter
    _resolve_table_path: Callable[[str], str]
    _write_silver_merged_metadata: _MergedSilverMetadataWriterProtocol

    def _prepare_merged_silver_write(
        self,
        request: _MergedSilverWriteRequest,
    ) -> _PreparedMergedSilverWrite:
        """Prepare normalized Arrow payload and resolved table path for merged writes.

        Args:
            request: Normalized merged write request.

        Returns:
            Prepared write payload with resolved table path and normalized Arrow table.
        """
        return _prepare_merged_silver_write(self, request)

    async def _write_silver_merged_delta(
        self,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None:
        """Write merged Arrow table into Delta Lake.

        Args:
            table_path: File system path to the Delta table target.
            arrow_table: PyArrow Table to write in overwrite mode.
        """
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
        """Export merged table to CSV when exporter is configured.

        Args:
            table_name: Logical table name used as the CSV export target.
            arrow_table: PyArrow Table containing the merged records to export.
        """
        await _export_silver_merged_csv(
            self, table_name=table_name, arrow_table=arrow_table
        )

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
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
                completed_at=completed_at,
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
            completed_at=prepared.request.completed_at,
            run_id=prepared.request.run_id,
            sources_used=prepared.request.sources_used,
        )
