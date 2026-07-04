"""CSV Filter Reader adapter.

Implements InputFilterPort for reading filter IDs from CSV files.
Uses Polars for efficient CSV parsing with asyncio.to_thread for non-blocking I/O.
"""

from __future__ import annotations

__all__ = ["CsvFilterReader"]

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.filtering import FilterLoadResult
from bioetl.infrastructure.adapters.input.csv_filter_processor import CsvFilterProcessor

if TYPE_CHECKING:
    from bioetl.domain.filtering import FilterColumn
    from bioetl.domain.ports import LoggerPort


class CsvFilterReader:
    """Reads filter IDs from CSV files using Polars."""

    def __init__(
        self,
        logger: LoggerPort | None = None,
        processor: CsvFilterProcessor | None = None,
    ) -> None:
        """Initialize CSV filter reader.

        Args:
            logger: Optional LoggerPort for structured logging.
            processor: Optional CsvFilterProcessor for data processing.
        """
        self._logger = logger
        self._processor = processor or CsvFilterProcessor(logger=logger)

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
        all_ids = self._processor.extract_column_ids(df, column_name)
        unique_ids, unique_count, duplicate_count, duplicates = (
            self._processor.compute_duplicate_stats(all_ids)
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

    async def load_filter_with_fallback(
        self,
        source_path: str,
        primary_column: str,
        fallback_column: str,
    ) -> tuple[FilterLoadResult, dict[str, str]]:
        """Load filter IDs and fallback mapping from CSV.

        Loads primary filter IDs and builds a mapping from primary to fallback
        values for use when primary lookup fails (e.g., DOI → title fallback).

        Args:
            source_path: Path to the CSV file.
            primary_column: Name of the primary filter column (e.g., 'doi').
            fallback_column: Name of the fallback column (e.g., 'title').

        Returns:
            Tuple of (FilterLoadResult, fallback_mapping).
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
            all_ids = self._processor.extract_column_ids(df, primary_column)
        else:
            title_only_count = self._processor.build_fallback_rows(
                df,
                primary_column,
                fallback_column,
                all_ids,
                fallback_mapping,
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
            self._processor.compute_duplicate_stats([id_ for id_ in all_ids if id_])
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
        column_ids = self._processor.extract_column_ids_map(df, columns)

        column_names = [col.column_name for col in columns]
        filter_fields = tuple(col.filter_field for col in columns)
        valid_combinations = self._processor.build_valid_combinations(df, column_names)
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
