"""Unified cleanup service for Silver and Gold layers.

Implements single entry point for preview and actual cleanup operations.
Used by both CLI (dry-run preview) and PipelineRunner (actual cleanup).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


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
        _storage: StoragePort for data layer operations.
        _logger: LoggerPort for structured logging.

    Example:
        >>> service = CleanupService(storage=storage, logger=logger)
        >>> preview = await service.preview("chembl_activity", "chembl.activity")
        >>> print(f"Would clear {preview.total_files} files")
        >>> result = await service.execute(
        ...     silver_table="chembl_activity",
        ...     gold_table="chembl.activity",
        ...     dry_run=False,
        ... )
        >>> print(f"Cleared {result.total_cleared} items")
    """

    def __init__(self, storage: StoragePort, logger: LoggerPort) -> None:
        """Initialize cleanup service.

        Args:
            storage: StoragePort for data layer operations.
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
        # Use sync preview_cleanup from StoragePort
        preview_dict = self._storage.preview_cleanup(
            silver_table=silver_table,
            gold_table=gold_table,
        )

        silver_info = self._parse_layer_info(preview_dict.get("silver", {}))
        gold_info = None
        if preview_dict.get("gold"):
            gold_info = self._parse_layer_info(preview_dict["gold"])

        total_files = preview_dict.get("total_files", 0)

        self._logger.debug(
            "cleanup_preview",
            silver_table=silver_table,
            gold_table=gold_table,
            total_files=total_files,
        )

        return CleanupPreview(
            silver=silver_info,
            gold=gold_info,
            total_files=total_files,
        )

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

    def _parse_layer_info(self, info_dict: dict[str, Any]) -> LayerInfo:
        """Parse layer info from storage preview response.

        Args:
            info_dict: Dictionary with layer information.

        Returns:
            LayerInfo dataclass.
        """
        return LayerInfo(
            path=info_dict.get("path", ""),
            file_count=info_dict.get("file_count", 0),
            exists=info_dict.get("exists", False),
        )

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
