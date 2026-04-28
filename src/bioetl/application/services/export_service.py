"""Export service for Delta Lake tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportFormat,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.application.services.export_manifests import (
    build_export_checksum_manifest,
    build_export_sidecar_payloads,
)
from bioetl.domain.exceptions import BioETLError, StorageError

if TYPE_CHECKING:
    import pyarrow as pa

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
                TableInfo(name=name, layer="silver", path=path)
                for name, path in self.catalog.list_tables(
                    base_path=self.silver_path,
                    layer="silver",
                )
            )
        if layer in ("all", "gold"):
            tables.extend(
                TableInfo(name=name, layer="gold", path=path)
                for name, path in self.catalog.list_tables(
                    base_path=self.gold_path,
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
        output_path = self.writer.write_export(
            table=table,
            table_name=table_name,
            layer=layer,
            fmt=options.format,
            output_dir=output_dir,
        )
        manifest_paths = (
            self._write_export_manifests(
                table=table,
                table_name=table_name,
                layer=layer,
                options=options,
                output_path=output_path,
                row_count=row_count,
            )
            if options.include_manifests
            else ()
        )
        self.logger.info(
            "Export completed",
            table=table_name,
            rows=row_count,
            output=str(output_path),
            manifests=[str(path) for path in manifest_paths],
        )
        return self._create_success_result(
            table_name=table_name,
            layer=layer,
            options=options,
            output_path=output_path,
            row_count=row_count,
            manifest_paths=manifest_paths,
        )

    def _write_export_manifests(
        self,
        *,
        table: pa.Table,
        table_name: str,
        layer: str,
        options: ExportOptions,
        output_path: Path,
        row_count: int,
    ) -> tuple[Path, ...]:
        """Write deterministic provenance, licensing, and checksum manifests."""
        data_fingerprint = self.writer.fingerprint_file(path=output_path)
        columns = tuple(field.name for field in table.schema)
        sidecars = build_export_sidecar_payloads(
            table_name=table_name,
            layer=layer,
            export_format=options.format,
            output_path=output_path,
            row_count=row_count,
            columns=columns,
            data_fingerprint=data_fingerprint,
            generated_at=options.manifest_generated_at,
            run_ids=options.run_ids,
            code_revision=options.code_revision,
            strict=options.manifest_strict,
        )
        manifest_prefix = output_path.stem
        provenance_path = self.writer.write_manifest(
            manifest_name=f"{manifest_prefix}.provenance-manifest",
            payload=sidecars.provenance_manifest,
            output_dir=output_path.parent,
        )
        licensing_path = self.writer.write_manifest(
            manifest_name=f"{manifest_prefix}.licensing-manifest",
            payload=sidecars.licensing_manifest,
            output_dir=output_path.parent,
        )
        manifest_generated_at = str(sidecars.provenance_manifest["generated_at"])
        checksum_payload = build_export_checksum_manifest(
            dataset_bundle_id=sidecars.dataset_bundle_id,
            generated_at=manifest_generated_at,
            fingerprints=(
                data_fingerprint,
                self.writer.fingerprint_file(path=provenance_path),
                self.writer.fingerprint_file(path=licensing_path),
            ),
        )
        checksums_path = self.writer.write_manifest(
            manifest_name=f"{manifest_prefix}.checksums-manifest",
            payload=checksum_payload,
            output_dir=output_path.parent,
        )
        return (provenance_path, licensing_path, checksums_path)

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
        manifest_paths: tuple[Path, ...] = (),
    ) -> ExportResult:
        """Build result payload for successful export case."""
        return ExportResult(
            table_name=table_name,
            layer=layer,
            format=options.format,
            output_path=output_path,
            row_count=row_count,
            manifest_paths=manifest_paths,
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

    def _get_table_path(self, table_name: str, layer: str) -> Path:
        """Get the table path through the catalog adapter."""
        base_path = self._get_layer_base_path(layer)
        return self.catalog.resolve_table_path(
            base_path=base_path,
            table_name=table_name,
            layer=layer,
        )

    def _get_layer_base_path(self, layer: str) -> Path:
        """Resolve the root path for one export layer."""
        if layer == "silver":
            return self.silver_path
        if layer == "gold":
            return self.gold_path
        raise ValueError(f"Invalid layer: {layer}")


__all__ = [
    "ColumnInfo",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "TableInfo",
    "TablePreview",
]
