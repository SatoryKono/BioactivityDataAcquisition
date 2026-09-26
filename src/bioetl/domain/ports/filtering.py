"""Filtering port for loading filter IDs from external sources.

This port abstracts the process of reading filter IDs from
various sources (CSV files, databases, etc.) for filtering API requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.filtering import FilterLoadResult

if TYPE_CHECKING:
    from bioetl.domain.filtering import FilterColumn


__all__ = [
    "InputFilterPort",
]


@runtime_checkable
class InputFilterPort(Protocol):
    """Port for loading filter IDs from external sources.

    This interface abstracts the process of reading filter IDs from
    various sources (CSV files, databases, etc.) for filtering API requests.

    Example:
        Basic usage with dependency injection::

            # In composition layer (bootstrap.py)
            filter_reader = CsvFilterReader(logger=logger)

            # In pipeline - load IDs for filtering ChEMBL activities
            result = await filter_reader.load_filter_ids(
                source_path="data/input/target_ids.csv",
                column_name="target_chembl_id",
            )

            # Use result.ids for API filtering
            for batch in batched(result.ids, batch_size=100):
                activities = await chembl.fetch_activities(target_ids=batch)

            # Log deduplication stats
            if result.has_duplicates:
                logger.warning(
                    "filter_had_duplicates",
                    total=result.total_count,
                    unique=result.unique_count,
                    duplicates=result.duplicate_count,
                )

    See Also:
        - :class:`FilterLoadResult` - Result container with deduplication metadata
        - :class:`CsvFilterReader` - CSV implementation in infrastructure layer
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
            source_path: Source location reference for the filter input.
            column_name: Name of the column containing filter IDs.

        Returns:
            FilterLoadResult with sorted unique IDs and duplicate statistics.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the column is not found in the source.

        Example:
            Load molecule IDs for filtering::

                result = await filter_reader.load_filter_ids(
                    source_path="data/input/molecules.csv",
                    column_name="molecule_chembl_id",
                )
                # result.unique_count -> 3
                # result.ids -> ('CHEMBL1', 'CHEMBL2', 'CHEMBL3', ...)
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
            source_path: Source location reference for the filter input.
            columns: List of FilterColumn objects defining columns to load.

        Returns:
            FilterLoadResult with:
            - column_ids: Per-field unique IDs for API __in filters
            - valid_combinations: Exact row-wise value combinations
            - filter_fields: Ordered field names for combinations

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If any column is not found in the source.

        Example:
            Filter by both target AND molecule (AND-logic)::

                from bioetl.domain.filtering import FilterColumn

                columns = [
                    FilterColumn(column_name="target_id", filter_field="target_chembl_id"),
                    FilterColumn(column_name="molecule_id", filter_field="molecule_chembl_id"),
                ]
                result = await filter_reader.load_multi_column_filter(
                    source_path="data/input/target_molecule_pairs.csv",
                    columns=columns,
                )

                # Server-side: Use column_ids for API __in filters
                # result.column_ids["target_chembl_id"] -> ('CHEMBL1', 'CHEMBL2')
                # result.column_ids["molecule_chembl_id"] -> ('CHEMBL100', 'CHEMBL200')

                # Client-side: Validate exact combinations after fetch
                # result.valid_combinations -> frozenset({('CHEMBL1', 'CHEMBL100'), ...})
                for record in fetched_records:
                    combo = (record["target_id"], record["molecule_id"])
                    if combo in result.valid_combinations:
                        yield record  # Exact match found
        """
        ...

    async def load_filter_with_fallback(
        self,
        source_path: str,
        primary_column: str,
        fallback_column: str,
    ) -> tuple[FilterLoadResult, dict[str, str]]:
        """Load filter IDs and fallback mapping from source.

        Loads primary filter IDs and builds a mapping from primary to fallback
        values for use when primary lookup fails (e.g., DOI -> title fallback).

        Args:
            source_path: Source location reference for the filter input.
            primary_column: Name of the primary filter column (e.g., 'doi').
            fallback_column: Name of the fallback column (e.g., 'title').

        Returns:
            Tuple of (FilterLoadResult, fallback_mapping).
            fallback_mapping maps primary values to fallback values.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If columns are not found in the source.

        Example:
            Load publications with DOI → title fallback for PubMed search::

                result, fallback_map = await filter_reader.load_filter_with_fallback(
                    source_path="data/input/publications.csv",
                    primary_column="doi",
                    fallback_column="title",
                )
                # result.ids -> ('10.1234/abc', '10.5678/def', ...)
                # fallback_map -> {'10.1234/abc': 'Some Paper Title', ...}

                # Use in pipeline with fallback search
                for doi in result.ids:
                    record = await pubmed.fetch_by_doi(doi)
                    if record is None and doi in fallback_map:
                        # DOI lookup failed, try title search
                        record = await pubmed.search_by_title(fallback_map[doi])
        """
        ...
