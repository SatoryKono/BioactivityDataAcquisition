"""Unified cleanup service for Silver and Gold layers.

Implements single entry point for preview and actual cleanup operations.
Used by both CLI (dry-run preview) and PipelineRunner (actual cleanup).
"""

from __future__ import annotations

__all__ = ["CleanupPreview", "CleanupResult", "CleanupService", "LayerInfo"]

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.lifecycle._cleanup_support import (
    parse_cleanup_preview_parts,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import MetaDict


class CleanupStorageProtocol(Protocol):
    """Minimal cleanup-focused storage contract for CleanupService."""
    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Describe which layer paths and files would be affected."""
        ...
    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear or count Silver-layer data for one table."""
        ...
    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear or count Gold-layer data for one table."""
        ...


@dataclass(frozen=True, slots=True)
class LayerInfo:
    """Information about a medallion layer for cleanup preview.
    Attributes:
        path: Path to the layer directory.
        file_count: Number of files in the layer.
        exists: Whether the layer exists.
    """
    path: str
    file_count: int
    exists: bool


@dataclass(frozen=True, slots=True)
class CleanupPreview:
    """Result of cleanup preview operation.
    Attributes:
        silver: Silver layer information.
        gold: Gold layer information (None if not specified).
        total_files: Total number of files that would be affected.
    """
    silver: LayerInfo
    gold: LayerInfo | None
    total_files: int


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Result of cleanup execution.
    Attributes:
        silver_cleared: Number of items cleared from Silver layer.
        gold_cleared: Number of items cleared from Gold layer.
        dry_run: Whether this was a dry run (no actual deletion).
    """
    silver_cleared: int
    gold_cleared: int
    dry_run: bool
    @property
    def total_cleared(self) -> int:
        """Get total items cleared.
        Returns:
            Sum of silver and gold cleared items.
        """
        return self.silver_cleared + self.gold_cleared


class CleanupService:
    """Unified service for cleanup operations.
    Provides single entry point for both preview (dry-run) and actual
    cleanup operations. Used by CLI for --dry-run mode and by
    PipelineRunner for rebuild/backfill runs.
    Dependencies are injected via constructor following clean architecture.
    Attributes:
        _storage: CleanupStorageProtocol for data layer operations.
        _logger: LoggerPort for structured logging.
    Example:
        >>> service = CleanupService(storage=storage, logger=logger)
        >>> preview = await service.preview("chembl_activity", "chembl.activity")
        >>> preview.total_files  # Number of files to clear
        42
        >>> result = await service.execute(
        ...     silver_table="chembl_activity",
        ...     gold_table="chembl.activity",
        ...     dry_run=False,
        ... )
        >>> result.total_cleared  # Number of items cleared
        150
    """
    def __init__(self, storage: CleanupStorageProtocol, logger: LoggerPort) -> None:
        """Initialize cleanup service.
        Args:
            storage: Cleanup-focused storage port for data layer operations.
            logger: LoggerPort for structured logging.
        """
        self._storage = storage
        self._logger = logger
    async def preview(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> CleanupPreview:
        """Preview what would be cleared without actual deletion.
        Used by CLI --dry-run mode to show users what data would be affected
        before performing a rebuild or backfill operation.
        Args:
            silver_table: Silver table name (e.g., 'chembl.activity').
            gold_table: Optional Gold table name.
        Returns:
            CleanupPreview with information about affected layers.
        """
        await asyncio.sleep(0)
        # Use sync preview_cleanup from StorageMaintenancePort.
        preview_dict = self._storage.preview_cleanup(
            silver_table=silver_table,
            gold_table=gold_table,
        )
        silver_parts, gold_parts, total_files = parse_cleanup_preview_parts(
            preview_dict
        )
        preview = CleanupPreview(
            silver=LayerInfo(*silver_parts),
            gold=LayerInfo(*gold_parts) if gold_parts is not None else None,
            total_files=total_files,
        )
        self._logger.debug(
            "cleanup_preview",
            silver_table=silver_table,
            gold_table=gold_table,
            total_files=preview.total_files,
        )
        return preview
    async def execute(
        self,
        silver_table: str,
        gold_table: str | None = None,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Execute cleanup operation.
        Clears Silver and optionally Gold layer data.
        Supports dry_run mode for preview without actual deletion.
        Args:
            silver_table: Silver table name (e.g., 'chembl.activity').
            gold_table: Optional Gold table name.
            dry_run: If True, only count what would be deleted.
        Returns:
            CleanupResult with counts of cleared items.
        """
        silver_cleared = await self._storage.clear_silver(silver_table, dry_run=dry_run)
        gold_cleared = 0
        if gold_table:
            gold_cleared = await self._storage.clear_gold(gold_table, dry_run=dry_run)
        result = CleanupResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            dry_run=dry_run,
        )
        self._log_result(silver_table, gold_table, result)
        return result
    def _log_result(
        self,
        silver_table: str,
        gold_table: str | None,
        result: CleanupResult,
    ) -> None:
        """Log cleanup operation result.
        Args:
            silver_table: Silver table name.
            gold_table: Gold table name.
            result: The cleanup operation result.
        """
        if result.dry_run:
            self._logger.info(
                "DRY RUN: Would clear storage",
                silver_table=silver_table,
                gold_table=gold_table,
                silver_would_clear=result.silver_cleared,
                gold_would_clear=result.gold_cleared,
            )
        elif result.total_cleared > 0:
            self._logger.info(
                "Cleared storage",
                silver_table=silver_table,
                gold_table=gold_table,
                silver_cleared=result.silver_cleared,
                gold_cleared=result.gold_cleared,
            )
