# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Delta IO sub-mixins used by `GoldWriterIOMixin` composition."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from bioetl.infrastructure.storage.gold.commit_outcome import (
    await_physical_commit,
    receipt_for,
)
from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _build_simple_gold_write,
    _execute_prepared_scd2_gold_write,
    _execute_prepared_simple_gold_write,
    _gold_write_retry_delay,
    _GoldWriterDeltaModuleProtocol,
    _prepare_scd2_gold_write,
    _run_gold_write_with_retry,
    _SimpleGoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from datetime import datetime

    import pyarrow as pa
    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol


class _GoldWriterExecutorArrowMixin:
    """Executor and Arrow conversion primitives reused by IO helpers."""

    logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]

    async def _run_in_executor(
        self,
        func: Callable[..., T],
        *args: object,
    ) -> T:
        """Run a local blocking helper behind the async writer facade."""
        # Keep blocking Gold Delta helpers off the event loop (ARCH-CR-01 / #6863).
        return await asyncio.to_thread(func, *args)

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> pa.Table:
        """Convert records to PyArrow table with Delta-safe null handling."""
        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )
        from bioetl.infrastructure.storage.delta.schema_ops import (
            drop_nondeterministic_persisted_fields,
        )

        converter = ArrowDataConverter(logger=self.logger)
        arrow_table = converter.convert_records_to_arrow(
            records,
            column_order=column_order,
        )
        return drop_nondeterministic_persisted_fields(arrow_table)


class _GoldWriterSimpleDeltaMixin(_GoldWriterExecutorArrowMixin):
    """Simple append/overwrite Delta write logic with retry policy."""

    csv_exporter: CsvExporterProtocol | None  # pyright: ignore[reportUninitializedInstanceVariable]

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
        prepared = _build_simple_gold_write(
            self,
            _SimpleGoldWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=mode,
                partition_cols=partition_cols,
                primary_keys=primary_keys,
                column_order=column_order,
            ),
        )
        module = cast(_GoldWriterDeltaModuleProtocol, _load_gold_writer_module())  # pyright: ignore[reportInvalidCast]
        await _execute_prepared_simple_gold_write(self, module, prepared)

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

    @staticmethod
    def _build_content_changed_predicate(
        source_alias: str = "source",
        target_alias: str = "target",
    ) -> str:
        """Build a null-safe content-hash change predicate."""
        return (
            f"{source_alias}.content_hash <> {target_alias}.content_hash "
            f"OR ({source_alias}.content_hash IS NULL AND {target_alias}.content_hash IS NOT NULL) "
            f"OR ({source_alias}.content_hash IS NOT NULL AND {target_alias}.content_hash IS NULL)"
        )

    @staticmethod
    def _build_current_snapshot_filter(
        *,
        business_keys: list[str],
        current_flag_col: str,
        records: list[GoldRecord],
    ) -> Any:
        """Filter the current SCD2 snapshot to keys present in this batch."""
        import pyarrow.dataset as ds

        current_filter = ds.field(current_flag_col).isin([True])
        if len(business_keys) == 1:
            key = business_keys[0]
            incoming_values = list(dict.fromkeys(record.get(key) for record in records))
            return current_filter & ds.field(key).isin(incoming_values)

        incoming_filter = None
        for record in records:
            record_filter = None
            for key in business_keys:
                value = record.get(key)
                field_filter = (
                    ds.field(key).is_null() if value is None else ds.field(key) == value
                )
                record_filter = (
                    field_filter
                    if record_filter is None
                    else record_filter & field_filter
                )
            incoming_filter = (
                record_filter
                if incoming_filter is None
                else incoming_filter | record_filter
            )

        if incoming_filter is None:
            raise ValueError("SCD2 snapshot filter requires at least one business key")
        return current_filter & incoming_filter

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
        prepared = _prepare_scd2_gold_write(
            table_path=table_path,
            records=records,
            scd_config=scd_config,
            partition_cols=partition_cols,
            ingestion_ts=ingestion_ts,
            column_order=column_order,
        )
        module = _load_gold_writer_module()
        await _execute_prepared_scd2_gold_write(self, module, prepared)

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
        import pyarrow as pa

        if not records:
            return

        business_keys = (
            [business_key] if isinstance(business_key, str) else business_key
        )
        marker_column = "__bioetl_scd2_expire"
        if any(marker_column in record for record in records):
            raise ValueError(f"Reserved SCD2 source field: {marker_column}")

        current_flag_col = scd_config.current_flag_col
        version_col = scd_config.version_col
        projected_columns = list(
            dict.fromkeys(
                [*business_keys, current_flag_col]
                + (
                    ["content_hash"]
                    if any("content_hash" in record for record in records)
                    else []
                )
                + (
                    [version_col]
                    if any(version_col in record for record in records)
                    else []
                )
            )
        )
        current_snapshot = await self._run_in_executor(
            lambda: dt.to_pyarrow_dataset().to_table(
                columns=projected_columns,
                filter=self._build_current_snapshot_filter(
                    business_keys=business_keys,
                    current_flag_col=current_flag_col,
                    records=records,
                ),
                use_threads=False,
            )
        )
        current_by_key = {
            tuple(row[key] for key in business_keys): row
            for row in current_snapshot.to_pylist()
        }

        has_content_hash = any("content_hash" in record for record in records)
        insert_records: list[GoldRecord] = []
        expire_records: list[GoldRecord] = []
        unchanged_records: list[GoldRecord] = []
        for input_record in records:
            record = dict(input_record)
            key = tuple(record.get(name) for name in business_keys)
            current = current_by_key.get(key)
            if current is None:
                insert_records.append({**record, marker_column: "insert"})
                continue
            changed = not has_content_hash or current.get("content_hash") != record.get(
                "content_hash"
            )
            if not changed:
                unchanged_records.append({**record, marker_column: "noop"})
                continue
            if version_col in record:
                record[version_col] = int(current.get(version_col, 0)) + 1
            expire_records.append({**record, marker_column: "expire"})
            insert_records.append({**record, marker_column: "insert"})

        source_records = [*expire_records, *insert_records, *unchanged_records]
        source_data = self._to_arrow_table(
            source_records,
            column_order=column_order,
        )
        valid_to_col = scd_config.valid_to_col
        merge_conditions = [f"source.{marker_column} = 'expire'"]
        merge_conditions.extend(f"target.{key} = source.{key}" for key in business_keys)
        merge_conditions.append(f"target.{current_flag_col} = true")
        merge_condition = " AND ".join(merge_conditions)
        ts_iso = ingestion_ts.isoformat()
        update_kwargs: dict[str, object] = {
            "updates": {
                valid_to_col: f"'{ts_iso}'",
                current_flag_col: "false",
            }
        }
        if has_content_hash:
            update_kwargs["predicate"] = self._build_content_changed_predicate()

        await await_physical_commit(
            lambda: self._run_in_executor(
                lambda: (
                    dt.merge(
                        source=pa.RecordBatchReader.from_batches(
                            source_data.schema, source_data.to_batches()
                        ),
                        predicate=merge_condition,
                        source_alias="source",
                        target_alias="target",
                    )
                    .when_matched_update(**update_kwargs)
                    .when_not_matched_insert(
                        updates={
                            field.name: f"source.{field.name}"
                            for field in source_data.schema
                            if field.name != marker_column
                        },
                        predicate=f"source.{marker_column} = 'insert'",
                    )
                    .execute()
                )
            ),
            receipt_for(str(dt.table_uri)),
        )


__all__ = [
    "_GoldWriterExecutorArrowMixin",
    "_GoldWriterScd2MergeMixin",
    "_GoldWriterSimpleDeltaMixin",
    "_SimpleGoldWriteRequest",
    "_build_simple_gold_write",
    "_gold_write_retry_delay",
    "_prepare_scd2_gold_write",
    "_run_gold_write_with_retry",
]
