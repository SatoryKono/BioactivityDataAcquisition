"""CSV Filter Reader adapter.

Implements InputFilterPort for reading filter IDs from CSV files.
Uses Polars for efficient CSV parsing.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.filtering import FilterColumn, FilterLoadResult

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class CsvFilterReader:
    """Reads filter IDs from CSV files using Polars."""

    def __init__(self, logger: LoggerPort | None = None) -> None:
        """Initialize CSV filter reader.

        Args:
            logger: Optional LoggerPort for structured logging.
        """
        self._logger = logger

    def _read_csv_dataframe(self, source_path: str) -> pl.DataFrame:
        """Read CSV file and return DataFrame."""
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV filter file not found: {source_path}")

        try:
            return pl.read_csv(source_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e

    def _extract_column_ids(self, df: pl.DataFrame, column_name: str) -> list[str]:
        """Extract and clean IDs from specified column."""
        if column_name not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column_name}' not found in CSV. Available columns: {available}"
            )

        result: list[str] = (
            df.select(pl.col(column_name).cast(pl.Utf8).str.strip_chars())
            .filter(pl.col(column_name).is_not_null())
            .filter(pl.col(column_name) != "")
            .to_series()
            .to_list()
        )
        return result

    def _compute_duplicate_stats(
        self, all_ids: list[str]
    ) -> tuple[tuple[str, ...], int, int, frozenset[str]]:
        """Compute unique IDs and duplicate statistics."""
        total_count = len(all_ids)
        id_counts = Counter(all_ids)
        duplicates = frozenset(
            id_val for id_val, count in id_counts.items() if count > 1
        )
        unique_ids = tuple(sorted(set(all_ids)))
        unique_count = len(unique_ids)
        duplicate_count = total_count - unique_count
        return unique_ids, unique_count, duplicate_count, duplicates

    def _extract_column_ids_map(
        self, df: pl.DataFrame, columns: list[FilterColumn]
    ) -> dict[str, tuple[str, ...]]:
        """Extract unique IDs per column for server-side filtering."""
        return {
            col.filter_field: tuple(
                sorted(set(self._extract_column_ids(df, col.column_name)))
            )
            for col in columns
        }

    def _build_valid_combinations(
        self, df: pl.DataFrame, column_names: list[str]
    ) -> set[tuple[str, ...]]:
        """Build valid row-wise combinations for client-side filtering."""
        combinations: set[tuple[str, ...]] = set()
        for row in df.select(column_names).iter_rows():
            combo = tuple(str(val).strip() if val is not None else "" for val in row)
            if all(combo):  # Skip rows with empty values
                combinations.add(combo)
        return combinations

    async def load_filter_ids(
        self, source_path: str, column_name: str
    ) -> FilterLoadResult:
        """Load unique IDs from a CSV file."""
        df = self._read_csv_dataframe(source_path)
        all_ids = self._extract_column_ids(df, column_name)
        unique_ids, unique_count, duplicate_count, duplicates = (
            self._compute_duplicate_stats(all_ids)
        )

        if duplicate_count > 0 and self._logger:
            self._logger.warning(
                "filter_ids_duplicates_found",
                source_path=source_path,
                column_name=column_name,
                total_count=len(all_ids),
                unique_count=unique_count,
                duplicate_count=duplicate_count,
                sample_duplicates=list(duplicates)[:10],
            )

        return FilterLoadResult(
            ids=unique_ids,
            total_count=len(all_ids),
            unique_count=unique_count,
            duplicate_count=duplicate_count,
            duplicates=duplicates,
        )

    def _log_multi_column_filter(
        self,
        source_path: str,
        columns: list[FilterColumn],
        filter_fields: tuple[str, ...],
        total_count: int,
        valid_combinations: set[tuple[str, ...]],
        column_ids: dict[str, tuple[str, ...]],
    ) -> None:
        """Log multi-column filter load statistics."""
        if not self._logger:
            return
        self._logger.info(
            "multi_column_filter_loaded",
            source_path=source_path,
            columns=[col.column_name for col in columns],
            filter_fields=list(filter_fields),
            total_rows=total_count,
            valid_combinations=len(valid_combinations),
            unique_ids_per_field={field: len(ids) for field, ids in column_ids.items()},
        )

    async def load_multi_column_filter(
        self,
        source_path: str,
        columns: list[FilterColumn],
    ) -> FilterLoadResult:
        """Load filter data from multiple columns.

        Returns unique IDs per column for server-side filtering, plus
        exact row-wise combinations for client-side filtering.

        Args:
            source_path: Path to the CSV file.
            columns: List of FilterColumn objects defining columns to load.

        Returns:
            FilterLoadResult with column_ids and valid_combinations.
        """
        df = self._read_csv_dataframe(source_path)
        column_ids = self._extract_column_ids_map(df, columns)

        column_names = [col.column_name for col in columns]
        filter_fields = tuple(col.filter_field for col in columns)
        valid_combinations = self._build_valid_combinations(df, column_names)
        total_count = len(df)

        self._log_multi_column_filter(
            source_path,
            columns,
            filter_fields,
            total_count,
            valid_combinations,
            column_ids,
        )

        return FilterLoadResult(
            total_count=total_count,
            column_ids=column_ids,
            valid_combinations=frozenset(valid_combinations),
            filter_fields=filter_fields,
        )
