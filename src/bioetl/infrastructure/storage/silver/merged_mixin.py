# mypy: disable-error-code=attr-defined
"""Merged-write helpers for ``SilverWriter``."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import pyarrow as pa

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.silver.merged_operations import (
    _build_merged_silver_write_request,
    _execute_merged_silver_write_flow,
    _export_silver_merged_csv,
    _MergedSilverMetadataWriterProtocol,
    _MergedSilverWriteRequest,
    _prepare_merged_silver_write,
    _PreparedMergedSilverWrite,
    _SilverWriterMergedHostProtocol,
    _write_silver_merged_delta,
)

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class SilverWriterMergedMixin:
    """Merged write path extracted from ``SilverWriter`` class body."""

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
        request_kwargs = dict(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
        )
        request_kwargs["completed_at"] = completed_at
        request_kwargs["run_id"] = run_id
        request_kwargs["sources_used"] = sources_used
        request_kwargs["preserve_column_order"] = preserve_column_order
        await _execute_merged_silver_write_flow(
            self,
            _build_merged_silver_write_request(**request_kwargs),
        )
