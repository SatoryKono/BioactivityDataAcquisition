"""CSV Filter Reader adapter.

Implements InputFilterPort for reading filter IDs from CSV files.
Uses Polars for efficient CSV parsing.
"""

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.filter_config import FilterLoadResult

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class CsvFilterReader:
    """Reads filter IDs from CSV files using Polars.

    This adapter implements the InputFilterPort protocol for loading
    unique IDs from CSV files to filter API requests.

    Example:
        >>> reader = CsvFilterReader(logger)
        >>> result = await reader.load_filter_ids("data/input/molecules.csv", "molecule_chembl_id")
        >>> print(result.ids)
        ('CHEMBL1201198', 'CHEMBL25', 'CHEMBL612545')
        >>> print(result.duplicate_count)
        0

    """

    def __init__(self, logger: "LoggerPort") -> None:
        """Initialize filter reader with logger.

        Args:
            logger: Structured logger instance.
        """
        self._logger = logger

    async def load_filter_ids(
        self,
        source_path: str,
        column_name: str,
    ) -> FilterLoadResult:
        """Load unique IDs from a CSV file.

        Reads the specified column from the CSV file and returns a FilterLoadResult
        with unique, sorted IDs and duplicate statistics.

        Handles common CSV issues:
        - Strips whitespace from values
        - Skips null/empty values
        - Removes duplicates (with statistics)
        - Sorts alphabetically for deterministic order

        Args:
            source_path: Path to the CSV file.
            column_name: Name of the column containing filter IDs.

        Returns:
            FilterLoadResult with sorted unique IDs and duplicate statistics.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            ValueError: If the specified column is not found in the CSV.

        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV filter file not found: {source_path}")

        # Read CSV with Polars (efficient for large files)
        try:
            df = pl.read_csv(source_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e

        # Validate column exists
        if column_name not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column_name}' not found in CSV. Available columns: {available}"
            )

        # Extract all non-null, stripped IDs (before deduplication)
        all_ids = (
            df.select(pl.col(column_name).cast(pl.Utf8).str.strip_chars())
            .filter(pl.col(column_name).is_not_null())
            .filter(pl.col(column_name) != "")
            .to_series()
            .to_list()
        )

        total_count = len(all_ids)

        # Find duplicates
        id_counts = Counter(all_ids)
        duplicates = frozenset(id_val for id_val, count in id_counts.items() if count > 1)

        # Get unique sorted IDs
        unique_ids = tuple(sorted(set(all_ids)))
        unique_count = len(unique_ids)
        duplicate_count = total_count - unique_count

        # Log duplicates if found
        if duplicate_count > 0:
            sample_duplicates = list(duplicates)[:10]
            self._logger.warning(
                "filter_ids_duplicates_found",
                source_path=source_path,
                column_name=column_name,
                total_count=total_count,
                unique_count=unique_count,
                duplicate_count=duplicate_count,
                sample_duplicates=sample_duplicates,
            )

        return FilterLoadResult(
            ids=unique_ids,
            total_count=total_count,
            unique_count=unique_count,
            duplicate_count=duplicate_count,
            duplicates=duplicates,
        )
