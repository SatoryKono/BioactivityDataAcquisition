"""CSV Filter Reader adapter.

Implements InputFilterPort for reading filter IDs from CSV files.
Uses Polars for efficient CSV parsing with asyncio.to_thread for non-blocking I/O.
"""

from __future__ import annotations

__all__ = ["CsvFilterReader"]

import asyncio
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.filtering import FilterColumn, FilterLoadResult
from bioetl.domain.transformations import safe_str

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
        """Read CSV file and return DataFrame.

        Returns:
            Polars DataFrame loaded from the given CSV file path.
        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV filter file not found: {source_path}")

        try:
            return pl.read_csv(source_path)
        except (pl.exceptions.PolarsError, OSError, ValueError, TypeError) as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e

    def _extract_column_ids(self, df: pl.DataFrame, column_name: str) -> list[str]:
        """Extract and clean IDs from specified column.

        Returns:
            List of non-empty stripped string values from the specified column.
        """
        if column_name not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column_name}' not found in CSV. Available columns: {available}"
            )

        # Extract values and convert to string safely (handling float IDs)
        raw_values = df.select(pl.col(column_name)).to_series().to_list()
        result = [
            s
            for v in raw_values
            if (s_val := safe_str(v, "")) is not None and (s := s_val.strip()) != ""
        ]
        return result

    def _compute_duplicate_stats(
        self, all_ids: list[str]
    ) -> tuple[tuple[str, ...], int, int, frozenset[str]]:
        """Compute unique IDs and duplicate statistics.

        Returns:
            Tuple of (unique IDs sorted tuple, unique count, duplicate count, frozenset of duplicated values).
        """
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
        """Extract unique IDs per column for server-side filtering.

        Returns:
            Dictionary mapping each filter_field name to its sorted tuple of unique IDs.
        """
        return {
            col.filter_field: tuple(
                sorted(set(self._extract_column_ids(df, col.column_name)))
            )
            for col in columns
        }

    def _build_valid_combinations(
        self, df: pl.DataFrame, column_names: list[str]
    ) -> set[tuple[str, ...]]:
        """Build valid row-wise combinations for client-side filtering.

        Returns:
            Set of row-wise value tuples with all columns non-empty.
        """
        combinations: set[tuple[str, ...]] = set()
        for row in df.select(column_names).iter_rows():
            combo = tuple(
                s_val.strip() if (s_val := safe_str(val, "")) is not None else ""
                for val in row
            )
            if all(combo):  # Skip rows with empty values
                combinations.add(combo)
        return combinations

    async def load_filter_ids(
        self, source_path: str, column_name: str
    ) -> FilterLoadResult:
        """Load unique IDs from a CSV file.

        Args:
            source_path: File path for source.
            column_name: Name of the column.

        Returns:
            Loaded FilterLoadResult.
        """
        df = await asyncio.to_thread(self._read_csv_dataframe, source_path)
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

    @staticmethod
    def _build_fallback_rows(
        df: pl.DataFrame,
        primary_column: str,
        fallback_column: str,
        all_ids: list[str],
        fallback_mapping: dict[str, str],
    ) -> int:
        """Process rows building ID list and fallback mapping. Returns title_only_count."""
        title_only_count = 0
        for row in df.iter_rows(named=True):
            primary_str = str(row.get(primary_column, "")).strip() if row.get(primary_column) else ""
            fallback_str = str(row.get(fallback_column, "")).strip() if row.get(fallback_column) else ""

            if primary_str:
                all_ids.append(primary_str)
                if fallback_str:
                    fallback_mapping[primary_str] = fallback_str
            elif fallback_str:
                marker = f"__title_only_{title_only_count}__"
                all_ids.append(marker)
                fallback_mapping[marker] = fallback_str
                title_only_count += 1
        return title_only_count

    async def load_filter_with_fallback(
        self,
        source_path: str,
        primary_column: str,
        fallback_column: str,
    ) -> tuple[FilterLoadResult, dict[str, str]]:
        """Load filter IDs and fallback mapping from CSV.

        Loads primary filter IDs and builds a mapping from primary to fallback
        values for use when primary lookup fails (e.g., DOI → title fallback).

        Handles three cases:
        1. Records with DOI and title → DOI in filter_ids, DOI→title in mapping
        2. Records with DOI only → DOI in filter_ids, no fallback
        3. Records with title only → empty string in filter_ids, ""→title in mapping

        Args:
            source_path: Path to the CSV file.
            primary_column: Name of the primary filter column (e.g., 'doi').
            fallback_column: Name of the fallback column (e.g., 'title').

        Returns:
            Tuple of (FilterLoadResult, fallback_mapping).
            fallback_mapping maps primary values to fallback values.
            Empty string key "" maps to titles for records without primary ID.
        """
        df = await asyncio.to_thread(self._read_csv_dataframe, source_path)

        # Build fallback mapping and collect IDs (including empty placeholders)
        fallback_mapping: dict[str, str] = {}
        all_ids: list[str] = []
        title_only_count = 0

        if fallback_column not in df.columns:
            if self._logger:
                self._logger.warning(
                    "fallback_column_not_found",
                    source_path=source_path,
                    fallback_column=fallback_column,
                    available_columns=df.columns,
                )
            all_ids = self._extract_column_ids(df, primary_column)
        else:
            title_only_count = self._build_fallback_rows(
                df, primary_column, fallback_column, all_ids, fallback_mapping,
            )
            if self._logger:
                self._logger.info(
                    "fallback_mapping_loaded",
                    source_path=source_path,
                    primary_column=primary_column,
                    fallback_column=fallback_column,
                    mapping_count=len(fallback_mapping),
                    title_only_count=title_only_count,
                )

        # Compute stats (markers __title_only_N__ are included as they are non-empty)
        unique_ids, unique_count, duplicate_count, duplicates = (
            self._compute_duplicate_stats([id_ for id_ in all_ids if id_])
        )

        result = FilterLoadResult(
            ids=unique_ids,
            total_count=len(all_ids),
            unique_count=unique_count,
            duplicate_count=duplicate_count,
            duplicates=duplicates,
        )

        return result, fallback_mapping

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
        df = await asyncio.to_thread(self._read_csv_dataframe, source_path)
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
