"""Data source ports for fetching records from external systems.

Defines DataSourcePort for basic fetching and FilterableDataSourcePort
for adapters that support server-side filtering.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from bioetl.domain.types import HealthStatus, JsonDict

__all__ = [
    "DataSourceFactoryPort",
    "DataSourcePort",
    "FilterableDataSourcePort",
]


@runtime_checkable
class DataSourcePort(Protocol):
    """Port for data sources (e.g., ChEMBL, PubChem).

    This interface abstracts the process of fetching data from an external
    source, allowing the application to be independent of the specific
    implementation of the data source client.
    """

    @property
    def provider_name(self) -> str:
        """The unique name of the data provider (e.g., 'chembl')."""
        ...

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager."""
        ...

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: port contract allows heterogeneous record values
    ]:  # Any: port contract allows heterogeneous record values
        """Fetch records from the data source (async generator).

        Note: This is NOT an async def because async generator functions
        return AsyncIterator directly without needing to be awaited.
        Implementations should be async generators (async def with yield).

        Args:
            entity_type: The type of entity to fetch (e.g., 'activity', 'molecule').
            limit: The maximum number of records to fetch.
            query: Optional search query for providers that support it (e.g., PubChem, UniProt).
            filter_ids: Optional set of IDs to filter by (for adapters that support filtering).
            filter_field: Optional field name to filter on (for adapters that support filtering).
            offset: Optional starting offset for checkpoint-based resume.
                Adapters with offset pagination (e.g., ChEMBL) start fetching from
                this position. Others may ignore this parameter.

        Yields:
            A dictionary representing a single record from the data source.

        Returns:
            Async iterator yielding fetched records.
        """
        ...

    async def health_check(self) -> HealthStatus:
        """Check the health of the data source.

        Returns:
            A HealthStatus object indicating the current status of the source.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the data source and release resources."""
        ...


@runtime_checkable
class FilterableDataSourcePort(DataSourcePort, Protocol):
    """Extended DataSourcePort that supports filtering at API level.

    This Protocol extends DataSourcePort for adapters that can perform
    server-side filtering by IDs (e.g., ChEMBL, PubMed).

    Use isinstance() check to detect if an adapter supports filtering:
        if isinstance(adapter, FilterableDataSourcePort):
            async for record in adapter.fetch_filtered(...):
                ...

    Note:
        Adapters that implement this Protocol MUST also implement DataSourcePort.
        The fetch_filtered() method should delegate to the provider's native
        filtering capabilities for efficient server-side filtering.
    """

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: port contract allows heterogeneous record values
    ]:  # Any: port contract allows heterogeneous record values
        """Fetch records filtered by specific IDs at the source level.

        This method enables efficient server-side filtering by passing
        filter criteria directly to the data source API.

        Args:
            entity_type: The type of entity to fetch (e.g., 'activity', 'publication').
            filter_ids: Sorted list of IDs to filter by (for deterministic batching).
            filter_field: Field name to filter on (e.g., 'molecule_chembl_id', 'pmid').
            limit: Optional maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.

        Returns:
            Async iterator yielding fetched records.
        """
        ...

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: port contract allows heterogeneous record values
    ]:  # Any: port contract allows heterogeneous record values
        """Fetch records filtered by multiple fields (AND logic).

        This method enables multi-field server-side filtering by passing
        multiple filter criteria directly to the data source API.
        The API will return records matching ALL filter conditions.

        Args:
            entity_type: The type of entity to fetch.
            filters: Mapping from filter_field to list of IDs.
                Example: {"molecule_chembl_id": ["CHEMBL25"], "document_chembl_id": ["CHEMBL1123"]}
            limit: Optional maximum number of records to fetch.

        Yields:
            Dictionary records matching ALL filter criteria.

        Returns:
            Async iterator yielding fetched records.
        """
        ...

    def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: port contract allows heterogeneous record values
    ]:  # Any: port contract allows heterogeneous record values
        """Fetch records with fallback search when primary lookup fails.

        When a primary ID lookup fails (e.g., DOI returns 404), attempts
        to find the record using the fallback value (e.g., search by title).

        Args:
            entity_type: The type of entity to fetch.
            filter_ids: List of primary IDs to filter by.
            filter_field: Field name for primary filtering (e.g., 'doi').
            fallback_mapping: Mapping from primary ID to fallback value.
            limit: Optional maximum number of records to fetch.

        Yields:
            Dictionary records found via primary lookup or fallback search.

        Returns:
            Async iterator yielding fetched records.
        """
        ...


@runtime_checkable
class DataSourceFactoryPort(Protocol):
    """Protocol for data source factory operations.

    Abstracts data source creation for health checking.
    """

    def list_providers(self) -> list[str]:
        """List available provider names.

        Returns:
            Collection of providers.
        """
        ...

    def create(
        self,
        provider: str,
    ) -> DataSourcePort:
        """Create a data source adapter for the given provider.

        Args:
            provider: Data provider name.

        Returns:
            Newly created data source instance.
        """
        ...
