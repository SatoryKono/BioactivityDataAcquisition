"""Subcellular Fraction Data Source wrapper.

Wraps a DataSourcePort to extract unique subcellular fractions from ChEMBL Assay records.
This is a derived entity pattern - subcellular_fraction entities are extracted
from the assay_subcellular_fraction field in assay records.

Architecture:
    ChEMBL API (assay endpoint)
           ↓
    SubcellularFractionDataSource (wrapper)
      - fetch("subcellular_fraction") → wrapped.fetch("assay")
      - extracts unique subcellular_fraction values
      - aggregates assay count per fraction
           ↓
    Pipeline receives subcellular_fraction records

Note: ChEMBL does NOT have a dedicated /subcellular_fraction endpoint.
This wrapper extracts and deduplicates values from /assay responses.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class SubcellularFractionDataSource:
    """Wraps a DataSourcePort to extract unique subcellular fractions from assay records.

    This is a Decorator pattern implementation that transforms the assay
    entity into derived subcellular_fraction entities. For each batch of assays
    fetched from the wrapped adapter, unique subcellular fractions are extracted
    and deduplicated.

    The wrapper:
    1. Intercepts fetch("subcellular_fraction") calls
    2. Fetches assays from the wrapped adapter via fetch("assay")
    3. Extracts unique subcellular_fraction values (M:1 relationship)
    4. Yields individual fraction records with computed entity_id
    5. Delegates all other operations to the wrapped adapter

    Example:
        >>> wrapped = SubcellularFractionDataSource(chembl_adapter)
        >>> async with wrapped:
        ...     async for fraction in wrapped.fetch("subcellular_fraction", limit=100):
        ...         process_fraction(fraction)

    """

    # Source entity type to fetch from wrapped adapter
    SOURCE_ENTITY_TYPE = "assay"
    # Target entity type this wrapper provides
    TARGET_ENTITY_TYPE = "subcellular_fraction"
    # Multiplier for assay limit estimation.
    # Not all assays have subcellular_fraction (many are cell-based or whole organism).
    # Analysis shows ~10-15% of ChEMBL assays have this field populated.
    # Using 100x multiplier ensures we fetch enough assays to get good coverage.
    ASSAY_LIMIT_MULTIPLIER = 100

    def __init__(
        self,
        data_source: DataSourcePort,
    ) -> None:
        """Initialize subcellular fraction data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap (ChemblAdapter).

        """
        self._data_source = data_source
        # Cache seen fractions for deduplication within a fetch session
        self._seen_fractions: set[str] = set()

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self._data_source.__aenter__()
        # Reset deduplication cache on new context
        self._seen_fractions = set()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records, extracting subcellular fractions if entity_type matches.

        For subcellular_fraction entity type:
        - Fetches assays from wrapped adapter
        - Extracts unique subcellular_fraction values
        - Yields individual fraction records (deduplicated)

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records (for subcellular_fraction, limits unique fractions).
            query: Optional search query.
            filter_ids: Optional filter IDs (passed to wrapped adapter).
            filter_field: Optional filter field (passed to wrapped adapter).

        Yields:
            Records from the data source.

        """
        if entity_type == self.TARGET_ENTITY_TYPE:
            # Reset deduplication cache for new fetch
            self._seen_fractions = set()
            async for fraction in self._fetch_subcellular_fractions(
                limit, filter_ids, filter_field
            ):
                yield fraction
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in self._data_source.fetch(
                entity_type=entity_type,
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
            ):
                yield record

    async def _fetch_subcellular_fractions(
        self,
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays and extract unique subcellular fractions.

        Args:
            limit: Maximum number of unique fraction records to yield.
            filter_ids: Optional assay IDs to filter by.
            filter_field: Optional field for filtering (typically assay_chembl_id).

        Yields:
            Subcellular fraction records extracted from assays.

        """
        fraction_count = 0
        # Track counts per fraction for statistics
        fraction_stats: dict[str, dict[str, Any]] = {}

        # Estimate assay limit based on fraction limit.
        # We need to fetch more assays than unique fractions because:
        # 1. Not all assays have subcellular_fraction populated
        # 2. Many assays share the same subcellular_fraction value
        assay_limit = limit * self.ASSAY_LIMIT_MULTIPLIER if limit else None

        async for assay in self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=assay_limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            fraction_record = self._extract_fraction_from_assay(assay)
            if fraction_record is None:
                continue

            fraction_key = fraction_record["subcellular_fraction"].lower().strip()

            # Track statistics (always update count even if already seen)
            if fraction_key not in fraction_stats:
                fraction_stats[fraction_key] = {
                    "record": fraction_record,
                    "count": 0,
                }
            fraction_stats[fraction_key]["count"] += 1

            # Deduplicate: only yield new fractions
            if fraction_key in self._seen_fractions:
                continue

            self._seen_fractions.add(fraction_key)

            # Update count in record before yielding
            fraction_record["assay_count"] = fraction_stats[fraction_key]["count"]

            yield fraction_record
            fraction_count += 1

            if limit and fraction_count >= limit:
                return

    def _extract_fraction_from_assay(
        self,
        assay: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Extract subcellular fraction from an assay record.

        Args:
            assay: Raw assay record from ChEMBL API.

        Returns:
            Subcellular fraction dictionary if present, None otherwise.

        """
        raw_fraction = assay.get("assay_subcellular_fraction")
        if not raw_fraction:
            return None

        fraction = str(raw_fraction).strip()
        if not fraction:
            return None

        assay_chembl_id = assay.get("assay_chembl_id")

        # Compute entity_id from normalized fraction name
        entity_id = self._compute_entity_id(fraction)

        return {
            "entity_id": entity_id,
            "subcellular_fraction": fraction,
            "example_assay_chembl_id": str(assay_chembl_id) if assay_chembl_id else None,
            "assay_count": 1,  # Will be updated with actual count
        }

    def _compute_entity_id(
        self,
        subcellular_fraction: str,
    ) -> str:
        """Compute entity ID for a subcellular fraction.

        Entity ID is SHA256 hash of: subcellular_fraction:normalized_name

        Args:
            subcellular_fraction: Subcellular fraction name (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        normalized = subcellular_fraction.lower().strip()
        composite = f"subcellular_fraction:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()

    # FilterableDataSourcePort implementation (delegates to wrapped adapter)

    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort:
        """Check that wrapped adapter implements FilterableDataSourcePort.

        Args:
            method_name: Name of the method being called (for error message).

        Returns:
            Wrapped adapter cast to FilterableDataSourcePort.

        Raises:
            TypeError: If wrapped adapter doesn't implement FilterableDataSourcePort.

        """
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Wrapped adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {method_name}() requires a filterable adapter."
            )
        return self._data_source

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered records.

        Implements FilterableDataSourcePort.fetch_filtered().

        For subcellular_fraction entity type:
        - Delegates to wrapped adapter's fetch_filtered("assay", ...)
        - Extracts unique subcellular fractions

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of IDs to filter by.
            filter_field: Field name to filter on.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.

        """
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Reset deduplication cache
            self._seen_fractions = set()
            async for fraction in self._fetch_filtered_subcellular_fractions(
                filterable, filter_ids, filter_field, limit
            ):
                yield fraction
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record

    async def _fetch_filtered_subcellular_fractions(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered assays and extract unique subcellular fractions.

        Args:
            filterable: Wrapped adapter that implements FilterableDataSourcePort.
            filter_ids: Assay ChEMBL IDs to filter by.
            filter_field: Field name (typically assay_chembl_id).
            limit: Maximum number of fraction records to yield.

        Yields:
            Subcellular fraction records extracted from filtered assays.

        """
        fraction_count = 0
        assay_limit = limit * self.ASSAY_LIMIT_MULTIPLIER if limit else None

        async for assay in filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=assay_limit,
        ):
            fraction_record = self._extract_fraction_from_assay(assay)
            if fraction_record is None:
                continue

            fraction_key = fraction_record["subcellular_fraction"].lower().strip()
            if fraction_key in self._seen_fractions:
                continue

            self._seen_fractions.add(fraction_key)
            yield fraction_record
            fraction_count += 1

            if limit and fraction_count >= limit:
                return

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by multiple fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Args:
            entity_type: Type of entity to fetch.
            filters: Mapping from filter_field to list of IDs.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching ALL filter criteria.

        """
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            fraction_count = 0
            assay_limit = limit * self.ASSAY_LIMIT_MULTIPLIER if limit else None

            async for assay in filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=assay_limit,
            ):
                fraction_record = self._extract_fraction_from_assay(assay)
                if fraction_record is None:
                    continue

                fraction_key = fraction_record["subcellular_fraction"].lower().strip()
                if fraction_key in self._seen_fractions:
                    continue

                self._seen_fractions.add(fraction_key)
                yield fraction_record
                fraction_count += 1

                if limit and fraction_count >= limit:
                    return
        else:
            async for record in filterable.fetch_multi_filtered(
                entity_type=entity_type,
                filters=filters,
                limit=limit,
            ):
                yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with fallback search when primary lookup fails.

        Implements FilterableDataSourcePort.fetch_filtered_with_fallback().

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of primary IDs to filter by.
            filter_field: Field name for primary filtering.
            fallback_mapping: Mapping from primary ID to fallback value.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records found via primary lookup or fallback search.

        """
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            fraction_count = 0
            assay_limit = limit * self.ASSAY_LIMIT_MULTIPLIER if limit else None

            async for assay in filterable.fetch_filtered_with_fallback(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=assay_limit,
            ):
                fraction_record = self._extract_fraction_from_assay(assay)
                if fraction_record is None:
                    continue

                fraction_key = fraction_record["subcellular_fraction"].lower().strip()
                if fraction_key in self._seen_fractions:
                    continue

                self._seen_fractions.add(fraction_key)
                yield fraction_record
                fraction_count += 1

                if limit and fraction_count >= limit:
                    return
        else:
            async for record in filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record

    def get_source_metadata(self, api_version: str | None = None) -> Any:
        """Delegate get_source_metadata to wrapped data source.

        Returns API request metadata collected by the underlying adapter.
        Used by BatchExecutor to enrich Bronze layer metadata.

        Args:
            api_version: Optional API version string.

        Returns:
            SourceMetadata with request details, or None if not supported.
        """
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None


__all__ = ["SubcellularFractionDataSource"]
