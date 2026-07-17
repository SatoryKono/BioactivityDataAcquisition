"""Export service for Delta Lake tables."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeGuard, runtime_checkable

from bioetl.application.services.export_execution import (
    create_failed_result as _create_failed_result,
)
from bioetl.application.services.export_execution import (
    create_missing_table_result as _create_missing_table_result,
)
from bioetl.application.services.export_execution import (
    create_success_result as _create_success_result,
)
from bioetl.application.services.export_execution import (
    export_existing_table as _export_existing_table,
)
from bioetl.application.services.export_execution import (
    get_layer_base_path as _get_layer_base_path,
)
from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportFormat,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.domain.exceptions import BioETLError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        DeltaReaderPort,
        ExportCatalogPort,
        ExportWriterPort,
        LoggerPort,
    )

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


class _PreviewField(Protocol):
    """Column metadata surface required for table previews."""

    @property
    def name(self) -> str: ...

    @property
    def type(self) -> object: ...

    @property
    def nullable(self) -> bool: ...


@runtime_checkable
class _PreviewSchema(Protocol):
    """Iterable schema returned by preview-capable Delta readers."""

    def __iter__(self) -> Iterator[_PreviewField]: ...


class _PreviewTable(Protocol):
    """Sample table surface required for preview serialization."""

    def to_pylist(self) -> list[dict[str, object]]: ...


def _is_preview_table(value: object) -> TypeGuard[_PreviewTable]:
    """Return whether a Delta reader payload supports preview serialization."""
    return callable(getattr(value, "to_pylist", None))


@dataclass
class ExportService:
    """Service for exporting Delta Lake tables to various formats."""

    reader: DeltaReaderPort
    catalog: ExportCatalogPort
    writer: ExportWriterPort
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
            tables.extend(
                TableInfo(name=name, layer="silver", path=Path(path))
                for name, path in self.catalog.list_tables(
                    base_path=str(self.silver_path),
                    layer="silver",
                )
            )
        if layer in ("all", "gold"):
            tables.extend(
                TableInfo(name=name, layer="gold", path=Path(path))
                for name, path in self.catalog.list_tables(
                    base_path=str(self.gold_path),
                    layer="gold",
                )
            )
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

        table_path_ref = table_path if isinstance(table_path, str) else table_path.as_posix()
        schema = await self.reader.get_schema(table_path_ref)
        if not isinstance(schema, _PreviewSchema):
            raise TypeError("Delta reader returned a non-iterable preview schema")
        columns = tuple(
            ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
            for f in schema
        )

        row_count = await self.reader.get_row_count(table_path_ref)
        sample_table = await self.reader.read_table(table_path_ref, limit=sample_rows)
        if not _is_preview_table(sample_table):
            raise TypeError("Delta reader returned a table without preview support")
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
            table_path_str = table_path if isinstance(table_path, str) else table_path.as_posix()
            if not await self.reader.table_exists(table_path_str):
                return self._create_missing_table_result(
                    table_name=table_name,
                    layer=layer,
                    options=options,
                    table_path=table_path,
                )
            return await _export_existing_table(
                reader=self.reader,
                writer=self.writer,
                logger=self.logger,
                export_path=self.export_path,
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

    def _create_missing_table_result(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        table_path: Path | str,
    ) -> ExportResult:
        """Build result payload for missing table case."""
        return _create_missing_table_result(
            table_name=table_name,
            layer=layer,
            options=options,
            table_path=table_path,
        )

    def _create_success_result(
        self,
        *,
        table_name: str,
        layer: str,
        options: ExportOptions,
        output_path: Path,
        row_count: int,
        manifest_paths: tuple[Path, ...] = (),
        audit_ref: str | None = None,
        redacted_columns: tuple[str, ...] = (),
    ) -> ExportResult:
        """Build result payload for successful export case."""
        return _create_success_result(
            table_name=table_name,
            layer=layer,
            options=options,
            output_path=output_path,
            row_count=row_count,
            manifest_paths=manifest_paths,
            audit_ref=audit_ref,
            redacted_columns=redacted_columns,
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
        return _create_failed_result(
            table_name=table_name,
            layer=layer,
            options=options,
            error=error,
        )

    def _get_table_path(self, table_name: str, layer: str) -> Path | str:
        """Get the table path through the catalog adapter."""
        base_path = self._get_layer_base_path(layer)
        result = self.catalog.resolve_table_path(
            base_path=str(base_path),
            table_name=table_name,
            layer=layer,
        )
        return result if isinstance(result, str) else Path(result)

    def _get_layer_base_path(self, layer: str) -> Path:
        """Resolve the root path for one export layer."""
        return _get_layer_base_path(
            layer=layer,
            silver_path=self.silver_path,
            gold_path=self.gold_path,
        )


__all__ = [
    "ColumnInfo",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "TableInfo",
    "TablePreview",
]
