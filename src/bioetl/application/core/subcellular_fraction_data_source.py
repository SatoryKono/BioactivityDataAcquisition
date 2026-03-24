"""Subcellular Fraction Data Source wrapper.

Wraps a DataSourcePort to extract unique assay_subcellular_fraction values
from Assay records and emit derived subcellular_fraction records.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from bioetl.application.core._data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _SourceMetadataDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort


class SubcellularFractionDataSource(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Wraps a DataSourcePort to extract subcellular fraction records."""

    SOURCE_ENTITY_TYPE = "assay"
    TARGET_ENTITY_TYPE = "subcellular_fraction"

    def __init__(self, data_source: DataSourcePort) -> None:
        """Initialize subcellular fraction data source wrapper."""
        self._data_source = data_source
        self._seen_fractions: set[str] = set()

    def _after_wrapped_data_source_enter(self) -> None:
        """Reset wrapper cache when entering a new async lifecycle."""
        self._seen_fractions = set()

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Yield subcellular-fraction records derived from assay fetches."""
        _ = offset
        async for record in self._fetch_subcellular_fractions(
            limit, query, filter_ids, filter_field
        ):
            yield record

    async def _fetch_subcellular_fractions(
        self,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Fetch assays and extract unique subcellular fraction records."""
        assays = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for record in self._extract_unique_fractions(assays, limit):
            yield record

    @staticmethod
    # Any: untyped API field value
    def _normalize_fraction(
        raw_fraction: Any,  # Any: type varies at runtime
    ) -> str | None:  # Any: type varies at runtime
        """Normalize subcellular fraction string."""
        if raw_fraction is None:
            return None
        fraction = str(raw_fraction).strip()
        return fraction or None

    @staticmethod
    def _compute_entity_id(subcellular_fraction: str) -> str:
        """Compute entity ID for a subcellular fraction."""
        normalized = (
            subcellular_fraction.lower().strip() if subcellular_fraction else ""
        )
        composite = f"subcellular_fraction:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    def _create_fraction_record(
        self,
        assay: JsonDict,  # Any: heterogeneous record values
        fraction: str,
    ) -> JsonDict:  # Any: heterogeneous record values
        """Create a subcellular fraction record."""
        assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
        return {
            "entity_id": self._compute_entity_id(fraction),
            "subcellular_fraction": fraction,
            "example_assay_id": str(assay_id).strip() if assay_id else None,
            "assay_count": 1,
        }

    async def _fetch_target_filtered_records(
        self,
        filterable: Any,  # Any: filterable adapter is structurally validated by mixin
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Yield subcellular fractions from filtered upstream assays."""
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

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: Any,  # Any: filterable adapter is structurally validated by mixin
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Yield subcellular fractions from multi-filtered upstream assays."""
        async for record in self._fetch_filtered_fractions(
            filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=None,
            ),
            limit,
        ):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        """Keep fallback-enabled assay fetches unbounded upstream."""
        _ = limit
        return None

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[Any],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Transform fallback-fetched assays into subcellular fraction records."""
        return self._fetch_filtered_fractions(source_records, limit)

    async def _fetch_filtered_fractions(
        self,
        assays: AsyncIterator[JsonDict],  # Any: heterogeneous record values
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Extract subcellular fractions from a filtered assay stream."""
        async for record in self._extract_unique_fractions(assays, limit):
            yield record

    async def _extract_unique_fractions(
        self,
        assays: AsyncIterator[JsonDict],  # Any: heterogeneous record values
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:  # Any: heterogeneous record values
        """Collect unique subcellular fraction records from assay stream."""
        self._seen_fractions = set()
        records: dict[str, JsonDict] = {}  # Any: heterogeneous record values

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


__all__ = ["SubcellularFractionDataSource"]
