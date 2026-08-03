"""CSV adapter for loading source IDs used by ID mapping pipelines."""

from __future__ import annotations

__all__ = ["IDMappingCsvReaderAdapter"]

import asyncio
import csv
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class IDMappingCsvReaderAdapter:
    """Read mapping source IDs from CSV files."""

    def __init__(self, logger: LoggerPort | None = None) -> None:
        """Initialize adapter with optional logger."""
        self._logger = logger

    async def read_ids(self, source_path: str, id_column: str) -> list[str]:
        """Load ordered non-empty IDs from CSV source.

        Returns:
            List of non-empty stripped ID strings from the specified column.
        """
        return await asyncio.to_thread(self._read_ids_sync, source_path, id_column)

    async def source_exists(self, source_path: str) -> bool:
        """Check source file existence.

        Returns:
            True if the source file exists, False otherwise.
        """
        return await asyncio.to_thread(Path(source_path).exists)

    async def health_check(self) -> HealthStatus:
        """Return health status for local CSV reader adapter.

        Returns:
            HealthStatus.HEALTHY as local CSV reader is always available.
        """
        await asyncio.sleep(0)
        return HealthStatus.HEALTHY

    def _read_ids_sync(self, source_path: str, id_column: str) -> list[str]:
        """Synchronous CSV parsing implementation.

        Returns:
            List of non-empty stripped ID strings from the specified column.
        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {source_path}")

        with path.open(newline="", encoding="utf-8") as file_handle:
            reader = csv.DictReader(file_handle)
            if id_column not in (reader.fieldnames or []):
                raise ValueError(
                    f"Missing required column '{id_column}' in {source_path}"
                )
            ids = [
                item for row in reader if (item := (row.get(id_column) or "").strip())
            ]

        if self._logger:
            self._logger.debug(
                "idmapping_source_read_complete",
                source_path=source_path,
                record_count=len(ids),
                id_column=id_column,
            )
        return ids
