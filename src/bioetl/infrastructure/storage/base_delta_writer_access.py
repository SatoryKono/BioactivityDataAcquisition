"""Table access mixin for ``BaseDeltaWriter``."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pyarrow as pa
    from deltalake import DeltaTable

    from bioetl.domain.types import BronzeRecord


class BaseDeltaWriterTableAccessMixin:
    """Delta table read/schema/cleanup helpers for ``BaseDeltaWriter``."""

    async def _open_delta_table(self, table_name: str) -> DeltaTable | None:
        """Open one Delta table by name and return None when it is missing."""
        from bioetl.infrastructure.storage import base_delta_writer as _base

        def _open() -> DeltaTable | None:
            table_path = self._resolve_table_path(table_name)
            try:
                return _base._load_delta_table(table_path)
            except _base.DeltaTableNotFoundError:
                return None

        return await asyncio.to_thread(_open)

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get the existing table schema when the Delta table exists."""
        from bioetl.infrastructure.storage import base_delta_writer as _base

        dt = await self._open_delta_table(table_name)
        if dt is None:
            return None
        return _base._get_delta_table_arrow_schema(dt)

    def get_table_path(self, table_name: str):
        """Return the filesystem path for a Delta table."""
        from pathlib import Path

        return Path(self._resolve_table_path(table_name))

    async def read_table(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Read records from a Delta table."""
        from bioetl.infrastructure.storage import base_delta_writer as _base

        dt = await self._open_delta_table(table_name)
        if dt is None:
            raise FileNotFoundError(f"Table not found: {table_name}")

        return _base._read_delta_records(dt, columns)

    def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
        """Clear one Delta table or every Delta table under ``base_path``."""
        from pathlib import Path

        from bioetl.infrastructure.storage import base_delta_writer as _base

        base = Path(self.base_path)
        return _base._clear_delta_tables(
            base_path=base,
            table_path=self.get_table_path(table_name) if table_name else None,
            dry_run=dry_run,
        )
