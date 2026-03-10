"""Delta IO sub-mixins used by `GoldWriterIOMixin` composition."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

import pyarrow as pa

from bioetl.infrastructure.storage.gold_writer_io_helpers import (
    initialize_scd2_records as _initialize_scd2_records,
)
from bioetl.infrastructure.storage.gold_writer_io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold_writer_io_helpers import (
    write_scd2_once as _write_scd2_once,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class _GoldWriterExecutorArrowMixin:
    """Executor and Arrow conversion primitives reused by IO helpers."""

    logger: LoggerPort

    async def _run_in_executor(
        self,
        func: Callable[..., T],
        *args: object,
    ) -> T:
        """Run a function in the default thread pool executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> pa.Table:
        """Convert records to PyArrow table with Delta-safe null handling."""
        from bioetl.infrastructure.storage.arrow_converter import ArrowDataConverter

        converter = ArrowDataConverter(logger=self.logger)
        return converter.convert_records_to_arrow(
            records,
            column_order=column_order,
        )


class _GoldWriterSimpleDeltaMixin(_GoldWriterExecutorArrowMixin):
    """Simple append/overwrite Delta write logic with retry policy."""

    csv_exporter: CsvExporter | None

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

                def _write_delta_with_mode(
                    table_or_uri: str = table_path,
                    data: pa.Table = arrow_data,
                    write_mode: str = mode,
                    partition_by: list[str] | None = partition_cols,
                    resolved_schema_mode: str | None = schema_mode,
                ) -> None:
                    module.write_deltalake(
                        table_or_uri=table_or_uri,
                        data=pa.RecordBatchReader.from_batches(
                            data.schema, data.to_batches()
                        ),
                        mode=write_mode,
                        partition_by=partition_by,
                        schema_mode=resolved_schema_mode,
                    )

                await self._run_in_executor(_write_delta_with_mode)
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


    async def finalize_csv_export(
        self,
        table_name: str,
        primary_keys: list[str] | None = None,
    ) -> None:
        """One-shot CSV finalize: deduplicate and sort after all batches.

        Args:
            table_name: Logical table name whose CSV export to finalize.
            primary_keys: Optional primary key columns for deduplication.
        """
        if self.csv_exporter:
            await self.csv_exporter.finalize_csv(
                table_name,
                primary_keys=primary_keys,
            )


class _GoldWriterScd2MergeMixin(_GoldWriterExecutorArrowMixin):
    """SCD2 write and merge primitives with deterministic retries."""

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
        _initialize_scd2_records(records, scd_config, ingestion_ts)

        module = _load_gold_writer_module()
        for attempt in range(3):
            try:
                await _write_scd2_once(
                    self,
                    module=module,
                    table_path=table_path,
                    records=records,
                    business_key=business_key,
                    scd_config=scd_config,
                    ingestion_ts=ingestion_ts,
                    partition_cols=partition_cols,
                    column_order=column_order,
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
        business_keys = (
            [business_key] if isinstance(business_key, str) else business_key
        )
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


__all__ = [
    "_GoldWriterExecutorArrowMixin",
    "_GoldWriterScd2MergeMixin",
    "_GoldWriterSimpleDeltaMixin",
]
