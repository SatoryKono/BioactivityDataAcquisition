"""Bronze cleanup service for retention operations (Application layer).

Provides high-level Bronze layer cleanup for CLI and other interfaces.
Uses StoragePort for actual cleanup operations.

Implements RULES.md §2.1 - Bronze layer 90-day retention policy.
Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


@dataclass(frozen=True, slots=True)
class CleanupResult:
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


@dataclass
class BronzeCleanupService:
    """Service for Bronze layer cleanup operations.

    Provides high-level operations for Bronze cleanup
    used by CLI and other interfaces. Wraps StoragePort
    for Application-layer abstraction.

    Implements RULES.md §2.1 Bronze layer retention:
    - Default retention: 90 days
    - Files older than retention period are removed
    - Empty directories are cleaned up

    Attributes:
        storage: StoragePort for storage operations.
        logger: Structured logger for observability.

    Example:
        >>> service = BronzeCleanupService(storage=storage, logger=logger)
        >>> result = await service.cleanup(retention_days=90)
        >>> logger.info("cleanup_complete", files_removed=result.files_removed)
    """

    storage: StoragePort
    logger: LoggerPort

    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Clean up old Bronze files based on retention policy.

        Removes files older than the specified retention period.
        Per RULES.md §2.1, default retention is 90 days.

        Args:
            retention_days: Files older than this will be removed (default: 90).
            dry_run: If True, only show what would be removed.

        Returns:
            CleanupResult with cleanup statistics.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

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

        cleanup_result = CleanupResult(
            files_removed=result["files_removed"],
            bytes_freed=result["bytes_freed"],
            directories_removed=result["directories_removed"],
            dry_run=dry_run,
            cutoff_date=cutoff_date,
        )

        self._log_result(cleanup_result)

        return cleanup_result

    def _log_result(self, result: CleanupResult) -> None:
        """Log cleanup result.

        Args:
            result: The cleanup result to log.
        """
        action = "Would remove" if result.dry_run else "Removed"
        self.logger.info(
            f"{action} Bronze files",
            files_removed=result.files_removed,
            bytes_freed=result.bytes_freed,
            directories_removed=result.directories_removed,
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

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.storage.aclose()
