# mypy: disable-error-code=attr-defined
"""Merged-write helpers for ``SilverWriter``."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

import pyarrow as pa
from deltalake import write_deltalake

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.base_delta_writer import coerce_null_types_for_delta

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class _SilverWriterMergedContext(Protocol):
    """Structural type for mixin self dependencies."""

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

    def _prepare_merged_arrow_table(
        self: _SilverWriterMergedContext,
        records: list[BronzeRecord],
        *,
        primary_keys: list[str] | None,
        preserve_column_order: bool,
    ) -> pa.Table:
        """Prepare normalized Arrow table for merged silver writes.

        Returns:
            PyArrow Table with coerced null types, canonical column order, and primary key sorting applied.
        """
        from bioetl.domain.schemas.column_order import canonical_column_order

        arrow_table = pa.Table.from_pylist(records)
        arrow_table = coerce_null_types_for_delta(arrow_table)

        if not preserve_column_order:
            ordered_columns = canonical_column_order(list(arrow_table.column_names))
            arrow_table = arrow_table.select(ordered_columns)

        if primary_keys:
            valid_keys = [
                key for key in primary_keys if key in arrow_table.schema.names
            ]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(key, "ascending") for key in valid_keys]
                )
        return arrow_table

    async def _write_silver_merged_delta(
        self: _SilverWriterMergedContext,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None:
        """Write merged Arrow table into Delta Lake."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_path,
                arrow_table,
                mode="overwrite",
                schema_mode="overwrite",
            ),
        )

    async def _export_silver_merged_csv(
        self: _SilverWriterMergedContext,
        *,
        table_name: str,
        arrow_table: pa.Table,
    ) -> None:
        """Export merged table to CSV when exporter is configured."""
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
        """Write merged records to Silver layer without explicit schema."""
        if not records:
            self.logger.warning(
                "No records to write for merged Silver",
                table_name=table_name,
            )
            return

        arrow_table = self._prepare_merged_arrow_table(
            records,
            primary_keys=primary_keys,
            preserve_column_order=preserve_column_order,
        )
        table_path = self._resolve_table_path(table_name)
        self.logger.info(
            "Writing merged Silver records",
            table_name=table_name,
            path=table_path,
            records=len(records),
        )
        await self._write_silver_merged_delta(
            table_path=table_path,
            arrow_table=arrow_table,
        )
        await self._export_silver_merged_csv(
            table_name=table_name,
            arrow_table=arrow_table,
        )
        await self._write_silver_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys or [],
            run_id=run_id,
            sources_used=sources_used,
        )
