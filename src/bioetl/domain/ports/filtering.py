"""Filtering port for loading filter IDs from external sources.

This port abstracts the process of reading filter IDs from
various sources (CSV files, databases, etc.) for filtering API requests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.filter_config import FilterLoadResult


@runtime_checkable
class InputFilterPort(Protocol):
    """Port for loading filter IDs from external sources.

    This interface abstracts the process of reading filter IDs from
    various sources (CSV files, databases, etc.) for filtering API requests.
    """

    async def load_filter_ids(
        self,
        source_path: str,
        column_name: str,
    ) -> FilterLoadResult:
        """Load unique IDs from an external source.

        IDs are returned in sorted order for deterministic processing.
        Includes metadata about duplicates found in the source.

        Args:
            source_path: Path to the filter source (e.g., CSV file path).
            column_name: Name of the column containing filter IDs.

        Returns:
            FilterLoadResult with sorted unique IDs and duplicate statistics.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the column is not found in the source.
        """
        ...
