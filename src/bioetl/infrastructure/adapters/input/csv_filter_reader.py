"""CSV Filter Reader adapter.

Implements InputFilterPort for reading filter IDs from CSV files.
Uses Polars for efficient CSV parsing.
"""

from pathlib import Path

import polars as pl


class CsvFilterReader:
    """Reads filter IDs from CSV files using Polars.

    This adapter implements the InputFilterPort protocol for loading
    unique IDs from CSV files to filter API requests.

    Example:
        >>> reader = CsvFilterReader()
        >>> ids = await reader.load_filter_ids("data/input/molecules.csv", "molecule_chembl_id")
        >>> print(ids)
        {'CHEMBL25', 'CHEMBL612545', 'CHEMBL1201198'}
    """

    async def load_filter_ids(
        self,
        source_path: str,
        column_name: str,
    ) -> list[str]:
        """Load unique IDs from a CSV file.

        Reads the specified column from the CSV file and returns a sorted list of
        unique, non-empty string values for deterministic processing.
        Handles common CSV issues:
        - Strips whitespace from values
        - Skips null/empty values
        - Removes duplicates
        - Sorts alphabetically for deterministic order

        Args:
            source_path: Path to the CSV file.
            column_name: Name of the column containing filter IDs.

        Returns:
            Sorted list of unique ID strings.

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

        # Extract unique, non-null, stripped IDs and sort for deterministic order
        ids = (
            df.select(pl.col(column_name).cast(pl.Utf8).str.strip_chars())
            .filter(pl.col(column_name).is_not_null())
            .filter(pl.col(column_name) != "")
            .unique()
            .sort(column_name)
            .to_series()
            .to_list()
        )

        return ids
