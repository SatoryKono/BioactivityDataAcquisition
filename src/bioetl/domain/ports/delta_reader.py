"""Delta Lake reader port for table access and export.

Provides read-only access to Silver/Gold Delta Lake tables
for export utilities and data inspection.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = [
    "DeltaReaderPort",
]


@runtime_checkable
class DeltaReaderPort(Protocol):
    """Port for reading Delta Lake tables.

    This interface abstracts Delta Lake read operations, allowing
    export utilities to access Silver/Gold layer data without
    knowing the underlying storage implementation.

    Note:
        This port is read-only. Write operations use narrow storage ports.
    """

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> object:
        """Read data from a Delta Lake table.

        Args:
            table_path: Concrete table storage reference.
            columns: Optional list of columns to read (projection pushdown).
                    If None, reads all columns.
            limit: Optional maximum number of rows to read.
                  If None, reads all rows.

        Returns:
            Opaque table payload with the requested data.

        Raises:
            An adapter-defined read error when the table reference is invalid or
            unreadable.
        """
        ...

    async def get_schema(self, table_path: str) -> object:
        """Get the schema of a Delta Lake table.

        Args:
            table_path: Concrete table storage reference.

        Returns:
            Opaque schema payload describing the table structure.

        Raises:
            An adapter-defined read error when the table reference is invalid or
            unreadable.
        """
        ...

    async def get_row_count(self, table_path: str) -> int:
        """Get the number of rows in a Delta Lake table.

        Uses Delta Lake metadata when possible for efficiency.

        Args:
            table_path: Concrete table storage reference.

        Returns:
            Total number of rows in the table.

        Raises:
            An adapter-defined read error when the table reference is invalid or
            unreadable.
        """
        ...

    async def table_exists(self, table_path: str) -> bool:
        """Check if a Delta Lake table exists at the given path.

        Args:
            table_path: Concrete table storage reference to probe.

        Returns:
            True if a valid Delta table exists, False otherwise.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the reader and release resources."""
        ...
