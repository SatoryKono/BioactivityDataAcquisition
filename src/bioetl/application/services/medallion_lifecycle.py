"""Medallion lifecycle service (Application layer - orchestration).

Implements RULES.md §2.1-2.3 medallion architecture lifecycle operations.
This service manages clearing, vacuum, and future archive operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.ports import LoggerPort, StoragePort


@dataclass(frozen=True, slots=True)
class ClearResult:
    """Result of clear operation.

    Attributes:
        silver_cleared: Number of Silver records cleared.
        gold_cleared: Number of Gold records cleared.
        dry_run: Whether this was a dry run (no actual deletion).
    """

    silver_cleared: int
    gold_cleared: int
    dry_run: bool

    @property
    def total_cleared(self) -> int:
        """Get total records cleared.

        Returns:
            Sum of silver and gold cleared records.
        """
        return self.silver_cleared + self.gold_cleared


@dataclass
class MedallionLifecycleService:
    """Service for managing medallion layer lifecycle operations.

    Responsibilities:
    - Clear Silver/Gold tables based on policy (M5)
    - Future: vacuum, archive, optimize operations

    This service is injected into PipelineRunner and handles
    lifecycle operations that were previously inline in the runner.

    Attributes:
        storage: StoragePort for data layer operations.
        logger: Structured logger for observability.

    Example:
        >>> service = MedallionLifecycleService(storage=storage, logger=logger)
        >>> policy = MedallionPolicy.for_run_type(RunType.REBUILD)
        >>> result = await service.clear(
        ...     policy=policy,
        ...     silver_table="chembl_activity",
        ...     gold_table="chembl.activity",
        ...     dry_run=False,
        ... )
        >>> result.total_cleared  # Number of records cleared
        150
    """

    storage: StoragePort
    logger: LoggerPort

    async def clear(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        dry_run: bool = False,
    ) -> ClearResult:
        """Clear medallion layers according to policy.

        Enforces medallion architecture invariants:
        - Only clears based on policy (not run type directly)
        - Logs all operations for observability

        Args:
            policy: Medallion policy determining what to clear.
            silver_table: Silver table name.
            gold_table: Gold table name.
            dry_run: If True, only count without deleting.

        Returns:
            ClearResult with counts of cleared records.
        """
        silver_cleared = 0
        gold_cleared = 0

        if policy.should_clear_silver:
            silver_cleared = await self.storage.clear_silver(
                silver_table, dry_run=dry_run
            )

        if policy.should_clear_gold:
            gold_cleared = await self.storage.clear_gold(gold_table, dry_run=dry_run)

        result = ClearResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            dry_run=dry_run,
        )

        self._log_result(policy, silver_table, gold_table, result)

        return result

    def _log_result(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        result: ClearResult,
    ) -> None:
        """Log clear operation result.

        Args:
            policy: The medallion policy used.
            silver_table: Silver table name.
            gold_table: Gold table name.
            result: The clear operation result.
        """
        if result.dry_run:
            self.logger.info(
                "DRY RUN: Would clear storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_would_clear": result.silver_cleared,
                    "gold_would_clear": result.gold_cleared,
                },
            )
        elif result.total_cleared > 0:
            self.logger.info(
                "Cleared storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_cleared": result.silver_cleared,
                    "gold_cleared": result.gold_cleared,
                },
            )

    async def vacuum(
        self,
        table: str,
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to reclaim storage space.

        Removes files older than retention period that are no longer
        referenced by the Delta log. Safe to run concurrently with reads.

        Args:
            table: Table name in format "provider.entity"
            retention_days: Minimum age of files to remove (default 7)
            dry_run: If True, only report what would be removed

        Returns:
            Number of files removed

        Raises:
            StorageError: If vacuum fails
        """
        retention_hours = retention_days * 24

        self.logger.info(
            "Starting vacuum operation",
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        try:
            files_removed = await self.storage.vacuum(
                table_name=table,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )

            self.logger.info(
                "Vacuum completed",
                table=table,
                files_removed=files_removed,
                dry_run=dry_run,
            )

            return files_removed

        except Exception as e:
            self.logger.error(
                "Vacuum failed",
                table=table,
                error=str(e),
            )
            raise

    async def archive(
        self,
        table: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage.

        Copies table data to archive location. Optionally removes source
        after successful copy.

        Args:
            table: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived

        Raises:
            StorageError: If archive fails
        """
        self.logger.info(
            "Starting archive operation",
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        try:
            files_archived = await self.storage.archive(
                table_name=table,
                target_path=target_path,
                remove_source=remove_source,
            )

            self.logger.info(
                "Archive completed",
                table=table,
                files_archived=files_archived,
            )

            return files_archived

        except Exception as e:
            self.logger.error(
                "Archive failed",
                table=table,
                error=str(e),
            )
            raise
