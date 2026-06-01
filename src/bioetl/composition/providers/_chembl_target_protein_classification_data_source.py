"""Composition-owned ChEMBL target protein-classification data-source wrappers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import cast

from bioetl.composition.providers._chembl_target_protein_classification_helpers import (
    _TARGET_COMPONENT_ENTITY_TYPE,
    _TARGET_ENTITY_TYPE,
    _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE,
)
from bioetl.composition.providers._chembl_target_protein_classification_relation_builder import (
    TargetProteinClassificationRelationBuilder,
)
from bioetl.composition.providers._derived_target_data_source_delegation import (
    DerivedTargetDataSourceDelegationMixin,
)
from bioetl.domain.ports import DataSourcePort, FilterableDataSourcePort
from bioetl.domain.types import JsonDict

__all__ = [
    "TargetProteinClassificationDataSource",
    "TargetProteinClassificationEnrichedTargetDataSource",
]


class TargetProteinClassificationEnrichedTargetDataSource(
    DerivedTargetDataSourceDelegationMixin,
):
    """Decorate ChEMBL target records with resolved protein-classification rows."""

    SOURCE_ENTITY_TYPE = _TARGET_ENTITY_TYPE
    TARGET_ENTITY_TYPE = _TARGET_ENTITY_TYPE

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source
        self._builder = TargetProteinClassificationRelationBuilder(data_source)

    def _after_wrapped_data_source_enter(self) -> None:
        self._builder.reset()

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        source_records = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )
        async for record in self._enrich_target_records(source_records):
            yield record

    async def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        source_records = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        )
        async for record in self._enrich_target_records(source_records):
            yield record

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        source_records = filterable.fetch_multi_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filters=filters,
            limit=limit,
        )
        async for record in self._enrich_target_records(source_records):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        return limit

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        _ = limit
        return self._enrich_target_records(source_records)

    async def _enrich_target_records(
        self,
        source_records: AsyncIterator[object],
    ) -> AsyncIterator[JsonDict]:
        async for record in source_records:
            if not isinstance(record, Mapping):
                continue
            yield await self._builder.enrich_target_record(cast("JsonDict", record))


class TargetProteinClassificationDataSource(
    DerivedTargetDataSourceDelegationMixin,
):
    """Expose target protein-classification rows derived from ChEMBL components."""

    SOURCE_ENTITY_TYPE = _TARGET_COMPONENT_ENTITY_TYPE
    TARGET_ENTITY_TYPE = _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source
        self._builder = TargetProteinClassificationRelationBuilder(data_source)

    def _after_wrapped_data_source_enter(self) -> None:
        self._builder.reset()

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        _ = query
        component_records = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=None,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )
        async for record in self._builder.iter_relation_rows_from_components(
            component_records,
            limit=limit,
        ):
            yield record

    async def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        if filter_field in {"target_id", "target_chembl_id"}:
            target_records = filterable.fetch_filtered(
                entity_type=_TARGET_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field="target_chembl_id",
                limit=None,
            )
            async for record in self._builder.iter_relation_rows_from_targets(
                target_records,
                limit=limit,
            ):
                yield record
            return

        component_records = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=None,
        )
        async for record in self._builder.iter_relation_rows_from_components(
            component_records,
            limit=limit,
        ):
            yield record

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        component_records = filterable.fetch_multi_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filters=filters,
            limit=None,
        )
        async for record in self._builder.iter_relation_rows_from_components(
            component_records,
            limit=limit,
        ):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        _ = limit
        return None

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        return self._builder.iter_relation_rows_from_components(
            source_records,
            limit=limit,
        )
