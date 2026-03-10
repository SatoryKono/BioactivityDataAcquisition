"""Silver compaction orchestration extracted from PostrunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.medallion import SilverWriteMode

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.ports import LoggerPort, StorageMaintenancePort


class PostrunCompactService:
    """Deduplicates Silver table after APPEND or MERGE pipeline runs."""

    # DELETE overwrites the entire table, so dedup is unnecessary.
    _COMPACTABLE_MODES = frozenset({SilverWriteMode.APPEND, SilverWriteMode.MERGE})

    def __init__(
        self,
        *,
        config: PipelineConfig,
        storage: StorageMaintenancePort,
        logger: LoggerPort,
        warning_allowlist: tuple[type[BaseException], ...],
    ) -> None:
        self._config = config
        self._storage = storage
        self._logger = logger
        self._warning_allowlist = warning_allowlist

    async def run_if_needed(self) -> int:
        """Deduplicate Silver if write mode is APPEND or MERGE.

        Returns:
            Number of duplicate rows removed, or 0 if skipped.
        """
        table_cfg = self._config.table
        if table_cfg.silver_write_mode not in self._COMPACTABLE_MODES:
            return 0
        silver_table = self._config.effective_silver_table
        pks = list(table_cfg.primary_keys)
        if not silver_table or not pks:
            return 0

        self._logger.info("silver_compact_starting", silver_table=silver_table)
        try:
            removed = await self._storage.deduplicate_silver(silver_table, pks)
            self._logger.info("silver_compact_completed", duplicates_removed=removed)
            await self._optimize_files(silver_table)
            return removed
        except self._warning_allowlist as exc:
            self._logger.warning("silver_compact_failed", error=str(exc))
            return 0

    async def _optimize_files(self, silver_table: str) -> None:
        """Compact small parquet files after dedup to improve read performance."""
        try:
            self._logger.info("silver_optimize_starting", silver_table=silver_table)
            await self._storage.optimize(table_name=silver_table)
            self._logger.info("silver_optimize_completed", silver_table=silver_table)
        except self._warning_allowlist as exc:
            self._logger.warning("silver_optimize_failed", error=str(exc))


__all__ = ["PostrunCompactService"]
