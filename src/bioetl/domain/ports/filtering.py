"""Filtering port for loading filter IDs from external sources.

This port abstracts the process of reading filter IDs from
various sources (CSV files, databases, etc.) for filtering API requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.filtering import FilterLoadResult

if TYPE_CHECKING:
    from bioetl.domain.filtering import FilterColumn


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

    async def load_multi_column_filter(
        self,
        source_path: str,
        columns: list[FilterColumn],
    ) -> FilterLoadResult:
        """Load filter data from multiple columns.

        Returns unique IDs per column for server-side filtering, plus
        exact row-wise combinations for client-side filtering.

        Args:
            source_path: Path to the filter source (e.g., CSV file path).
            columns: List of FilterColumn objects defining columns to load.

        Returns:
            FilterLoadResult with:
            - column_ids: Per-field unique IDs for API __in filters
            - valid_combinations: Exact row-wise value combinations
            - filter_fields: Ordered field names for combinations

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If any column is not found in the source.
        """
        ...


@runtime_checkable
class FallbackInputFilterPort(InputFilterPort, Protocol):
    """Extended InputFilterPort with fallback column support.

    This Protocol extends InputFilterPort for filter readers that support
    loading a primary column with a fallback column mapping (e.g., DOI with
    title fallback for CrossRef).

    Use isinstance() check to detect if a reader supports fallback:
        if isinstance(reader, FallbackInputFilterPort):
            result, mapping = await reader.load_filter_with_fallback(...)
    """

    async def load_filter_with_fallback(
        self,
        source_path: str,
        primary_column: str,
        fallback_column: str,
    ) -> tuple[FilterLoadResult, dict[str, str]]:
        """Load filter IDs with fallback column mapping.

        Args:
            source_path: Path to the filter source.
            primary_column: Name of the primary filter column.
            fallback_column: Name of the fallback column for mapping.

        Returns:
            Tuple of (FilterLoadResult, fallback_mapping dict).
            The fallback_mapping maps primary IDs to fallback values.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If any column is not found in the source.
        """
        ...
