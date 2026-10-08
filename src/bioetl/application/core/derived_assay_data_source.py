"""Shared fetch choreography for assay-derived data-source wrappers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, ClassVar, cast

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
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort


class DerivedAssayDataSource(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Own the common bounded-scan contract for assay-derived entities."""

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

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        if limit is not None and limit <= 0:
            return
        scan_limit = self._upstream_limit(limit, filter_ids)
        source = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=scan_limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        bounded = iter_derived_source(
            source,
            output_limit=limit,
            scan_limit=scan_limit,
        )
        async for record in self._expand_derived_records(
            bounded,
            limit=limit,
            offset=offset,
        ):
            yield record

    async def _fetch_target_filtered_records(
        self,
        filterable: Any,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(limit, filter_ids)
        source = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=scan_limit,
        )
        async for record in self._expand_bounded_source(
            source,
            limit=limit,
            scan_limit=scan_limit,
        ):
            yield record

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: Any,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(
            limit,
            filter_id_count=sum(len(values) for values in filters.values()),
        )
        source = filterable.fetch_multi_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filters=filters,
            limit=scan_limit,
        )
        async for record in self._expand_bounded_source(
            source,
            limit=limit,
            scan_limit=scan_limit,
        ):
            yield record

    async def _expand_bounded_source(
        self,
        source: AsyncIterator[object],
        *,
        limit: int | None,
        scan_limit: int,
    ) -> AsyncIterator[JsonDict]:
        bounded = iter_derived_source(
            source,
            output_limit=limit,
            scan_limit=scan_limit,
        )
        async for record in self._expand_derived_records(
            self._coerce_assay_records(bounded),
            limit=limit,
        ):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        return self._upstream_limit(limit)

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        return self._expand_derived_records(
            self._coerce_assay_records(source_records),
            limit=limit,
        )

    async def _coerce_assay_records(
        self,
        assays: AsyncIterator[object],
    ) -> AsyncIterator[JsonDict]:
        async for assay in assays:
            if isinstance(assay, dict):
                yield cast("JsonDict", assay)

    def _expand_derived_records(
        self,
        assays: AsyncIterator[JsonDict],
        *,
        limit: int | None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        raise NotImplementedError
