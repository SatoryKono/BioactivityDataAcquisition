"""Subcellular Fraction Data Source wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core import subcellular_fraction_support as support
from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.derived_scan_budget import (
    bounded_source_records,
    resolve_derived_upstream_limit,
)
from bioetl.application.core.target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort

__all__ = ["SubcellularFractionDataSource"]


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
    # assay_subcellular_fraction is sparse; scale upstream assays for --limit runs.
    ASSAY_LIMIT_MULTIPLIER: ClassVar[int] = 200

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source
        self._seen_fractions: set[str] = set()

    def _after_wrapped_data_source_enter(self) -> None:
        self._seen_fractions = set()

    def _upstream_limit(
        self,
        limit: int | None,
        filter_ids: list[str] | None = None,
    ) -> int:
        return resolve_derived_upstream_limit(
            limit,
            multiplier=self.ASSAY_LIMIT_MULTIPLIER,
            filter_ids=filter_ids,
        )

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        skip = max(0, offset or 0)
        seen = 0
        emitted = 0
        fetch_limit = None if limit is None else (limit + skip)
        async for record in self._fetch_subcellular_fractions(
            fetch_limit, query, filter_ids, filter_field
        ):
            if seen < skip:
                seen += 1
                continue
            yield record
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    async def _fetch_subcellular_fractions(
        self,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[JsonDict]:
        assays = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=self._upstream_limit(limit, filter_ids),
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for record in self._extract_unique_fractions(assays, limit):
            yield record

    @staticmethod
    def _normalize_fraction(
        raw_fraction: Any,  # Any: upstream assay payload may carry heterogeneous scalar/object values.
    ) -> str | None:
        return support.normalize_fraction(raw_fraction)

    @staticmethod
    def _compute_entity_id(subcellular_fraction: str) -> str:
        return support.compute_entity_id(subcellular_fraction)

    def _create_fraction_record(
        self,
        assay: JsonDict,
        fraction: str,
    ) -> JsonDict:
        return support.create_fraction_record(assay, fraction)

    async def _fetch_target_filtered_records(
        self,
        filterable: Any,  # Any: mixin provides a duck-typed filtered fetch surface rather than one concrete protocol.
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        async for record in self._fetch_filtered_fractions(
            filterable.fetch_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=self._upstream_limit(limit, filter_ids),
            ),
            limit,
        ):
            yield record

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: Any,  # Any: mixin accepts multiple runtime filterable adapters with the same fetch contract.
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        id_count = sum(len(values) for values in filters.values())
        async for record in self._fetch_filtered_fractions(
            filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=resolve_derived_upstream_limit(
                    limit,
                    multiplier=self.ASSAY_LIMIT_MULTIPLIER,
                    filter_id_count=id_count,
                ),
            ),
            limit,
        ):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        return self._upstream_limit(limit)

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[
            object
        ],  # object: fallback source stream forwards raw upstream records before normalization.
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        return self._fetch_filtered_fractions(source_records, limit)

    async def _fetch_filtered_fractions(
        self,
        assays: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        async for record in self._extract_unique_fractions(
            self._coerce_assay_records(assays), limit
        ):
            yield record

    async def _coerce_assay_records(
        self,
        assays: AsyncIterator[object],
    ) -> AsyncIterator[JsonDict]:
        """Yield only mapping-shaped assay records expected by extraction helpers."""
        async for assay in assays:
            if isinstance(assay, dict):
                yield cast("JsonDict", assay)

    async def _extract_unique_fractions(
        self,
        assays: AsyncIterator[JsonDict],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        async for record in support.extract_unique_fraction_records(
            bounded_source_records(assays),
            limit,
            self._seen_fractions,
            # Limited runs stop once the unique quota is filled so upstream I/O
            # stays inside the derived-scan time budget. Unlimited runs keep the
            # full-stream aggregation contract (#7787).
            continue_after_limit=limit is None,
        ):
            yield record
