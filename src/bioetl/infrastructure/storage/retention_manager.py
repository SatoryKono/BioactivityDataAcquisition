"""Delta table retention and maintenance operations.

Implements RULES.md §2.1.1 - Delta Lake specifications:
- REQ-DELTA-002: VACUUM scheduler (7-day retention)
- REQ-DELTA-003: Forensic retention (7-30 days configurable)
- REQ-DATA-008: Time Travel support

This module extracts maintenance operations from SilverWriter for better
separation of concerns:
- VACUUM: Remove old files no longer referenced by Delta log
- Optimize: Compact files for better query performance
- Time Travel: Read historical versions of tables
- Table Info: Retrieve metadata about Delta tables
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import TableNotFoundError

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class RetentionManager:
    """Manager for Delta table retention and maintenance operations.

    Handles VACUUM, optimize, time travel, and table metadata retrieval.
    Extracted from SilverWriter to improve separation of concerns.
    """

    def __init__(self, base_path: str | Path) -> None:
        """Initialize retention manager.

        Args:
            base_path: Base path for Delta tables (local filesystem).
        """
        self.base_path = str(base_path).rstrip("/")

    def _get_table_path(self, table_name: str) -> str:
        """Get the filesystem path for a table.

        Args:
            table_name: Table name (e.g., 'chembl.activity' or 'chembl_activity').

        Returns:
            Path string to the table directory.
        """
        return f"{self.base_path}/{table_name.replace('.', '/')}"

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files that are no longer referenced by the Delta log.

        Implements REQ-DELTA-002 and REQ-DELTA-003.

        Args:
            table_name: Table name.
            retention_hours: Hours of retention (default uses Delta Lake default of 168 hours).
                            Must be >= 168 hours unless explicitly overridden at table level.
            dry_run: If True, only list files to be deleted without deleting them.

        Returns:
            List of files deleted (or to be deleted in dry_run mode).

        Raises:
            TableNotFoundError: If table does not exist.
        """
        table_path = self._get_table_path(table_name)
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
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
        target_size: int | None = None,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Optimize table layout through file compaction.

        Compacts small files into larger ones for better query performance.

        Args:
            table_name: Table name.
            target_size: Target file size in bytes (currently unused, reserved for future
                        delta-rs API support).
            partition_filters: Optional filters to limit optimization to specific partitions.
                              Format: [(column, op, value), ...] e.g., [("date", "=", "2024-01-01")]

        Returns:
            Optimization metrics dictionary with details about files processed.

        Raises:
            TableNotFoundError: If table does not exist.
        """
        # Note: target_size reserved for future delta-rs API support
        _ = target_size  # Suppress unused variable warning
        table_path = self._get_table_path(table_name)
        loop = asyncio.get_running_loop()
        filters = partition_filters  # Capture for lambda closure
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return await loop.run_in_executor(
                None, lambda: dt.optimize.compact(partition_filters=filters)
            )
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get metadata about a Delta table.

        Args:
            table_name: Table name.

        Returns:
            Dictionary with table metadata:
            - version: Current table version number
            - num_files: Number of data files
            - schema: PyArrow schema of the table
            - metadata: Table metadata dictionary

        Raises:
            TableNotFoundError: If table does not exist.
        """
        table_path = self._get_table_path(table_name)
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return {
                "version": dt.version(),
                "num_files": len(dt.files()),
                "schema": dt.schema().to_arrow(),
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
        """Read a previous version of the table.

        Implements REQ-DATA-008 Time Travel support.

        Args:
            table_name: Table name.
            version: Version number to read (mutually exclusive with timestamp).
            timestamp: Timestamp to read table as of (mutually exclusive with version).

        Returns:
            DeltaTable instance at the specified version/timestamp.

        Raises:
            ValueError: If both version and timestamp are specified, or neither is specified.
            TableNotFoundError: If table does not exist.
        """
        if version is not None and timestamp is not None:
            raise ValueError("Specify either version or timestamp, not both")

        table_path = self._get_table_path(table_name)
        loop = asyncio.get_running_loop()

        try:
            if version is not None:
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        version=version,
                    ),
                )
            elif timestamp is not None:
                timestamp_str = timestamp.isoformat()
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        storage_options={
                            "time_travel": timestamp_str,
                        },
                    ),
                )
            else:
                raise ValueError("Must specify either version or timestamp")
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e
