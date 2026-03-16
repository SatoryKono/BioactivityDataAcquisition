"""Maintenance mixin for medallion lifecycle operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StorageMaintenancePort


_MAINTENANCE_OPERATION_ERRORS = (
    StorageError,
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


class _MedallionMaintenanceMixin:
    """Direct maintenance operations delegated to StorageMaintenancePort."""

    storage: StorageMaintenancePort
    logger: LoggerPort

    async def vacuum(
        self,
        table: str,
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> int:
        """Vacuum a Delta table and return removed file count.

        Args:
            table: Delta table name to vacuum.
            retention_days: Minimum file age in days before files are eligible
                for removal. Converted internally to hours for the storage call.
            dry_run: If True, report removable files without deleting them.

        Returns:
            Number of files removed (or that would be removed in dry_run mode).
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
        except _MAINTENANCE_OPERATION_ERRORS as e:
            self.logger.error("Vacuum failed", table=table, error=str(e))
            raise

    async def archive(
        self,
        table: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive table data to target path and optionally remove source.

        Args:
            table: Delta table name to archive.
            target_path: Destination path string for the archived data.
            remove_source: If True, remove source data after successful archiving.

        Returns:
            Number of files archived.
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
        except _MAINTENANCE_OPERATION_ERRORS as e:
            self.logger.error("Archive failed", table=table, error=str(e))
            raise
