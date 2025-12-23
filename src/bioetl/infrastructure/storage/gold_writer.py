"""Gold layer writer (business-ready data with strict validation).

Implements RULES.md §2.1.1 - Gold Layer specifications.

Requirements:
- REQ-DATA-009: Strict validation (strict=True)
- REQ-DATA-010: SCD Type 2 or date partitioning
- REQ-CONTRACT-001: Published schemas in docs/contracts/

Architecture:
- Uses Pandera for strict schema validation
- Local filesystem storage with Delta Lake format
- Implements SCD Type 2 (Slowly Changing Dimensions) for history tracking
- Enforces data contracts
- CSV export delegated to CsvExporter (composition)
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pandera as pandera_pa
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class GoldWriter:
    """Writer for Gold layer (validated business data).

    Enforces strict validation before writing. All records must pass
    schema validation or the entire batch fails.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

    def __init__(
        self,
        base_path: str | Path,
        csv_exporter: CsvExporter | None = None,
    ) -> None:
        """Initialize Gold writer.

        Args:
            base_path: Base path for Gold tables (local filesystem)
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
        """
        self.base_path = str(base_path).rstrip("/")
        self.csv_exporter = csv_exporter

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        schema: DataFrameSchema | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: dict[str, Any] | None = None,
    ) -> None:
        """Write validated records to Gold layer."""
        if not records:
            raise ValueError("No records to write")

        if schema is not None:
            if not schema.strict:
                raise ValueError("Gold layer requires strict=True schema validation")
            import polars as pl

            df = pl.DataFrame(records)
            try:
                await self._run_in_executor(lambda: schema.validate(df, lazy=False))
            except pandera_pa.errors.SchemaError as e:
                raise ValueError(f"Schema validation failed: {e}") from e

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"

        if mode == "scd2":
            if scd_config is None:
                raise ValueError("scd_config required for SCD Type 2 mode")
            await self._write_scd2(table_path, records, scd_config, partition_cols)
        elif mode in ("overwrite", "append"):
            await self._write_simple(
                table_path,
                table_name,
                records,
                mode,
                partition_cols,
                primary_keys,
                schema,
            )
        else:
            raise ValueError(
                f"Invalid mode: {mode}. Use 'overwrite', 'append', or 'scd2'"
            )

    async def _run_in_executor(self, func, *args):
        """Run a function in the executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _sanitize_type_for_delta(self, dtype: pa.DataType) -> pa.DataType:
        """Recursively replace null types with string (Delta Lake doesn't support null)."""
        if pa.types.is_null(dtype):
            return pa.string()
        elif pa.types.is_list(dtype):
            inner = self._sanitize_type_for_delta(dtype.value_type)
            return pa.list_(inner)
        elif pa.types.is_large_list(dtype):
            inner = self._sanitize_type_for_delta(dtype.value_type)
            return pa.large_list(inner)
        elif pa.types.is_struct(dtype):
            new_fields = [
                pa.field(f.name, self._sanitize_type_for_delta(f.type), f.nullable)
                for f in dtype
            ]
            return pa.struct(new_fields)
        elif pa.types.is_map(dtype):
            key_type = self._sanitize_type_for_delta(dtype.key_type)
            item_type = self._sanitize_type_for_delta(dtype.item_type)
            return pa.map_(key_type, item_type)
        return dtype

    def _to_arrow_table(self, records: list[dict[str, Any]]) -> pa.Table:
        """Convert records to PyArrow table, handling null types.

        Delta Lake doesn't support null type, so we convert null columns to string.
        This includes nested null types (e.g., list<null>).
        """
        arrow_data = pa.Table.from_pylist(records)

        # Check if schema needs sanitization (contains null types anywhere)
        # Use lowercase check since PyArrow may print "null" or "Null"
        schema_str = str(arrow_data.schema).lower()
        if "null" in schema_str:
            # Can't cast null to string directly, need to rebuild columns
            new_columns = []
            new_fields = []
            for i, field in enumerate(arrow_data.schema):
                col = arrow_data.column(i)
                new_type = self._sanitize_type_for_delta(field.type)
                if pa.types.is_null(field.type):
                    # Create string array with all nulls
                    new_col = pa.array([None] * len(col), type=pa.string())
                    new_columns.append(new_col)
                elif new_type != field.type:
                    # Try to cast for nested types
                    try:
                        new_columns.append(col.cast(new_type))
                    except pa.ArrowInvalid:
                        # If cast fails, convert to string via Python
                        new_columns.append(
                            pa.array(
                                [
                                    str(v) if v is not None else None
                                    for v in col.to_pylist()
                                ],
                                type=pa.string(),
                            )
                        )
                else:
                    new_columns.append(col)
                new_fields.append(pa.field(field.name, new_type, field.nullable))

            new_schema = pa.schema(new_fields)
            arrow_data = pa.Table.from_arrays(new_columns, schema=new_schema)

        return arrow_data

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: DataFrameSchema | None = None,
    ) -> None:
        """Write records using simple overwrite or append mode."""
        arrow_data = self._to_arrow_table(records)

        # Sort by primary keys for deterministic writing
        if primary_keys:
            arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])

        for attempt in range(3):
            try:
                await self._run_in_executor(
                    lambda table_or_uri=table_path, data=arrow_data, mode=mode, partition_by=partition_cols: write_deltalake(
                        table_or_uri=table_or_uri,
                        data=pa.RecordBatchReader.from_batches(
                            data.schema, data.to_batches()
                        ),
                        mode=mode,
                        partition_by=partition_by,
                    )
                )
                break
            except Exception as e:
                # Retry on potential concurrency/protocol errors
                if attempt == 2:
                    raise e
                # Exponential backoff with jitter (Base 0.5s, Multiplier 2, Jitter 0.1s)
                delay = 0.5 * (2**attempt) + random.uniform(0, 0.1)
                await asyncio.sleep(delay)

        # Delegate CSV export to CsvExporter if configured
        if self.csv_exporter:
            # Match CSV append behavior to Delta mode
            csv_append = mode != "overwrite"
            await self.csv_exporter.export(table_name, arrow_data, append=csv_append)

    async def _write_scd2(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        scd_config: dict[str, Any],
        partition_cols: list[str] | None,
    ) -> None:
        """Write records using SCD Type 2 (history tracking)."""
        business_key = scd_config["business_key"]

        # Sort records by business key for deterministic processing
        sort_keys = [business_key] if isinstance(business_key, str) else business_key

        # Sort the input records list since we modify it in place
        records.sort(key=lambda r: tuple(r.get(k) for k in sort_keys))
        version_col = scd_config.get("version_col", "version")
        valid_from_col = scd_config.get("valid_from_col", "valid_from")
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")

        now = datetime.now(UTC).isoformat()
        for record in records:
            record[valid_from_col] = now
            record[valid_to_col] = None
            record[current_flag_col] = True
            record[version_col] = record.get(version_col, 1)

        for attempt in range(3):
            try:
                try:
                    dt = await self._run_in_executor(
                        lambda table_path=table_path: DeltaTable(table_path)
                    )
                    await self._merge_scd2(dt, records, business_key, scd_config)
                except TableNotFoundError:
                    arrow_data = self._to_arrow_table(records)
                    await self._run_in_executor(
                        lambda table_or_uri=table_path, data=arrow_data, mode="append", partition_by=partition_cols: write_deltalake(
                            table_or_uri=table_or_uri,
                            data=pa.RecordBatchReader.from_batches(
                                data.schema, data.to_batches()
                            ),
                            mode=mode,
                            partition_by=partition_by,
                        )
                    )
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                # Exponential backoff with jitter
                delay = 0.5 * (2**attempt) + random.uniform(0, 0.1)
                await asyncio.sleep(delay)

    async def _merge_scd2(
        self,
        dt: DeltaTable,
        records: list[dict[str, Any]],
        business_key: str | list[str],
        scd_config: dict[str, Any],
    ) -> None:
        """Merge records using SCD Type 2 logic."""
        if isinstance(business_key, str):
            business_keys = [business_key]
        else:
            business_keys = business_key

        new_data = self._to_arrow_table(records)
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in business_keys
        )
        merge_condition += f" AND target.{current_flag_col} = true"
        now = datetime.now(UTC).isoformat()

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
                        valid_to_col: f"'{now}'",
                        current_flag_col: "false",
                    }
                )
                .when_not_matched_insert_all()
                .execute()
            )
        )

    def clear(self, table_name: str | None = None) -> int:
        """Clear Gold Delta table(s) at the start of a pipeline run.

        Args:
            table_name: If provided, only clear this table.
                       If None, clear all tables in base_path.

        Returns:
            Number of tables cleared.
        """
        import shutil
        from pathlib import Path

        base = Path(self.base_path)
        if not base.exists():
            return 0

        cleared = 0
        if table_name:
            # Clear specific table
            table_path = base / table_name.replace(".", "/")
            if table_path.exists():
                shutil.rmtree(table_path)
                cleared = 1
        else:
            # Clear all Delta tables (directories with _delta_log)
            for item in base.iterdir():
                if item.is_dir() and (item / "_delta_log").exists():
                    shutil.rmtree(item)
                    cleared += 1

        return cleared

    async def read_gold(
        self,
        table_name: str,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        dt = await self._run_in_executor(
            lambda: DeltaTable(table_path)
        )
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)
        if current_only and "is_current" in arrow_table.column_names:
            import pyarrow.compute as pc

            arrow_table = arrow_table.filter(pc.equal(arrow_table["is_current"], True))
        return arrow_table.to_pylist()

    async def get_history(
        self,
        table_name: str,
        business_key_values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        dt = await self._run_in_executor(
            lambda: DeltaTable(table_path)
        )
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)
        import pyarrow.compute as pc

        mask = None
        for key, value in business_key_values.items():
            condition = pc.equal(arrow_table[key], value)
            mask = condition if mask is None else pc.and_(mask, condition)
        if mask is not None:
            arrow_table = arrow_table.filter(mask)
        if "valid_from" in arrow_table.column_names:
            arrow_table = arrow_table.sort_by([("valid_from", "ascending")])
        return arrow_table.to_pylist()
