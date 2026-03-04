"""Delta Lake reader for table access and export.

Provides read-only access to Silver/Gold Delta Lake tables
using delta-rs library.

Implements DeltaReaderPort for export utilities.
"""

from __future__ import annotations

__all__ = ["DeltaReader"]


import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class DeltaReader:
    """Read-only accessor for Delta Lake tables.

    Provides efficient reading with column projection and row limiting.
    Uses async wrappers around sync delta-rs operations.
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
    ) -> None:
        """Initialize Delta reader.

        Args:
            base_path: Base path for Delta table storage.
                      Tables are read from subdirectories (e.g., base_path/chembl/activity/).
            logger: Structured logger for observability (MUST be injected).
        """
        self._base_path = Path(base_path)
        self._logger = logger

    def _resolve_path(self, table_path: str) -> Path:
        """Resolve table path to absolute path.

        Handles both relative paths (provider/entity) and absolute paths.

        Args:
            table_path: Table path, can be relative (chembl/activity) or absolute.

        Returns:
            Absolute Path to the table directory.
        """
        path = Path(table_path)
        if path.is_absolute():
            return path
        return self._base_path / table_path

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read data from a Delta Lake table.

        Args:
            table_path: Path to the Delta table (relative or absolute).
            columns: Optional list of columns to read (projection pushdown).
            limit: Optional maximum number of rows to read.

        Returns:
            PyArrow Table with the requested data.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _read() -> pa.Table:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            # Build read with optional column projection
            table = dt.to_pyarrow_table(columns=columns)

            # Apply row limit if specified
            if limit is not None and limit < table.num_rows:
                table = table.slice(0, limit)

            return table

        self._logger.debug(
            "Reading Delta table",
            path=str(resolved_path),
            columns=columns,
            limit=limit,
        )

        return await loop.run_in_executor(None, _read)

    async def get_schema(self, table_path: str) -> pa.Schema:
        """Get the schema of a Delta Lake table.

        Args:
            table_path: Path to the Delta table.

        Returns:
            PyArrow Schema describing the table structure.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _get_schema() -> pa.Schema:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e
            return dt.schema().to_arrow()

        return await loop.run_in_executor(None, _get_schema)

    async def get_row_count(self, table_path: str) -> int:
        """Get the number of rows in a Delta Lake table.

        Uses Delta Lake metadata for efficiency when available.

        Args:
            table_path: Path to the Delta table.

        Returns:
            Total number of rows in the table.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _count_rows() -> int:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            # Use metadata if available, otherwise count from data
            # delta-rs doesn't expose row count in metadata directly,
            # so we read minimal data to count
            return int(dt.to_pyarrow_table().num_rows)

        return await loop.run_in_executor(None, _count_rows)

    async def table_exists(self, table_path: str) -> bool:
        """Check if a Delta Lake table exists at the given path.

        Args:
            table_path: Path to check for Delta table.

        Returns:
            True if a valid Delta table exists, False otherwise.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _check_exists() -> bool:
            delta_log = resolved_path / "_delta_log"
            if not delta_log.exists():
                return False
            # Verify it's a valid Delta table
            try:
                DeltaTable(str(resolved_path))
                return True
            except DeltaTableNotFoundError:
                return False

        return await loop.run_in_executor(None, _check_exists)

    async def aclose(self) -> None:
        """Gracefully close the reader (no-op, no persistent resources)."""
