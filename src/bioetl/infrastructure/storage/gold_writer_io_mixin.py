"""Write/read and Delta operation helpers for GoldWriter."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

import pyarrow as pa

from bioetl.domain.medallion import GoldWriteMode

T = TypeVar("T")

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


def _load_gold_writer_module() -> ModuleType:
    """Load canonical gold_writer module to preserve monkeypatch points."""
    from importlib import import_module

    return import_module("bioetl.infrastructure.storage.gold_writer")


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


class GoldWriterIOMixin:
    """Mixin with write dispatch, SCD2 merge, and read helpers."""

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
        from bioetl.domain.schemas.column_order import canonical_column_order

        if not records:
            self.logger.warning(
                "No records to write for merged Gold",
                table_name=table_name,
            )
            return

        if schema is not None:
            await self._validate_records_against_schema(records, schema)

        arrow_table = pa.Table.from_pylist(records)

        module = _load_gold_writer_module()
        arrow_table = module.coerce_null_types_for_delta(arrow_table)

        if not preserve_column_order:
            ordered_columns = canonical_column_order(list(arrow_table.column_names))
            arrow_table = arrow_table.select(ordered_columns)

        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in arrow_table.schema.names]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(pk, "ascending") for pk in valid_keys]
                )

        table_path = self._resolve_table_path(table_name)

        self.logger.info(
            "Writing merged Gold records",
            table_name=table_name,
            path=table_path,
            records=len(records),
        )

        await self._run_in_executor(
            lambda: module.write_deltalake(
                table_path,
                arrow_table,
                mode="overwrite",
                schema_mode="overwrite",
            )
        )

        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_table,
                append=False,
            )

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
            await self._write_scd2(
                table_path,
                records,
                normalized,
                partition_cols,
                ingestion_ts,
                column_order,
            )
        else:
            await self._write_simple(
                table_path,
                table_name,
                records,
                mode.value,
                partition_cols,
                primary_keys,
                schema,
                column_order,
            )

    async def _run_in_executor(
        self,
        func: Callable[..., T],
        *args: Any,  # Any: variadic executor args
    ) -> T:
        """Run a function in the executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> pa.Table:
        """Convert records to PyArrow table, handling null types."""
        from bioetl.infrastructure.storage.arrow_converter import ArrowDataConverter

        converter = ArrowDataConverter(logger=self.logger)
        return converter.convert_records_to_arrow(
            records,
            column_order=column_order,
        )

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
    ) -> None:
        """Write records using simple overwrite or append mode."""
        arrow_data = self._to_arrow_table(records, column_order=column_order)
        if primary_keys:
            arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])

        schema_mode = "overwrite" if mode == "overwrite" else None
        module = _load_gold_writer_module()
        for attempt in range(3):
            try:
                await self._run_in_executor(
                    lambda table_or_uri=table_path, data=arrow_data, write_mode=mode, partition_by=partition_cols, resolved_schema_mode=schema_mode: (
                        module.write_deltalake(
                            table_or_uri=table_or_uri,
                            data=pa.RecordBatchReader.from_batches(
                                data.schema, data.to_batches()
                            ),
                            mode=write_mode,
                            partition_by=partition_by,
                            schema_mode=resolved_schema_mode,
                        )
                    )
                )
                break
            except module.GOLD_WRITE_RETRY_ERRORS as error:
                if attempt == 2:
                    raise error
                delay = 0.5 * (2**attempt) + 0.05
                await module.asyncio.sleep(delay)
        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_data,
                append=mode != "overwrite",
                primary_keys=primary_keys if mode != "overwrite" else None,
            )

    async def _write_scd2(
        self,
        table_path: str,
        records: list[GoldRecord],
        scd_config: ScdConfig,
        partition_cols: list[str] | None,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None:
        """Write records using SCD Type 2 (history tracking)."""
        business_key = scd_config["business_key"]
        sort_keys = [business_key] if isinstance(business_key, str) else business_key

        records.sort(key=lambda record: tuple(record.get(key) for key in sort_keys))
        version_col = scd_config.get("version_col", "version")
        valid_from_col = scd_config.get("valid_from_col", "valid_from")
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")

        ts_iso = ingestion_ts.isoformat()
        for record in records:
            record[valid_from_col] = ts_iso
            record[valid_to_col] = None
            record[current_flag_col] = True
            record[version_col] = record.get(version_col, 1)

        module = _load_gold_writer_module()

        for attempt in range(3):
            try:
                try:
                    dt = await self._run_in_executor(
                        lambda: module.DeltaTable(table_path)
                    )
                    await self._merge_scd2(
                        dt,
                        records,
                        business_key,
                        scd_config,
                        ingestion_ts,
                        column_order,
                    )
                except module.TableNotFoundError:
                    arrow_data = self._to_arrow_table(
                        records, column_order=column_order
                    )
                    await self._run_in_executor(
                        lambda table_or_uri=table_path, data=arrow_data, write_mode="append", partition_by=partition_cols: (
                            module.write_deltalake(
                                table_or_uri=table_or_uri,
                                data=pa.RecordBatchReader.from_batches(
                                    data.schema, data.to_batches()
                                ),
                                mode=write_mode,
                                partition_by=partition_by,
                            )
                        )
                    )
                break
            except module.GOLD_WRITE_RETRY_ERRORS as error:
                if attempt == 2:
                    raise error
                delay = 0.5 * (2**attempt) + 0.05
                await module.asyncio.sleep(delay)

    async def _merge_scd2(
        self,
        dt: Any,  # Any: deltalake DeltaTable untyped
        records: list[GoldRecord],
        business_key: str | list[str],
        scd_config: ScdConfig,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None:
        """Merge records using SCD Type 2 logic."""
        if isinstance(business_key, str):
            business_keys = [business_key]
        else:
            business_keys = business_key

        new_data = self._to_arrow_table(records, column_order=column_order)
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in business_keys
        )
        merge_condition += f" AND target.{current_flag_col} = true"
        ts_iso = ingestion_ts.isoformat()

        await self._run_in_executor(
            lambda: (
                dt.merge(
                    source=pa.RecordBatchReader.from_batches(
                        new_data.schema, new_data.to_batches()
                    ),
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update(
                    updates={
                        valid_to_col: f"'{ts_iso}'",
                        current_flag_col: "false",
                    }
                )
                .when_not_matched_insert_all()
                .execute()
            )
        )

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[GoldRecord]:
        """Read data from Gold table."""
        table_path = self._resolve_table_path(table_name)
        module = _load_gold_writer_module()

        dt = await self._run_in_executor(lambda: module.DeltaTable(table_path))
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)
        if current_only and "is_current" in arrow_table.column_names:
            import pyarrow.compute as pc

            arrow_table = arrow_table.filter(pc.equal(arrow_table["is_current"], True))
        result: list[GoldRecord] = arrow_table.to_pylist()
        if columns:
            selected = [{k: rec.get(k) for k in columns} for rec in result]
            return selected
        return result

    async def get_history(
        self,
        table_name: str,
        business_key_values: dict[str, Any] | None = None,  # Any: heterogeneous values
        limit: int = 10,
    ) -> list[GoldRecord]:
        """Get history of records in Gold table (for SCD2 tracking)."""
        table_path = self._resolve_table_path(table_name)
        module = _load_gold_writer_module()

        dt = await self._run_in_executor(lambda: module.DeltaTable(table_path))
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)

        if business_key_values:
            import pyarrow.compute as pc

            mask = None
            for key, value in business_key_values.items():
                condition = pc.equal(arrow_table[key], value)
                mask = condition if mask is None else pc.and_(mask, condition)
            if mask is not None:
                arrow_table = arrow_table.filter(mask)

        if "valid_from" in arrow_table.column_names:
            arrow_table = arrow_table.sort_by([("valid_from", "ascending")])
        result: list[GoldRecord] = arrow_table.to_pylist()
        return result[:limit] if limit > 0 else result


GoldWriterIOHelper = GoldWriterIOMixin

__all__ = ["GoldWriterIOHelper", "GoldWriterIOMixin"]
