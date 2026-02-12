"""Subcellular Fraction Data Source wrapper.

Wraps a DataSourcePort to extract unique subcellular fractions from assay records.
Used to create the subcellular_fraction entity from ChEMBL data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from bioetl.application.core.entity_id import compute_subcellular_fraction_entity_id
from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class SubcellularFractionDataSource:
    """Wraps a DataSourcePort to extract subcellular fractions from assay records.

    This wrapper intercepts requests for 'subcellular_fraction' and fetches
    'assay' records instead, yielding unique subcellular fractions found.
    """

    SOURCE_ENTITY_TYPE = "assay"
    TARGET_ENTITY_TYPE = "subcellular_fraction"

    def __init__(self, data_source: DataSourcePort) -> None:
        """Initialize subcellular fraction data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap.
        """
        self._data_source = data_source
        self._seen_fractions: set[str] = set()

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self._data_source.__aenter__()
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
        """Fetch records, extracting fractions if entity_type is subcellular_fraction."""
        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            count = 0
            async for assay in self._data_source.fetch(
                entity_type=self.SOURCE_ENTITY_TYPE,
                limit=None,  # We can't easily limit source because of 1:M/deduplication
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
            ):
                fraction = assay.get("assay_subcellular_fraction")
                if not fraction or not fraction.strip():
                    continue

                if fraction not in self._seen_fractions:
                    self._seen_fractions.add(fraction)
                    yield self._create_fraction_record(
                        fraction, assay.get("assay_chembl_id")
                    )
                    count += 1
                    if limit and count >= limit:
                        return
        else:
            async for record in self._data_source.fetch(
                entity_type=entity_type,
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
            ):
                yield record

    def _create_fraction_record(
        self, fraction: str, assay_id: str | None
    ) -> dict[str, Any]:
        """Create a subcellular fraction record."""
        return {
            "entity_id": compute_subcellular_fraction_entity_id(fraction),
            "subcellular_fraction": fraction,
            "example_assay_chembl_id": assay_id,
            "assay_count": 1,  # Placeholder, not accurately counted here
        }

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()

    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort:
        """Check that wrapped adapter implements FilterableDataSourcePort."""
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
        """Fetch filtered records."""
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            count = 0
            async for assay in filterable.fetch_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=None,
            ):
                fraction = assay.get("assay_subcellular_fraction")
                if not fraction or not fraction.strip():
                    continue

                if fraction not in self._seen_fractions:
                    self._seen_fractions.add(fraction)
                    yield self._create_fraction_record(
                        fraction, assay.get("assay_chembl_id")
                    )
                    count += 1
                    if limit and count >= limit:
                        return
        else:
            async for record in filterable.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by multiple fields."""
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            count = 0
            async for assay in filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=None,
            ):
                fraction = assay.get("assay_subcellular_fraction")
                if not fraction or not fraction.strip():
                    continue

                if fraction not in self._seen_fractions:
                    self._seen_fractions.add(fraction)
                    yield self._create_fraction_record(
                        fraction, assay.get("assay_chembl_id")
                    )
                    count += 1
                    if limit and count >= limit:
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
        """Fetch records with fallback search."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type == self.TARGET_ENTITY_TYPE:
            self._seen_fractions = set()
            count = 0
            async for assay in filterable.fetch_filtered_with_fallback(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=None,
            ):
                fraction = assay.get("assay_subcellular_fraction")
                if not fraction or not fraction.strip():
                    continue

                if fraction not in self._seen_fractions:
                    self._seen_fractions.add(fraction)
                    yield self._create_fraction_record(
                        fraction, assay.get("assay_chembl_id")
                    )
                    count += 1
                    if limit and count >= limit:
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
        """Delegate get_source_metadata to wrapped data source."""
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None
