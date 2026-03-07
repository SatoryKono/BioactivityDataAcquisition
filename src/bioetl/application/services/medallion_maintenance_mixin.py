"""Maintenance mixin for medallion lifecycle operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


_MAINTENANCE_OPERATION_ERRORS = (
    StorageError,
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


class _MedallionMaintenanceMixin:
    """Direct maintenance operations delegated to StoragePort."""

    storage: StoragePort
    logger: LoggerPort

    async def vacuum(
        self,
        table: str,
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> int:
        """Vacuum a Delta table and return removed file count."""
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
        """Archive table data to target path and optionally remove source."""
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
