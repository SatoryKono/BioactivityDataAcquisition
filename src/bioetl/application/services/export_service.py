"""Export service for Delta Lake tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.export_discovery import (
    _scan_layer_for_tables,
    _scan_provider_for_tables,
)
from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportFormat,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.application.services.export_writers import (
    _write_delimited_file,
    _write_xlsx_file,
)
from bioetl.domain.exceptions import BioETLError, StorageError

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.ports import DeltaReaderPort, LoggerPort

_EXPORT_OPERATION_ERRORS = (
    StorageError,
    BioETLError,
    ImportError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    Exception,
)


@dataclass
class ExportService:
    """Service for exporting Delta Lake tables to various formats."""

    reader: DeltaReaderPort
    logger: LoggerPort
    silver_path: Path
    gold_path: Path
    export_path: Path = field(default_factory=lambda: Path("data/exports"))

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """Discover available Delta tables.

        Args:
            layer: Layer scope to scan — 'silver', 'gold', or 'all' to scan both.

        Returns:
            Sorted list of TableInfo objects for all discovered Delta tables.
        """
        tables: list[TableInfo] = []
        if layer in ("all", "silver"):
            tables.extend(_scan_layer_for_tables(self.silver_path, "silver"))
        if layer in ("all", "gold"):
            tables.extend(_scan_layer_for_tables(self.gold_path, "gold"))
        return sorted(tables, key=lambda t: (t.layer, t.name))

    async def preview(
        self,
        table_name: str,
        layer: str = "silver",
        sample_rows: int = 5,
    ) -> TablePreview:
        """Get preview of a table's schema and sample data.

        Args:
            table_name: Delta table name to preview.
            layer: Medallion layer to search in ('silver' or 'gold').
            sample_rows: Number of sample rows to include in the preview.

        Returns:
            TablePreview with schema columns, row count, and sample row data.
        """
        table_path = self._get_table_path(table_name, layer)

        schema = await self.reader.get_schema(str(table_path))
        columns = tuple(
            ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
            for f in schema
        )

        row_count = await self.reader.get_row_count(str(table_path))
        sample_table = await self.reader.read_table(str(table_path), limit=sample_rows)
        samples = tuple(sample_table.to_pylist())

        return TablePreview(
            table_name=table_name,
            layer=layer,
            row_count=row_count,
            columns=columns,
            sample_rows=samples,
        )

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Export a Delta table to the specified format.

        Args:
            table_name: Delta table name to export.
            layer: Medallion layer to read from ('silver' or 'gold').
            options: Optional export options controlling format, columns, limit,
                and output path. Defaults to ExportOptions() if not provided.

        Returns:
            ExportResult with output path, row count, and any error message.
        """
        options = options or ExportOptions()
        table_path = self._get_table_path(table_name, layer)

        try:
            if not await self.reader.table_exists(str(table_path)):
                return self._create_missing_table_result(
                    table_name=table_name,
                    layer=layer,
                    options=options,
                    table_path=table_path,
                )
            return await self._export_existing_table(
                table_name=table_name,
                layer=layer,
                options=options,
                table_path=table_path,
            )
        except _EXPORT_OPERATION_ERRORS as e:
            self.logger.error(
                "Export failed", table=table_name, layer=layer, error=str(e)
            )
            return self._create_failed_result(
                table_name=table_name,
                layer=layer,
                options=options,
                error=str(e),
            )

    async def _export_existing_table(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        table_path: Path,
    ) -> ExportResult:
        """Export an existing table and build success result."""
        self.logger.info(
            "Reading table for export",
            table=table_name,
            layer=layer,
            format=options.format,
            limit=options.limit,
        )
        table = await self.reader.read_table(
            str(table_path), columns=options.columns, limit=options.limit
        )
        row_count = table.num_rows
        output_dir = options.output_path or self.export_path
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._write_export(
            table, table_name, layer, options.format, output_dir
        )
        self.logger.info(
            "Export completed",
            table=table_name,
            rows=row_count,
            output=str(output_path),
        )
        return self._create_success_result(
            table_name=table_name,
            layer=layer,
            options=options,
            output_path=output_path,
            row_count=row_count,
        )

    def _create_missing_table_result(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        table_path: Path,
    ) -> ExportResult:
        """Build result payload for missing table case."""
        return ExportResult(
            table_name=table_name,
            layer=layer,
            format=options.format,
            output_path=None,
            row_count=0,
            error=f"Table not found: {table_path}",
        )

    def _create_success_result(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        output_path: Path,
        row_count: int,
    ) -> ExportResult:
        """Build result payload for successful export case."""
        return ExportResult(
            table_name=table_name,
            layer=layer,
            format=options.format,
            output_path=output_path,
            row_count=row_count,
        )

    def _create_failed_result(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        error: str,
    ) -> ExportResult:
        """Build result payload for failed export case."""
        return ExportResult(
            table_name=table_name,
            layer=layer,
            format=options.format,
            output_path=None,
            row_count=0,
            error=error,
        )

    def _write_export(
        self,
        table: pa.Table,
        table_name: str,
        layer: str,
        fmt: ExportFormat,
        output_dir: Path,
    ) -> Path:
        """Write table to export file using appropriate format."""
        safe_name = f"{layer}_{table_name.replace('.', '_')}"
        if fmt == "csv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.csv", ",")
        if fmt == "tsv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.tsv", "\t")
        if fmt == "xlsx":
            return _write_xlsx_file(table, output_dir / f"{safe_name}.xlsx")
        raise ValueError(f"Unsupported format: {fmt}")

    def _get_table_path(self, table_name: str, layer: str) -> Path:
        """Get the filesystem path for a table."""
        if layer == "silver":
            base_path = self.silver_path
        elif layer == "gold":
            base_path = self.gold_path
        else:
            raise ValueError(f"Invalid layer: {layer}")

        if not base_path.exists():
            raise FileNotFoundError(f"Layer path not found: {base_path}")

        for provider_dir in base_path.iterdir():
            if not provider_dir.is_dir():
                continue
            for entity_dir in provider_dir.iterdir():
                if not entity_dir.is_dir():
                    continue
                table_dir = entity_dir / table_name
                if table_dir.exists() and (table_dir / "_delta_log").exists():
                    return table_dir.resolve()

        raise FileNotFoundError(
            f"Table '{table_name}' not found in {layer} layer at {base_path}"
        )


__all__ = [
    "ColumnInfo",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "TableInfo",
    "TablePreview",
    "_scan_layer_for_tables",
    "_scan_provider_for_tables",
    "_write_delimited_file",
    "_write_xlsx_file",
]
