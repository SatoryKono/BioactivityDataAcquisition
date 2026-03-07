"""Write/read and Delta operation helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, cast

import pyarrow as pa

from bioetl.domain.medallion import GoldWriteMode
from bioetl.infrastructure.storage.gold_writer_io_delta_mixins import (
    _GoldWriterExecutorArrowMixin,
    _GoldWriterScd2MergeMixin,
    _GoldWriterSimpleDeltaMixin,
)
from bioetl.infrastructure.storage.gold_writer_io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold_writer_read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
)

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class _GoldMergedMetadataWriterProtocol(Protocol):
    """Typed contract for merged-metadata writer implementation."""

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        schema: DataFrameSchema | None = None,
    ) -> None: ...


class _GoldWriteDispatchTargetProtocol(Protocol):
    """Protocol for dispatch targets implemented by concrete write mixins."""

    async def _write_scd2(
        self,
        table_path: str,
        records: list[GoldRecord],
        scd_config: ScdConfig,
        partition_cols: list[str] | None,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: DataFrameSchema | None = None,
        column_order: list[str] | None = None,
    ) -> None: ...


class _GoldWriterMergedDispatchMixin(_GoldWriterExecutorArrowMixin):
    """Merged-write orchestration and mode dispatch."""

    logger: LoggerPort
    csv_exporter: CsvExporter | None
    _resolve_table_path: Callable[[str], str]
    _validate_records_against_schema: Callable[
        [list[GoldRecord], DataFrameSchema], Awaitable[None]
    ]

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None = None,
        *,
        schema: DataFrameSchema | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Gold layer with optional strict validation."""
        if not records:
            self.logger.warning(
                "No records to write for merged Gold",
                table_name=table_name,
            )
            return

        if schema is not None:
            await self._validate_records_against_schema(records, schema)
        arrow_table = self._prepare_gold_merged_table(
            records=records,
            primary_keys=primary_keys,
            preserve_column_order=preserve_column_order,
        )
        table_path = self._resolve_table_path(table_name)
        self._log_gold_merged_write(table_name, table_path, len(records))
        await self._write_gold_merged_delta(table_path, arrow_table)
        await self._export_gold_merged_csv(table_name, arrow_table)
        await self._write_gold_merged_sidecar(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            schema=schema,
        )

    def _prepare_gold_merged_table(
        self,
        *,
        records: list[GoldRecord],
        primary_keys: list[str] | None,
        preserve_column_order: bool,
    ) -> pa.Table:
        """Build deterministic arrow table for merged Gold output."""
        from bioetl.domain.schemas.column_order import canonical_column_order

        module = _load_gold_writer_module()
        arrow_table = module.coerce_null_types_for_delta(pa.Table.from_pylist(records))
        if not preserve_column_order:
            ordered_columns = canonical_column_order(list(arrow_table.column_names))
            arrow_table = arrow_table.select(ordered_columns)
        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in arrow_table.schema.names]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(pk, "ascending") for pk in valid_keys]
                )
        return arrow_table

    def _log_gold_merged_write(
        self, table_name: str, table_path: str, count: int
    ) -> None:
        """Log merged Gold write intent."""
        self.logger.info(
            "Writing merged Gold records",
            table_name=table_name,
            path=table_path,
            records=count,
        )

    async def _write_gold_merged_delta(
        self, table_path: str, arrow_table: pa.Table
    ) -> None:
        """Persist merged Gold table to Delta."""
        module = _load_gold_writer_module()
        await self._run_in_executor(
            lambda: module.write_deltalake(
                table_path,
                arrow_table,
                mode="overwrite",
                schema_mode="overwrite",
            )
        )

    async def _export_gold_merged_csv(
        self, table_name: str, arrow_table: pa.Table
    ) -> None:
        """Export merged Gold table to CSV when exporter is configured."""
        if self.csv_exporter:
            await self.csv_exporter.export(table_name, arrow_table, append=False)

    async def _write_gold_merged_sidecar(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None,
        run_id: str | None,
        sources_used: list[str] | None,
        schema: DataFrameSchema | None,
    ) -> None:
        """Write merged Gold metadata sidecar via mixin protocol."""
        metadata_writer = cast(_GoldMergedMetadataWriterProtocol, self)
        await metadata_writer._write_gold_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys or [],
            run_id=run_id,
            sources_used=sources_used,
            schema=schema,
        )

    async def _dispatch_write(
        self,
        mode: GoldWriteMode,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        partition_cols: list[str] | None,
        primary_keys: list[str] | None,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        column_order: list[str] | None,
    ) -> None:
        """Dispatch to appropriate write method based on mode."""
        module = _load_gold_writer_module()

        if mode == GoldWriteMode.SCD2:
            assert ingestion_ts is not None
            assert scd_config is not None
            normalized = module._normalize_scd_config(scd_config, primary_keys)
            dispatch_target = cast(_GoldWriteDispatchTargetProtocol, self)
            await dispatch_target._write_scd2(
                table_path,
                records,
                normalized,
                partition_cols,
                ingestion_ts,
                column_order,
            )
            return
        dispatch_target = cast(_GoldWriteDispatchTargetProtocol, self)
        await dispatch_target._write_simple(
            table_path,
            table_name,
            records,
            mode.value,
            partition_cols,
            primary_keys,
            schema,
            column_order,
        )


class GoldWriterIOMixin(
    _GoldWriterMergedDispatchMixin,
    _GoldWriterSimpleDeltaMixin,
    _GoldWriterScd2MergeMixin,
    GoldWriterReadCleanupMixin,
):
    """Compose Gold writer IO responsibilities from focused mixins."""


__all__ = ["GoldWriterIOMixin"]
