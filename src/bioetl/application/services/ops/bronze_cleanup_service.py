"""Bronze cleanup service for retention operations (Application layer).

Provides high-level Bronze layer cleanup for CLI and other interfaces.
Uses BronzeStoragePort for actual cleanup operations.

Implements RULES.md §2.1 - Bronze layer 90-day retention policy.
Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = ["BronzeCleanupResult", "BronzeCleanupService"]


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import resolve_runtime_clock

if TYPE_CHECKING:
    from bioetl.domain.ports import BronzeStoragePort, ClockPort, LoggerPort


@dataclass(frozen=True, slots=True)
class BronzeCleanupResult:
    """Result of Bronze cleanup operation.

    Attributes:
        files_removed: Number of files removed.
        bytes_freed: Total bytes freed.
        directories_removed: Number of empty directories removed.
        dry_run: Whether this was a dry run.
        cutoff_date: Cutoff date used for cleanup.
    """

    files_removed: int
    bytes_freed: int
    directories_removed: int
    dry_run: bool
    cutoff_date: datetime
    files_planned: int = 0
    bytes_planned: int = 0
    directories_planned: int = 0
    files_skipped: int = 0
    bytes_skipped: int = 0
    directories_skipped: int = 0
    files_conflicted: int = 0
    bytes_conflicted: int = 0
    directories_conflicted: int = 0
    files_failed: int = 0
    bytes_failed: int = 0
    directories_failed: int = 0


@dataclass
class BronzeCleanupService:
    """Service for Bronze layer cleanup operations.

    Provides high-level operations for Bronze cleanup
    used by CLI and other interfaces. Depends on the narrow
    ``BronzeStoragePort`` (ISP — only Bronze operations needed).

    Implements RULES.md §2.1 Bronze layer retention:
    - Default retention: 90 days
    - Files older than retention period are removed
    - Empty directories are cleaned up

    Attributes:
        storage: BronzeStoragePort for Bronze storage operations.
        logger: Structured logger for observability.

    Example:
        >>> service = BronzeCleanupService(storage=storage, logger=logger)
        >>> result = await service.cleanup(retention_days=90)
        >>> logger.info("cleanup_complete", files_removed=result.files_removed)
    """

    storage: BronzeStoragePort
    logger: LoggerPort
    clock: ClockPort

    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> BronzeCleanupResult:
        """Clean up old Bronze files based on retention policy.

        Removes files older than the specified retention period.
        Per RULES.md §2.1, default retention is 90 days.

        Args:
            retention_days: Files older than this will be removed (default: 90).
            dry_run: If True, only show what would be removed.

        Returns:
            BronzeCleanupResult with cleanup statistics.
        """
        if retention_days < 0:
            raise ValueError("retention_days cannot be negative")
        now = resolve_runtime_clock(self.clock).now()
        cutoff_date = now - timedelta(days=retention_days)

        self.logger.info(
            "Starting Bronze cleanup",
            retention_days=retention_days,
            cutoff_date=cutoff_date.isoformat(),
            dry_run=dry_run,
        )

        result = await self.storage.cleanup_bronze(
            cutoff_date=cutoff_date,
            dry_run=dry_run,
        )

        cleanup_result = BronzeCleanupResult(
            files_removed=result["files_removed"],
            bytes_freed=result["bytes_freed"],
            directories_removed=result["directories_removed"],
            dry_run=dry_run,
            cutoff_date=cutoff_date,
            files_planned=result.get("files_planned", 0),
            bytes_planned=result.get("bytes_planned", 0),
            directories_planned=result.get("directories_planned", 0),
            files_skipped=result.get("files_skipped", 0),
            bytes_skipped=result.get("bytes_skipped", 0),
            directories_skipped=result.get("directories_skipped", 0),
            files_conflicted=result.get("files_conflicted", 0),
            bytes_conflicted=result.get("bytes_conflicted", 0),
            directories_conflicted=result.get("directories_conflicted", 0),
            files_failed=result.get("files_failed", 0),
            bytes_failed=result.get("bytes_failed", 0),
            directories_failed=result.get("directories_failed", 0),
        )

        self._log_result(cleanup_result)

        return cleanup_result

    def _log_result(self, result: BronzeCleanupResult) -> None:
        """Log cleanup result.

        Args:
            result: The cleanup result to log.
        """
        self.logger.info(
            "bronze_cleanup_completed",
            files_removed=result.files_removed,
            bytes_freed=result.bytes_freed,
            directories_removed=result.directories_removed,
            files_planned=result.files_planned,
            bytes_planned=result.bytes_planned,
            directories_planned=result.directories_planned,
            files_skipped=result.files_skipped,
            bytes_skipped=result.bytes_skipped,
            directories_skipped=result.directories_skipped,
            files_conflicted=result.files_conflicted,
            bytes_conflicted=result.bytes_conflicted,
            directories_conflicted=result.directories_conflicted,
            files_failed=result.files_failed,
            bytes_failed=result.bytes_failed,
            directories_failed=result.directories_failed,
            cutoff_date=result.cutoff_date.isoformat(),
            dry_run=result.dry_run,
        )

    @staticmethod
    def format_bytes(b: int) -> str:
        """Format bytes as human-readable string.

        Args:
            b: Number of bytes.

        Returns:
            Human-readable string (e.g., "1.5 GB").
        """
        for unit, div in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
            if b >= div:
                return f"{b / div:.2f} {unit}"
        return f"{b} bytes"
