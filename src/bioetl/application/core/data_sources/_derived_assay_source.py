"""Shared mechanics for data sources derived from ChEMBL assay records."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import ClassVar, cast

from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.derived_scan_budget import (
    iter_derived_source,
    resolve_derived_upstream_limit,
)
from bioetl.application.core.target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)
from bioetl.domain.ports import DataSourcePort, FilterableDataSourcePort
from bioetl.domain.types import JsonDict


class _DerivedAssayDataSourceBase(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    SOURCE_ENTITY_TYPE = "assay"
    TARGET_ENTITY_TYPE: str
    ASSAY_LIMIT_MULTIPLIER: ClassVar[int]

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source

    def _upstream_limit(
        self,
        limit: int | None,
        filter_ids: list[str] | None = None,
        *,
        filter_id_count: int | None = None,
    ) -> int:
        return resolve_derived_upstream_limit(
            limit,
            multiplier=self.ASSAY_LIMIT_MULTIPLIER,
            filter_ids=filter_ids,
            filter_id_count=filter_id_count,
        )

    def _iter_assays(
        self,
        *,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(limit, filter_ids)
        source = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=scan_limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        return iter_derived_source(source, output_limit=limit, scan_limit=scan_limit)

    def _iter_filtered_assays(
        self,
        filterable: FilterableDataSourcePort,
        *,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(limit, filter_ids)
        source = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=scan_limit,
        )
        return iter_derived_source(source, output_limit=limit, scan_limit=scan_limit)

    def _iter_multi_filtered_assays(
        self,
        filterable: FilterableDataSourcePort,
        *,
        filters: dict[str, list[str]],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        filter_id_count = sum(len(values) for values in filters.values())
        scan_limit = self._upstream_limit(
            limit,
            filter_id_count=filter_id_count,
        )
        source = filterable.fetch_multi_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filters=filters,
            limit=scan_limit,
        )
        return iter_derived_source(source, output_limit=limit, scan_limit=scan_limit)

    def _iter_derived_records(
        self,
        assays: AsyncIterator[JsonDict],
        *,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        raise NotImplementedError

    async def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        assays = self._iter_filtered_assays(
            filterable,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        )
        async for record in self._iter_derived_records(assays, limit=limit):
            yield record

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        assays = self._iter_multi_filtered_assays(
            filterable,
            filters=filters,
            limit=limit,
        )
        async for record in self._iter_derived_records(assays, limit=limit):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        return self._upstream_limit(limit)

    async def _coerce_assay_records(
        self,
        assays: AsyncIterator[object],
    ) -> AsyncIterator[JsonDict]:
        async for assay in assays:
            if isinstance(assay, dict):
                yield cast("JsonDict", assay)
