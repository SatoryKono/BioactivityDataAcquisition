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

from datetime import datetime
from typing import Any

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.infrastructure.storage.exceptions import (
    MergeConflictError,
    SchemaValidationError,
    TableNotFoundError,
)


class DeltaWriter:
    """Writer for Silver layer (normalized data in Delta Lake).

    Implements merge/upsert strategy to handle updates and deduplication.

    Example:
        >>> writer = DeltaWriter(
        ...     base_path="s3://bioetl-silver",
        ...     storage_options={
        ...         "AWS_ENDPOINT_URL": "http://localhost:9000",
        ...         "AWS_ACCESS_KEY_ID": "bioetl",
        ...         "AWS_SECRET_ACCESS_KEY": "bioetl_minio_pass",
        ...         "AWS_REGION": "us-east-1",
        ...     }
        ... )
        >>> records = [
        ...     {
        ...         "entity_id": "CHEMBL123",
        ...         "value": 5.5,
        ...         "_run_id": "uuid-123",
        ...         "_source_batch_id": "batch-456"
        ...     }
        ... ]
        >>> writer.write_silver(
        ...     table_name="chembl.activity",
        ...     records=records,
        ...     primary_keys=["entity_id"],
        ...     partition_cols=["year", "month"]
        ... )
    """

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
    ) -> None:
        """Initialize Delta writer.

        Args:
            base_path: Base path for Delta tables (e.g., 's3://bioetl-silver')
            storage_options: Storage configuration for S3/MinIO:
                - AWS_ENDPOINT_URL: For MinIO (e.g., 'http://localhost:9000')
                - AWS_ACCESS_KEY_ID: Access key
                - AWS_SECRET_ACCESS_KEY: Secret key
                - AWS_REGION: Region (default: 'us-east-1')
        """
        self.base_path = base_path.rstrip("/")
        self.storage_options = storage_options or {}

    def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        partition_cols: list[str] | None = None,
    ) -> None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert).

        Requirements:
        - REQ-DATA-006: Delta Lake format (ACID)
        - REQ-DATA-008: Merge/Upsert strategy
        - REQ-LINEAGE-001: Records contain _source_batch_id

        Args:
            table_name: Table name (e.g., 'chembl.activity')
            records: List of normalized records with metadata:
                - entity_id: Business key
                - _run_id: Run UUID (correlation ID)
                - _run_type: incremental | backfill | rebuild
                - _source_batch_id: Batch ID for lineage
                - _ingestion_ts: Ingestion timestamp
            primary_keys: Keys for merge operation (e.g., ['entity_id'])
            partition_cols: Optional partition columns (e.g., ['year', 'month'])

        Raises:
            ValueError: If records list is empty or missing required metadata.
            SchemaValidationError: If record schema does not match table schema.
            MergeConflictError: If merge operation fails due to concurrent writes.
            CustomTableNotFoundError: If the underlying table is not found.
        """
        if not records:
            raise ValueError("No records to write")

        # Validate required metadata fields
        required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        first_record = records[0]
        missing_fields = required_fields - set(first_record.keys())
        if missing_fields:
            raise ValueError(
                f"Records missing required metadata fields: {missing_fields}"
            )

        # Construct table path
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        arrow_data = pa.Table.from_pylist(records)

        try:
            # Load existing table
            dt = DeltaTable(table_path, storage_options=self.storage_options)

            # Perform merge/upsert
            self._merge_records(dt, arrow_data, primary_keys)

        except DeltaTableNotFoundError:
            # Table doesn't exist, create it
            try:
                write_deltalake(
                    table_or_uri=table_path,
                    data=arrow_data,
                    mode="append",
                    partition_by=partition_cols,
                    storage_options=self.storage_options,
                )
            except ArrowTypeError as schema_exc:
                raise SchemaValidationError(
                    table_name, errors=[str(schema_exc)]
                ) from schema_exc
        except SchemaMismatchError as e:
            raise SchemaValidationError(table_name, errors=[str(e)]) from e
        except ArrowTypeError as e:
            raise SchemaValidationError(table_name, errors=[str(e)]) from e
        except DeltaError as e:
            # Catch potential merge conflicts
            if "Merge-conflict" in str(e):
                raise MergeConflictError(table_name, conflicts=1) from e
            raise

    def _merge_records(
        self,
        dt: DeltaTable,
        records: pa.Table,
        primary_keys: list[str],
    ) -> None:
        """Merge records into existing Delta table.

        Implements UPSERT logic:
        - If primary key exists: UPDATE with new values (based on _run_type priority)
        - If primary key doesn't exist: INSERT new record

        Requirements:
        - REQ-DATA-008: Merge/Upsert strategy
        - RULES.md §2.4: Merge priority (rebuild > backfill > incremental)

        Args:
            dt: Delta table instance
            records: New records to merge as a PyArrow Table
            primary_keys: Keys for matching records
        """
        # Build merge condition (match on primary keys)
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )

        # Merge with priority check
        # Priority: rebuild (3) > backfill (2) > incremental (1)
        # Only update if new run_type has higher or equal priority
        (
            dt.merge(
                source=records,
                predicate=merge_condition,
                source_alias="source",
                target_alias="target",
            )
            .when_matched_update_all(
                predicate=(
                    # Update if new run_type has higher priority
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
        )

    def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,  # 7 days default
        dry_run: bool = False,
    ) -> list[str]:
        """Run VACUUM operation to remove old file versions.

        Requirements:
        - REQ-DELTA-002: VACUUM with 7-day retention

        VACUUM removes files that are no longer referenced by the Delta log
        and older than the retention period. This reduces storage costs.

        Args:
            table_name: Table name (e.g., 'chembl.activity')
            retention_hours: Retention period in hours (default: 168 = 7 days)
            dry_run: If True, return files that would be deleted without deleting

        Returns:
            List of file paths deleted (or would be deleted if dry_run=True)

        Example:
            >>> writer = DeltaWriter(base_path="s3://bioetl-silver")
            >>> deleted = writer.vacuum("chembl.activity", retention_hours=168)
            >>> print(f"Deleted {len(deleted)} files")
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        try:
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            return dt.vacuum(retention_hours=retention_hours, dry_run=dry_run)
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    def optimize(
        self,
        table_name: str,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Optimize table by compacting small files.

        Combines small files into larger ones for better query performance.

        Args:
            table_name: Table name (e.g., 'chembl.activity')
            partition_filters: Optional partition filters (e.g., [('year', '=', 2025)])

        Returns:
            Optimization metrics (files added, removed, etc.)

        Example:
            >>> writer = DeltaWriter(base_path="s3://bioetl-silver")
            >>> metrics = writer.optimize("chembl.activity")
            >>> print(f"Compacted {metrics['numFilesRemoved']} files")
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        try:
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            return dt.optimize.compact(partition_filters=partition_filters)
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get table metadata and statistics.

        Args:
            table_name: Table name (e.g., 'chembl.activity')

        Returns:
            Dictionary with:
            - version: Current table version
            - num_files: Number of data files
            - size_bytes: Total size in bytes
            - schema: Table schema

        Example:
            >>> writer = DeltaWriter(base_path="s3://bioetl-silver")
            >>> info = writer.get_table_info("chembl.activity")
            >>> print(f"Table version: {info['version']}")
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        try:
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            return {
                "version": dt.version(),
                "num_files": len(dt.files()),
                "schema": dt.schema().to_pyarrow(),
                "metadata": dt.metadata(),
            }
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Access historical version of table (Time Travel).

        Requirements:
        - REQ-DATA-008: Time Travel support

        Args:
            table_name: Table name
            version: Table version number (mutually exclusive with timestamp)
            timestamp: Timestamp for version (mutually exclusive with version)

        Returns:
            Delta table at specified version/timestamp

        Example:
            >>> writer = DeltaWriter(base_path="s3://bioetl-silver")
            >>> # Access yesterday's version
            >>> historical = writer.time_travel(
            ...     "chembl.activity",
            ...     timestamp=datetime(2025, 12, 14)
            ... )
        """
        if version is not None and timestamp is not None:
            raise ValueError("Specify either version or timestamp, not both")

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"

        try:
            if version is not None:
                return DeltaTable(
                    table_path,
                    version=version,
                    storage_options=self.storage_options,
                )
            elif timestamp is not None:
                # Convert datetime to ISO format string
                timestamp_str = timestamp.isoformat()
                return DeltaTable(
                    table_path,
                    storage_options={
                        **self.storage_options,
                        "time_travel": timestamp_str,
                    },
                )
            else:
                raise ValueError("Must specify either version or timestamp")
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e
