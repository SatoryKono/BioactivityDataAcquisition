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
        """Resolve the full path to a Delta table."""
        ...

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to remove old file versions."""
        ...

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity."""
        ...

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage."""
        ...

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Preview what would be cleared without actual deletion."""
        ...

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers."""
        ...

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers."""
        ...


__all__ = ["StorageMaintenancePort"]
