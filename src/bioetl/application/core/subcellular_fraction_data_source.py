"""Subcellular Fraction Data Source wrapper.

Wraps a DataSourcePort to extract unique assay_subcellular_fraction values
from Assay records and emit derived subcellular_fraction records.
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
    """Wraps a DataSourcePort to extract subcellular fraction records."""

    SOURCE_ENTITY_TYPE = "assay"
    TARGET_ENTITY_TYPE = "subcellular_fraction"

    def __init__(self, data_source: DataSourcePort) -> None:
        """Initialize subcellular fraction data source wrapper."""
        self._data_source = data_source
        self._seen_fractions: set[str] = set()

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context and reset cache."""
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
        """Fetch records, extracting subcellular fractions if requested."""
        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_subcellular_fractions(
                limit, query, filter_ids, filter_field
            ):
                yield record
        else:
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
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays and extract unique subcellular fraction records."""
        self._seen_fractions = set()
        records: dict[str, dict[str, Any]] = {}

        async for assay in self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            raw_fraction = assay.get("assay_subcellular_fraction")
            fraction = self._normalize_fraction(raw_fraction)
            if not fraction:
                continue

            key = fraction.lower()
            record = records.get(key)
            if record is None:
                record = self._create_fraction_record(assay, fraction)
                records[key] = record
                self._seen_fractions.add(key)
                if limit and len(records) >= limit:
                    break
            else:
                record["assay_count"] = int(record["assay_count"]) + 1
                if record["example_assay_id"] is None:
                    assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
                    record["example_assay_id"] = (
                        str(assay_id).strip() if assay_id else None
                    )

        for record in records.values():
            yield record

    @staticmethod
    def _normalize_fraction(raw_fraction: Any) -> str | None:
        """Normalize subcellular fraction string."""
        if raw_fraction is None:
            return None
        fraction = str(raw_fraction).strip()
        return fraction or None

    @staticmethod
    def _compute_entity_id(subcellular_fraction: str) -> str:
        """Compute entity ID for a subcellular fraction."""
        normalized = subcellular_fraction.lower().strip() if subcellular_fraction else ""
        composite = f"subcellular_fraction:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    def _create_fraction_record(
        self,
        assay: dict[str, Any],
        fraction: str,
    ) -> dict[str, Any]:
        """Create a subcellular fraction record."""
        assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
        return {
            "entity_id": self._compute_entity_id(fraction),
            "subcellular_fraction": fraction,
            "example_assay_id": str(assay_id).strip() if assay_id else None,
            "assay_count": 1,
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
        """Fetch filtered records with subcellular fraction extraction."""
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_filtered_fractions(
                filterable.fetch_filtered(
                    entity_type=self.SOURCE_ENTITY_TYPE,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    limit=None,
                ),
                limit,
            ):
                yield record
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
        """Fetch multi-filtered records with subcellular fraction extraction."""
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_filtered_fractions(
                filterable.fetch_multi_filtered(
                    entity_type=self.SOURCE_ENTITY_TYPE,
                    filters=filters,
                    limit=None,
                ),
                limit,
            ):
                yield record
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
        """Fetch records with fallback and subcellular fraction extraction."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_filtered_fractions(
                filterable.fetch_filtered_with_fallback(
                    entity_type=self.SOURCE_ENTITY_TYPE,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    fallback_mapping=fallback_mapping,
                    limit=None,
                ),
                limit,
            ):
                yield record
        else:
            async for record in filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record

    async def _fetch_filtered_fractions(
        self,
        assays: AsyncIterator[dict[str, Any]],
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract subcellular fractions from a filtered assay stream."""
        self._seen_fractions = set()
        records: dict[str, dict[str, Any]] = {}

        async for assay in assays:
            raw_fraction = assay.get("assay_subcellular_fraction")
            fraction = self._normalize_fraction(raw_fraction)
            if not fraction:
                continue

            key = fraction.lower()
            record = records.get(key)
            if record is None:
                record = self._create_fraction_record(assay, fraction)
                records[key] = record
                self._seen_fractions.add(key)
                if limit and len(records) >= limit:
                    break
            else:
                record["assay_count"] = int(record["assay_count"]) + 1
                if record["example_assay_id"] is None:
                    assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
                    record["example_assay_id"] = (
                        str(assay_id).strip() if assay_id else None
                    )

        for record in records.values():
            yield record

    def get_source_metadata(self, api_version: str | None = None) -> Any:
        """Delegate get_source_metadata to wrapped data source if supported."""
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None


__all__ = ["SubcellularFractionDataSource"]
