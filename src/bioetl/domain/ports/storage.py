"""Storage port for Medallion layer operations.

This port abstracts the underlying storage mechanism (file system, data lake)
allowing the application to write data to Bronze/Silver/Gold layers.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from bioetl.domain.types import (
    ArrowSchema,
    BatchID,
    HealthStatus,
    RunID,
    RunType,
)


@runtime_checkable
class StoragePort(Protocol):
    """Port for data storage (Bronze, Silver, Gold layers).

    This interface abstracts the underlying storage mechanism (e.g., file system,
    data lake, data warehouse), allowing the application to write data to
    different layers without knowing the implementation details.
    """

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> Path:
        """Write raw records to the Bronze layer.

        Args:
            records: An iterable of byte strings, where each string is a raw record.
            provider: The name of the data provider.
            entity: The type of entity being written.
            date: The datetime for the data partition.
            batch_id: The unique identifier for the batch of records.
            run_id: The unique identifier for the pipeline run (for traceability).
            run_type: The type of pipeline run (incremental, backfill, rebuild).
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.

        Returns:
            Path: Relative path to the written file.
        """
        ...

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
    ) -> None:
        """Write transformed records to the Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift:
                - 'error': Raise SchemaEvolutionError (default)
                - 'evolve': Allow schema evolution (add new columns)
                - 'ignore': Proceed without changes (filter to existing schema)

        Raises:
            SchemaEvolutionError: If schema drift detected and on_schema_mismatch='error'
        """
        ...

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: Any,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
    ) -> None:
        """Write aggregated or validated records to the Gold layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a gold record.
            schema: Pandera DataFrameSchema for strict validation (required).
            primary_keys: Optional list of column names for sorting/deduplication.
            mode: The write mode (e.g., 'overwrite', 'append', 'scd2').

        Raises:
            ValueError: If schema validation fails (strict=True required).
        """
        ...

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the storage connection and release resources."""
        ...

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and basic write capability.

        Validates:
        - Bronze, Silver, Gold directories exist or can be created
        - Directories are writable

        Returns:
            HealthStatus indicating storage health:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (some layers unavailable)
            - UNHEALTHY: Storage completely unavailable
        """
        ...

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh CSV exports without duplicates from previous runs.

        Args:
            table_name: If provided, only clear CSV for this table.
                       If None, clear all CSV files.

        Returns:
            Total number of files deleted.
        """
        ...

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh data without duplicates from previous runs.

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Total number of tables cleared.
        """
        ...

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to remove old file versions.

        Removes files no longer referenced by the Delta log and older
        than retention period. Uses delta-rs VACUUM operation.

        Args:
            table_name: Table name in format "provider.entity" (e.g., "chembl.activity")
            retention_hours: Minimum age of files to remove (default 168h = 7 days)
            dry_run: If True, only report what would be removed

        Returns:
            Number of files removed (or would be removed if dry_run)

        Raises:
            StorageError: If vacuum operation fails
        """
        ...

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage.

        Copies table data to archive location. Optionally removes source.

        Args:
            table_name: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived

        Raises:
            StorageError: If archive operation fails
        """
        ...

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> dict[str, Any]:
        """Preview what would be cleared without actual deletion.

        Used by CLI dry-run mode to show users what data would be affected
        before performing a rebuild or backfill operation.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with structure:
            {
                "silver": {"path": str, "file_count": int, "exists": bool},
                "gold": {"path": str, "file_count": int, "exists": bool} | None,
                "total_files": int
            }
        """
        ...
