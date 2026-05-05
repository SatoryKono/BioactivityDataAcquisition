"""Protocol seam for CSV export collaborators used by storage writers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import pyarrow as pa


class CsvExporterPort(Protocol):
    """Minimal CSV exporter surface used by storage-layer helpers."""

    async def export(
        self,
        table_name: str,
        data: pa.Table,
        append: bool = True,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path: ...

    async def finalize_csv(
        self,
        table_name: str,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path | None: ...

    def clear(self, table_name: str | None = None) -> list[Path]: ...
