"""Ports for export table discovery and file writing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = ["ExportCatalogPort", "ExportWriterPort"]

ExportFormatLiteral = Literal["csv", "xlsx", "tsv"]


@runtime_checkable
class ExportCatalogPort(Protocol):
    """Locate Delta tables for export workflows."""

    def list_tables(
        self,
        *,
        base_path: Path,
        layer: str,
    ) -> list[tuple[str, Path]]:
        """Return discovered `(table_name, table_path)` pairs for one layer."""
        ...

    def resolve_table_path(
        self,
        *,
        base_path: Path,
        table_name: str,
        layer: str,
    ) -> Path:
        """Resolve one table path or raise when it does not exist."""
        ...


@runtime_checkable
class ExportWriterPort(Protocol):
    """Persist exported tables to external file formats."""

    def write_export(
        self,
        *,
        table: pa.Table,
        table_name: str,
        layer: str,
        fmt: ExportFormatLiteral,
        output_dir: Path,
    ) -> Path:
        """Write one exported table and return the created file path."""
        ...
