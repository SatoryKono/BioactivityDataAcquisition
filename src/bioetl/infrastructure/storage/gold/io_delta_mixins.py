"""Delta IO sub-mixins used by `GoldWriterIOMixin` composition."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _build_simple_gold_write,
    _execute_prepared_scd2_gold_write,
    _execute_prepared_simple_gold_write,
    _GoldWriteAsyncioProtocol,
    _GoldWriterDeltaModuleProtocol,
    _GoldWriteRetryModuleProtocol,
    _prepare_scd2_gold_write,
    _SimpleGoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol


class _GoldWriterExecutorArrowMixin:
    """Executor and Arrow conversion primitives reused by IO helpers."""

    logger: LoggerPort

    async def _run_in_executor(
        self,
        func: Callable[..., T],
        *args: object,
    ) -> T:
        """Run a local blocking helper behind the async writer facade."""
        return await asyncio.to_thread(func, *args)

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> object:
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

    csv_exporter: CsvExporterProtocol | None

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
        module = cast(_GoldWriterDeltaModuleProtocol, _load_gold_writer_module())
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

        business_keys = (
            [business_key] if isinstance(business_key, str) else business_key
        )
        new_data = self._to_arrow_table(records, column_order=column_order)
        valid_to_col = scd_config.valid_to_col
        current_flag_col = scd_config.current_flag_col
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in business_keys
        )
        merge_condition += f" AND target.{current_flag_col} = true"
        ts_iso = ingestion_ts.isoformat()
        update_kwargs: dict[str, object] = {
            "updates": {
                valid_to_col: f"'{ts_iso}'",
                current_flag_col: "false",
            }
        }
        if "content_hash" in new_data.schema.names:
            update_kwargs["predicate"] = self._build_content_changed_predicate()

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
                .when_matched_update(**update_kwargs)
                .when_not_matched_insert_all()
                .execute()
            )
        )


def _gold_write_retry_delay(attempt: int) -> float:
    """Return the deterministic retry delay used by Gold write helpers."""
    return float((0.5 * (2**attempt)) + 0.05)


async def _run_gold_write_with_retry(
    module: object,
    operation: Callable[[], Awaitable[object]],
    max_attempts: int = 3,
) -> None:
    """Run a retryable async gold write operation using the legacy helper API."""
    retry_module = cast(_GoldWriteRetryModuleProtocol, module)
    retry_errors = retry_module.GOLD_WRITE_RETRY_ERRORS
    try:
        import pyarrow as pa
    except ImportError:
        pass
    else:
        if pa.ArrowException not in retry_errors:
            retry_errors = (*retry_errors, pa.ArrowException)
    sleep_module = cast(_GoldWriteAsyncioProtocol, getattr(module, "asyncio", asyncio))

    for attempt in range(max_attempts):
        try:
            await operation()
            return
        except retry_errors:
            if attempt >= max_attempts - 1:
                raise
            await sleep_module.sleep(_gold_write_retry_delay(attempt))


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
