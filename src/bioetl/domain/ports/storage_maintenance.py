"""Storage maintenance protocol for cross-layer operations."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from bioetl.domain.types import MetaDict


@runtime_checkable
class StorageMaintenancePort(Protocol):
    """Port for cross-layer storage maintenance operations."""

    def get_table_path(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> Path:
        """Resolve the full path to a Delta table.

        Args:
            table_name: Logical table name or entity path.
            layer: Medallion layer to resolve the path for. Defaults to 'silver'.

        Returns:
            Absolute Path to the Delta table directory.
        """
        ...

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to remove old file versions.

        Args:
            table_name: Logical table name to vacuum.
            retention_hours: Minimum age in hours for files to be eligible for deletion. Defaults to 168.
            dry_run: If True, reports what would be deleted without removing files. Defaults to False.

        Returns:
            Number of files deleted (or that would be deleted in dry_run mode).
        """
        ...

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity.

        Args:
            table_name: Logical table name to optimize.
            retention_hours: Retention hours passed to the underlying vacuum step. Defaults to 168.
            dry_run: If True, reports what would be optimized without making changes. Defaults to False.
        """
        ...

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage.

        Args:
            table_name: Logical table name to archive.
            target_path: Destination path for the archived data.
            remove_source: If True, removes the source table after archiving. Defaults to False.

        Returns:
            Number of records archived.
        """
        ...

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Preview what would be cleared without actual deletion.

        Args:
            silver_table: Name of the Silver table to inspect.
            gold_table: Optional name of the Gold table to inspect. Defaults to None.

        Returns:
            Dictionary summarising the tables and counts that would be affected.
        """
        ...

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        """Deduplicate Silver table by primary keys after append-mode writes.

        Keeps the latest record per primary key group (by _ingestion_ts).

        Args:
            table_name: Logical Silver table name.
            primary_keys: Business key columns for deduplication.

        Returns:
            Number of duplicate rows removed.
        """
        ...

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Args:
            table_name: If provided, clears only files for this table. Defaults to None (clears all).

        Returns:
            Number of CSV files deleted.
        """
        ...

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Args:
            table_name: If provided, clears only this Delta table. Defaults to None (clears all).

        Returns:
            Number of Delta tables cleared.
        """
        ...


__all__ = ["StorageMaintenancePort"]
