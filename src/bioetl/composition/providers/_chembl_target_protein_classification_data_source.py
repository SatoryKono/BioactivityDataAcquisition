"""Composition-owned ChEMBL target protein-classification data-source wrappers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from types import TracebackType
from typing import cast

from bioetl.composition.providers._chembl_target_protein_classification_helpers import (
    _TARGET_COMPONENT_ENTITY_TYPE,
    _TARGET_ENTITY_TYPE,
    _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE,
)
from bioetl.composition.providers._chembl_target_protein_classification_relation_builder import (
    TargetProteinClassificationRelationBuilder,
)
from bioetl.domain.ports import (
    DataSourcePort,
    FilterableDataSourcePort,
    HealthCheckResult,
)
from bioetl.domain.types import HealthStatus, JsonDict

__all__ = [
    "TargetProteinClassificationDataSource",
    "TargetProteinClassificationEnrichedTargetDataSource",
]


class _TargetProteinClassificationDataSourceMixin:
    """Local wrapper surface that avoids growing application-core facade imports."""

    _data_source: DataSourcePort
    SOURCE_ENTITY_TYPE: str
    TARGET_ENTITY_TYPE: str

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> "_TargetProteinClassificationDataSourceMixin":
        """Enter the wrapped data-source context and reset wrapper state."""
        await self._data_source.__aenter__()
        self._after_wrapped_data_source_enter()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Delegate async context teardown to the wrapped data source."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    def _after_wrapped_data_source_enter(self) -> None:
        """Hook for subclasses that need to reset wrapper-local state."""

    async def health_check(self) -> HealthStatus:
        """Delegate health checks to the wrapped data source."""
        return await self._data_source.health_check()

    async def check_health(self) -> HealthCheckResult:
        """Delegate detailed health checks when available, else synthesize one."""
        check_health = getattr(self._data_source, "check_health", None)
        if check_health is not None and callable(check_health):
            return await check_health()
        return HealthCheckResult(
            status=await self._data_source.health_check(),
            latency_ms=0.0,
            provider=self.provider_name,
        )

    async def aclose(self) -> None:
        """Delegate resource shutdown to the wrapped data source."""
        await self._data_source.aclose()

    def get_source_metadata(self, api_version: str | None = None) -> object | None:
        """Delegate source metadata lookup to the wrapped data source if present."""
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return cast("object | None", get_metadata(api_version))
        return None

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch derived target rows or delegate non-target entities."""
        if entity_type == self.TARGET_ENTITY_TYPE:
            return self._fetch_target_records(
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
                offset=offset,
            )
        return self._data_source.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )

    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort:
        """Validate that the wrapped source supports filterable data-source APIs."""
        if isinstance(self._data_source, FilterableDataSourcePort):
            return self._data_source
        message = f"{self.provider_name} does not support {method_name}"
        raise TypeError(message)

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch filtered derived target rows or delegate non-target entities."""
        filterable = self._ensure_filterable("fetch_filtered")
        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_target_filtered_records(
                filterable=filterable,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
            return
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
    ) -> AsyncIterator[JsonDict]:
        """Fetch multi-filtered derived target rows or delegate non-target entities."""
        filterable = self._ensure_filterable("fetch_multi_filtered")
        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_target_multi_filtered_records(
                filterable=filterable,
                filters=filters,
                limit=limit,
            ):
                yield record
            return
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
    ) -> AsyncIterator[JsonDict]:
        """Fetch fallback-enabled derived target rows or delegate non-target entities."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")
        if entity_type == self.TARGET_ENTITY_TYPE:
            async for record in self._fetch_target_filtered_with_fallback_records(
                filterable=filterable,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record
            return
        async for record in filterable.fetch_filtered_with_fallback(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=limit,
        ):
            yield record

    def _fetch_target_filtered_with_fallback_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        """Yield target rows from fallback-enabled upstream source records."""
        source_records = filterable.fetch_filtered_with_fallback(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=self._resolve_target_fallback_upstream_limit(limit),
        )
        return self._yield_target_records_from_fallback_source_records(
            source_records,
            limit,
        )

    def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch derived target records."""
        raise NotImplementedError

    def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch filtered derived target records."""
        raise NotImplementedError

    def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch multi-filtered derived target records."""
        raise NotImplementedError

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        """Resolve the upstream limit for fallback source fetches."""
        raise NotImplementedError

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        """Yield target records from fallback source records."""
        raise NotImplementedError


class TargetProteinClassificationEnrichedTargetDataSource(
    _TargetProteinClassificationDataSourceMixin,
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
    _TargetProteinClassificationDataSourceMixin,
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
