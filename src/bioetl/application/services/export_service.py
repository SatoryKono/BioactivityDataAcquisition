"""Export service for Delta Lake tables.

Provides high-level export operations for Silver/Gold Delta tables
to CSV, XLSX, and TSV formats.
"""

from __future__ import annotations

__all__ = [
    "ColumnInfo",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "TableInfo",
    "TablePreview",
]


from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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


ExportFormat = Literal["csv", "xlsx", "tsv"]


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    """Information about a table column.

    Attributes:
        name: Column name.
        type: Column data type as string.
        nullable: Whether the column allows nulls.
    """

    name: str
    type: str
    nullable: bool


@dataclass(frozen=True, slots=True)
class TablePreview:
    """Preview of a Delta table for display.

    Attributes:
        table_name: Full table name (e.g., chembl.activity).
        layer: Medallion layer (silver/gold).
        row_count: Total number of rows.
        columns: List of column information.
        sample_rows: First few rows as dictionaries.
    """

    table_name: str
    layer: str
    row_count: int
    columns: tuple[ColumnInfo, ...]
    sample_rows: tuple[
        dict[str, Any], ...  # Any: port contract allows heterogeneous record values
    ]  # Any: port contract allows heterogeneous record values


@dataclass(frozen=True, slots=True)
class TableInfo:
    """Information about a discovered table.

    Attributes:
        name: Table name in format "provider.entity".
        layer: Medallion layer (silver/gold).
        path: Full path to the table directory.
    """

    name: str
    layer: str
    path: Path


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Options for export operation.

    Attributes:
        format: Output format (csv, xlsx, tsv).
        output_path: Directory to write output file.
        limit: Maximum rows to export (None for all).
        columns: Columns to include (None for all).
    """

    format: ExportFormat = "csv"
    output_path: Path | None = None
    limit: int | None = None
    columns: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Result of an export operation.

    Attributes:
        table_name: Name of exported table.
        layer: Medallion layer.
        format: Output format used.
        output_path: Path to the exported file.
        row_count: Number of rows exported.
        error: Error message if export failed.
    """

    table_name: str
    layer: str
    format: ExportFormat
    output_path: Path | None
    row_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if export succeeded."""
        return self.error is None


def _scan_layer_for_tables(base_path: Path, layer_name: str) -> list[TableInfo]:
    """Scan a layer directory for Delta tables.

    Args:
        base_path: Root path of the layer.
        layer_name: Name of the layer (silver/gold).

    Returns:
        List of TableInfo for discovered tables.
    """
    tables: list[TableInfo] = []
    if not base_path.exists():
        return tables

    for provider_dir in base_path.iterdir():
        if not provider_dir.is_dir():
            continue
        tables.extend(_scan_provider_for_tables(provider_dir, layer_name))

    return tables


def _scan_provider_for_tables(provider_dir: Path, layer_name: str) -> list[TableInfo]:
    """Scan a provider directory for Delta tables.

    Args:
        provider_dir: Provider directory path.
        layer_name: Name of the layer.

    Returns:
        List of TableInfo for discovered tables.
    """
    tables: list[TableInfo] = []
    for entity_dir in provider_dir.iterdir():
        if not entity_dir.is_dir():
            continue
        for table_dir in entity_dir.iterdir():
            if table_dir.is_dir() and (table_dir / "_delta_log").exists():
                tables.append(
                    TableInfo(name=table_dir.name, layer=layer_name, path=table_dir)
                )
    return tables


def _write_delimited_file(
    table: pa.Table, output_path: Path, delimiter: str = ","
) -> Path:
    """Write Arrow table to delimited file (CSV or TSV).

    Args:
        table: PyArrow table to write.
        output_path: Path to output file.
        delimiter: Field delimiter character.

    Returns:
        Path to written file.
    """
    import pyarrow.csv as pv

    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    write_options = pv.WriteOptions(delimiter=delimiter)
    pv.write_csv(flattened, output_path, write_options=write_options)
    return output_path


def _write_xlsx_file(table: pa.Table, output_path: Path) -> Path:
    """Write Arrow table to XLSX file.

    Args:
        table: PyArrow table to write.
        output_path: Path to output file.

    Returns:
        Path to written file.

    Raises:
        ImportError: If openpyxl is not installed.
    """
    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    df = flattened.to_pandas()

    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
    except ImportError as e:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from e

    return output_path


@dataclass
class ExportService:
    """Service for exporting Delta Lake tables to various formats.

    Responsibilities:
    - Discover tables in Silver/Gold layers
    - Preview table schema and sample data
    - Export tables to CSV, XLSX, TSV formats

    Attributes:
        reader: Delta reader for accessing tables.
        logger: Structured logger for observability.
        silver_path: Base path for Silver layer.
        gold_path: Base path for Gold layer.
        export_path: Default export output directory.
    """

    reader: DeltaReaderPort
    logger: LoggerPort
    silver_path: Path
    gold_path: Path
    export_path: Path = field(default_factory=lambda: Path("data/exports"))

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """Discover available Delta tables.

        Args:
            layer: Which layer to scan - "all", "silver", or "gold".

        Returns:
            List of discovered tables, sorted alphabetically.
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
            table_name: Table name in format "provider.entity".
            layer: Medallion layer to read from.
            sample_rows: Number of sample rows to include.

        Returns:
            TablePreview with schema and sample data.

        Raises:
            FileNotFoundError: If table does not exist.
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
        """Export a Delta table to the specified format."""
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
        elif fmt == "tsv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.tsv", "\t")
        elif fmt == "xlsx":
            return _write_xlsx_file(table, output_dir / f"{safe_name}.xlsx")
        else:
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
