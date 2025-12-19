"""Silver layer writer (Delta Lake with merge/upsert).

Implements RULES.md §2.1.1 - Silver Layer specifications.

Requirements:
- REQ-DATA-006: Delta Lake format (ACID transactions)
- REQ-DATA-007: Merge/Upsert strategy
- REQ-DATA-008: Time Travel support
- REQ-DELTA-001: Protocol Version (Writer 2, Reader 1)
- REQ-DELTA-002: VACUUM scheduler (7-day retention)
- REQ-DELTA-003: Forensic retention (7-30 days configurable)
- REQ-LINEAGE-001: Records contain _source_batch_id

Architecture:
- Uses deltalake (delta-rs) for Python
- Supports partitioning for query optimization
- Implements merge/upsert based on primary keys
- ACID guarantees for concurrent writes
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Literal
from pathlib import Path
import pyarrow.csv as pv
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import (
    MergeConflictError,
    SchemaViolationError,
    TableNotFoundError,
)


class DeltaWriter:
    """Writer for Silver layer (normalized data in Delta Lake).

    Implements merge/upsert strategy to handle updates and deduplication.
    """

    @staticmethod
    def _flatten_for_csv(table: pa.Table) -> pa.Table:
        """Convert complex types (list, struct) to JSON strings for CSV export."""
        import json as json_module

        new_columns = []
        for i, field in enumerate(table.schema):
            col = table.column(i)
            if pa.types.is_list(field.type) or pa.types.is_large_list(field.type) or pa.types.is_struct(field.type):
                json_strings = [
                    json_module.dumps(val.as_py()) if val.as_py() is not None else None
                    for val in col
                ]
                new_columns.append(pa.array(json_strings, type=pa.string()))
            else:
                new_columns.append(col)

        new_schema = pa.schema([
            pa.field(f.name, pa.string() if pa.types.is_list(f.type) or pa.types.is_large_list(f.type) or pa.types.is_struct(f.type) else f.type, f.nullable)
            for f in table.schema
        ])
        return pa.Table.from_arrays(new_columns, schema=new_schema)

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
        csv_path: str | None = None,
        csv_options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Delta writer.

        Args:
            base_path: Base path for Delta tables
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

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
    ) -> None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert)."""
        if not records:
            raise ValueError("No records to write")

        required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        if missing_fields := required_fields - set(records[0].keys()):
            raise ValueError(f"Records missing required metadata fields: {missing_fields}")

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"

        # Filter records to only include fields in schema to avoid null type columns
        # Also serialize dict/list values to JSON strings for string-typed columns
        schema_fields = set(schema.names)
        string_fields = {
            field.name for field in schema
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
        }

        def serialize_value(key: str, value):
            """Serialize dict/list values to JSON strings for string columns."""
            if value is None:
                return None
            if key in string_fields and isinstance(value, (dict, list)):
                return json.dumps(value)
            return value

        filtered_records = [
            {k: serialize_value(k, v) for k, v in rec.items() if k in schema_fields}
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)

        loop = asyncio.get_running_loop()

        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path, storage_options=self.storage_options),
            )
            await self._merge_records(dt, arrow_data, primary_keys)
        except DeltaTableNotFoundError:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: write_deltalake(
                        table_or_uri=table_path,
                        data=arrow_data,
                        mode="append",
                        partition_by=partition_cols,
                        storage_options=self.storage_options,
                    ),
                )
            except ArrowTypeError as schema_exc:
                raise SchemaViolationError(table_name, errors=[str(schema_exc)]) from schema_exc
        except (SchemaMismatchError, ArrowTypeError) as e:
            raise SchemaViolationError(table_name, errors=[str(e)]) from e
        except DeltaError as e:
            if "Merge-conflict" in str(e):
                raise MergeConflictError(table_name, conflicts=1) from e
            raise

        if self.csv_path:
            csv_full_path = Path(self.csv_path) / f"{table_name}.csv"
            csv_full_path.parent.mkdir(parents=True, exist_ok=True)

            # Build CSV write options from config
            delimiter = self.csv_options.get("delimiter", ",")
            include_header = self.csv_options.get("header", True)

            write_options = pv.WriteOptions(
                include_header=include_header,
                delimiter=delimiter,
            )

            # Convert list/struct columns to JSON strings for CSV compatibility
            csv_data = self._flatten_for_csv(arrow_data)

            await loop.run_in_executor(
                None,
                lambda: pv.write_csv(csv_data, csv_full_path, write_options=write_options)
            )

    async def _merge_records(
        self,
        dt: DeltaTable,
        records: pa.Table,
        primary_keys: list[str],
    ) -> None:
        """Merge records into existing Delta table."""
        merge_condition = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: (
                dt.merge(
                    source=records,
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update_all(
                    predicate=(
                        "CASE "
                        "WHEN source._run_type = 'rebuild' THEN 3 "
                        "WHEN source._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END >= "
                        "CASE "
                        "WHEN target._run_type = 'rebuild' THEN 3 "
                        "WHEN target._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END"
                    )
                )
                .when_not_matched_insert_all()
                .execute()
            ),
        )

    # ... (the rest of the file remains the same)
    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,  # 7 days default
        dry_run: bool = False,
    ) -> list[str]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path, storage_options=self.storage_options),
            )
            return await loop.run_in_executor(
                None,
                lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
            )
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def optimize(
        self,
        table_name: str,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path, storage_options=self.storage_options),
            )
            return await loop.run_in_executor(
                None, lambda: dt.optimize.compact(partition_filters=partition_filters)
            )
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path, storage_options=self.storage_options),
            )
            return {
                "version": dt.version(),
                "num_files": len(dt.files()),
                "schema": dt.schema().to_pyarrow(),
                "metadata": dt.metadata(),
            }
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        if version is not None and timestamp is not None:
            raise ValueError("Specify either version or timestamp, not both")

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()

        try:
            if version is not None:
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        version=version,
                        storage_options=self.storage_options,
                    ),
                )
            elif timestamp is not None:
                timestamp_str = timestamp.isoformat()
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        storage_options={
                            **self.storage_options,
                            "time_travel": timestamp_str,
                        },
                    ),
                )
            else:
                raise ValueError("Must specify either version or timestamp")
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e
