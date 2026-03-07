"""Data models and types for table export service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bioetl.domain.types import JsonDict

ExportFormat = Literal["csv", "xlsx", "tsv"]


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    """Information about a table column."""

    name: str
    type: str
    nullable: bool


@dataclass(frozen=True, slots=True)
class TablePreview:
    """Preview of a Delta table for display."""

    table_name: str
    layer: str
    row_count: int
    columns: tuple[ColumnInfo, ...]
    sample_rows: tuple[
        JsonDict, ...  # Any: port contract allows heterogeneous record values
    ]  # Any: port contract allows heterogeneous record values


@dataclass(frozen=True, slots=True)
class TableInfo:
    """Information about a discovered table."""

    name: str
    layer: str
    path: Path


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Options for export operation."""

    format: ExportFormat = "csv"
    output_path: Path | None = None
    limit: int | None = None
    columns: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Result of an export operation."""

    table_name: str
    layer: str
    format: ExportFormat
    output_path: Path | None
    row_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check whether export succeeded."""
        return self.error is None


__all__ = [
    "ColumnInfo",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "TableInfo",
    "TablePreview",
]
