"""Data writer adapter component implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from bioetl.domain.clients.base.output.contracts import WriteResult


class FormatWriter(Protocol):
    """Protocol for format-specific writers (CSV, Parquet, JSON)."""

    def write(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Write DataFrame to path."""
        ...

    def has_format_support(self, fmt: str) -> bool:
        """Check if format is supported."""
        ...


class DataWriterAdapter:
    """Adapter for format-specific data writers.

    This component delegates to concrete writers (CSV, Parquet)
    without knowledge of QC reports, metadata, or checksums.
    It provides a unified interface for the facade.
    """

    def __init__(self, writer: FormatWriter) -> None:
        """Initialize adapter with concrete writer.

        Args:
            writer: Format-specific writer (CsvWriter, ParquetWriter).
        """
        self._writer = writer

    def write(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Write DataFrame to the specified path.

        Args:
            df: DataFrame to write.
            path: Target file path.
            column_order: Optional column ordering.

        Returns:
            WriteResult with path, row_count, duration.
        """
        return self._writer.write(df, path, column_order=column_order)

    def has_format_support(self, fmt: str) -> bool:
        """Check if this writer supports the given format.

        Args:
            fmt: Format name (e.g., 'csv', 'parquet').

        Returns:
            True if format is supported.
        """
        return self._writer.has_format_support(fmt)


__all__ = ["DataWriterAdapter", "FormatWriter"]
