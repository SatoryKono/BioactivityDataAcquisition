"""Gold layer writer (business-ready data with strict validation).

Implements RULES.md §2.1.1 - Gold Layer specifications.

Requirements:
- REQ-DATA-009: Strict validation (strict=True)
- REQ-DATA-010: SCD Type 2 or date partitioning
- REQ-CONTRACT-001: Published schemas in docs/contracts/

Architecture:
- Uses Pandera for strict schema validation
- Supports both Delta Lake and Parquet formats
- Implements SCD Type 2 (Slowly Changing Dimensions) for history tracking
- Enforces data contracts
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from pathlib import Path
import pyarrow.csv as pv
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from pandera.polars import DataFrameSchema
import pandera as pandera_pa


class GoldWriter:
    """Writer for Gold layer (validated business data).

    Enforces strict validation before writing. All records must pass
    schema validation or the entire batch fails.
    """

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
        csv_path: str | None = None,
        csv_options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Gold writer.

        Args:
            base_path: Base path for Gold tables
            storage_options: Storage options for S3/MinIO
            csv_path: Path for CSV export (None to disable)
            csv_options: CSV export options:
                - delimiter: Field delimiter (default: ",")
                - header: Include header row (default: True)
                - encoding: File encoding (default: "utf-8")
        """
        self.base_path = base_path.rstrip("/")
        self.storage_options = storage_options or {}
        self.csv_path = csv_path
        self.csv_options = csv_options or {}

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: DataFrameSchema | None = None,
        mode: str = "overwrite",
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
            await self._write_simple(table_path, records, mode, partition_cols, schema)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'overwrite', 'append', or 'scd2'")

    async def _run_in_executor(self, func, *args):
        """Run a function in the executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    async def _write_simple(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        mode: str,
        partition_cols: list[str] | None,
        schema: DataFrameSchema | None = None,
    ) -> None:
        """Write records using simple overwrite or append mode."""
        # Let pyarrow infer schema from data - pandera validation already done
        arrow_data = pa.Table.from_pylist(records)

        await self._run_in_executor(
            lambda: write_deltalake(
                table_or_uri=table_path,
                data=arrow_data,
                mode=mode,
                partition_by=partition_cols,
                storage_options=self.storage_options,
            )
        )

        if self.csv_path:
            csv_full_path = Path(self.csv_path) / f"{table_path.replace(self.base_path, '')}.csv"
            csv_full_path.parent.mkdir(parents=True, exist_ok=True)

            # Build CSV write options from config
            delimiter = self.csv_options.get("delimiter", ",")
            include_header = self.csv_options.get("header", True)

            write_options = pv.WriteOptions(
                include_header=include_header,
                delimiter=delimiter,
            )

            await self._run_in_executor(
                lambda: pv.write_csv(arrow_data, csv_full_path, write_options=write_options)
            )

    async def _write_scd2(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        scd_config: dict[str, Any],
        partition_cols: list[str] | None,
    ) -> None:
        """Write records using SCD Type 2 (history tracking)."""
        business_key = scd_config["business_key"]
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

        try:
            dt = await self._run_in_executor(
                lambda: DeltaTable(table_path, storage_options=self.storage_options)
            )
            await self._merge_scd2(dt, records, business_key, scd_config)
        except TableNotFoundError:
            arrow_data = pa.Table.from_pylist(records)
            await self._run_in_executor(
                lambda: write_deltalake(
                    table_or_uri=table_path,
                    data=arrow_data,
                    mode="append",
                    partition_by=partition_cols,
                    storage_options=self.storage_options,
                )
            )

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

        new_data = pa.Table.from_pylist(records)
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")
        merge_condition = " AND ".join(f"target.{key} = source.{key}" for key in business_keys)
        merge_condition += f" AND target.{current_flag_col} = true"
        now = datetime.now(UTC).isoformat()

        await self._run_in_executor(
            lambda: (
                dt.merge(
                    source=new_data,
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

    # ... (the rest of the file remains the same)
    async def read_gold(
        self,
        table_name: str,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        dt = await self._run_in_executor(
            lambda: DeltaTable(table_path, storage_options=self.storage_options)
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
            lambda: DeltaTable(table_path, storage_options=self.storage_options)
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
