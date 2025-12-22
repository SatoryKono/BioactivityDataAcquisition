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
- CSV export delegated to CsvExporter (composition)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

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

if TYPE_CHECKING:
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class DeltaWriter:
    """Writer for Silver layer (normalized data in Delta Lake).

    Implements merge/upsert strategy to handle updates and deduplication.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
        csv_exporter: CsvExporter | None = None,
    ) -> None:
        """Initialize Delta writer.

        Args:
            base_path: Base path for Delta tables
            storage_options: Storage options for S3/MinIO
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
        """
        self.base_path = base_path.rstrip("/")
        self.storage_options = storage_options or {}
        self.csv_exporter = csv_exporter

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
            raise ValueError(
                f"Records missing required metadata fields: {missing_fields}"
            )

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"

        # Filter records to only include fields in schema to avoid null type columns
        # Also serialize dict/list values to JSON strings for string-typed columns
        schema_fields = set(schema.names)
        string_fields = {
            field.name
            for field in schema
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
        # Use RecordBatchReader for better compatibility with delta-rs Arrow C Data interface
        arrow_reader = pa.RecordBatchReader.from_batches(
            schema, arrow_data.to_batches()
        )

        loop = asyncio.get_running_loop()

        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path, storage_options=self.storage_options),
            )
            await self._merge_records(dt, arrow_reader, primary_keys)
        except DeltaTableNotFoundError:
            try:
                # Re-create reader as it might have been consumed
                arrow_reader = pa.RecordBatchReader.from_batches(
                    schema, arrow_data.to_batches()
                )
                await loop.run_in_executor(
                    None,
                    lambda: write_deltalake(
                        table_or_uri=table_path,
                        data=arrow_reader,
                        mode="append",
                        partition_by=partition_cols,
                        storage_options=self.storage_options,
                    ),
                )
            except ArrowTypeError as schema_exc:
                raise SchemaViolationError(
                    table_name, errors=[str(schema_exc)]
                ) from schema_exc
        except (SchemaMismatchError, ArrowTypeError) as e:
            raise SchemaViolationError(table_name, errors=[str(e)]) from e
        except DeltaError as e:
            if "Merge-conflict" in str(e):
                raise MergeConflictError(table_name, conflicts=1) from e
            raise

        # Delegate CSV export to CsvExporter if configured
        if self.csv_exporter:
            await self.csv_exporter.export(table_name, arrow_data)

    async def _merge_records(
        self,
        dt: DeltaTable,
        records: pa.Table | pa.RecordBatchReader,
        primary_keys: list[str],
    ) -> None:
        """Merge records into existing Delta table."""
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )
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
