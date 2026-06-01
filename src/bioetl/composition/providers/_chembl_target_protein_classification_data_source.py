"""Composition-owned ChEMBL target protein-classification data-source wrappers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)
from bioetl.application.services.protein_classification_resolution import (
    ProteinClassificationResolutionService,
    TargetProteinClassificationRecord,
)
from bioetl.domain.ports import DataSourcePort, FilterableDataSourcePort
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)

__all__ = [
    "TargetProteinClassificationDataSource",
    "TargetProteinClassificationEnrichedTargetDataSource",
]

_TARGET_ENTITY_TYPE = "target"
_TARGET_COMPONENT_ENTITY_TYPE = "target_component"
_PROTEIN_CLASS_ENTITY_TYPE = "protein_class"
_TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE = "target_protein_classification"


class TargetProteinClassificationEnrichedTargetDataSource(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Decorate ChEMBL target records with resolved protein-classification rows."""

    SOURCE_ENTITY_TYPE = _TARGET_ENTITY_TYPE
    TARGET_ENTITY_TYPE = _TARGET_ENTITY_TYPE

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source
        self._builder = _TargetProteinClassificationRelationBuilder(data_source)

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
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Expose target protein-classification rows derived from ChEMBL components."""

    SOURCE_ENTITY_TYPE = _TARGET_COMPONENT_ENTITY_TYPE
    TARGET_ENTITY_TYPE = _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source
        self._builder = _TargetProteinClassificationRelationBuilder(data_source)

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


@dataclass(slots=True)
class _TargetProteinClassificationRelationBuilder:
    data_source: DataSourcePort
    _component_cache: dict[int, JsonDict | None] = field(default_factory=dict)
    _protein_class_cache: dict[int, JsonDict | None] = field(default_factory=dict)
    _hierarchy_cache: dict[int, ProteinClassHierarchy] = field(default_factory=dict)

    def reset(self) -> None:
        self._component_cache.clear()
        self._protein_class_cache.clear()
        self._hierarchy_cache.clear()

    async def enrich_target_record(self, record: JsonDict) -> JsonDict:
        target_id = _target_id_from_record(record)
        if target_id is None:
            return dict(record)
        component_ids = _component_ids_from_target_record(record)
        rows = await self.relation_rows_for_target(
            target_id=target_id,
            component_ids=component_ids,
        )
        enriched = dict(record)
        enriched["target_protein_classifications"] = rows
        return enriched

    async def iter_relation_rows_from_targets(
        self,
        target_records: AsyncIterator[object],
        *,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        emitted = 0
        async for record in target_records:
            if not isinstance(record, Mapping):
                continue
            target_id = _target_id_from_record(record)
            if target_id is None:
                continue
            rows = await self.relation_rows_for_target(
                target_id=target_id,
                component_ids=_component_ids_from_target_record(record),
            )
            for row in rows:
                yield row
                emitted += 1
                if limit is not None and emitted >= limit:
                    return

    async def iter_relation_rows_from_components(
        self,
        component_records: AsyncIterator[object],
        *,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        emitted = 0
        index_by_target: dict[str, int] = {}
        seen_leaf_by_target: dict[str, set[int]] = {}
        seen_targets: set[str] = set()
        resolved_targets: set[str] = set()

        async for raw_record in component_records:
            if not isinstance(raw_record, Mapping):
                continue
            component = cast("Mapping[str, object]", raw_record)
            component_id = _coerce_positive_int(component.get("component_id"))
            if component_id is None:
                continue
            target_ids = _target_ids_from_component_record(component)
            seen_targets.update(target_ids)
            component_result = await self._resolve_component(component_id, component)
            if component_result.error is not None:
                continue
            for target_id in target_ids:
                for hierarchy in component_result.hierarchies:
                    seen_leafs = seen_leaf_by_target.setdefault(target_id, set())
                    if hierarchy.leaf_id in seen_leafs:
                        continue
                    seen_leafs.add(hierarchy.leaf_id)
                    resolved_targets.add(target_id)
                    row = TargetProteinClassificationRecord.resolved(
                        target_id=target_id,
                        hierarchy_index=index_by_target.get(target_id, 0),
                        component_id=component_id,
                        hierarchy=hierarchy,
                    ).to_dict()
                    index_by_target[target_id] = index_by_target.get(target_id, 0) + 1
                    yield row
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        return

        for target_id in sorted(seen_targets - resolved_targets):
            yield TargetProteinClassificationRecord.missing(target_id).to_dict()
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    async def relation_rows_for_target(
        self,
        *,
        target_id: str,
        component_ids: Iterable[int],
    ) -> list[JsonDict]:
        normalized_component_ids = tuple(dict.fromkeys(component_ids))
        component_results = {
            component_id: await self._resolve_component(component_id)
            for component_id in normalized_component_ids
        }
        port = _ResolvedComponentClassificationPort(component_results)
        result = ProteinClassificationResolutionService(port).resolve_target(
            target_id=target_id,
            component_ids=normalized_component_ids,
        )
        return [row.to_dict() for row in result.rows]

    async def _resolve_component(
        self,
        component_id: int,
        component_row: Mapping[str, object] | None = None,
    ) -> _ComponentClassificationResult:
        try:
            row = (
                dict(component_row)
                if component_row is not None
                else await self._load_component_row(component_id)
            )
            if row is None:
                return _ComponentClassificationResult(
                    hierarchies=(),
                    error=ProteinClassificationResolutionError(
                        f"missing target_component row {component_id}"
                    ),
                )
            leaf_ids = _leaf_ids_from_component_row(row)
            hierarchies: list[ProteinClassHierarchy] = []
            for leaf_id in leaf_ids:
                hierarchies.append(await self._resolve_leaf_hierarchy(leaf_id))
            return _ComponentClassificationResult(hierarchies=tuple(hierarchies))
        except ProteinClassificationResolutionError as exc:
            return _ComponentClassificationResult(hierarchies=(), error=exc)

    async def _load_component_row(self, component_id: int) -> JsonDict | None:
        if component_id not in self._component_cache:
            self._component_cache[component_id] = await self._fetch_one(
                _TARGET_COMPONENT_ENTITY_TYPE,
                "component_id",
                component_id,
            )
        return self._component_cache[component_id]

    async def _resolve_leaf_hierarchy(
        self,
        leaf_id: int,
    ) -> ProteinClassHierarchy:
        cached = self._hierarchy_cache.get(leaf_id)
        if cached is not None:
            return cached
        await self._prefetch_protein_class_chain(leaf_id)
        graph = ChEMBLProteinClassificationGraph.from_rows(
            protein_class_rows=[
                row for row in self._protein_class_cache.values() if row is not None
            ],
            target_component_rows=[
                {
                    "component_id": 1,
                    "protein_classification_ids": _canonical_json([leaf_id]),
                }
            ],
        )
        hierarchies = graph.get_component_classifications(1)
        if not hierarchies:
            raise ProteinClassificationResolutionError(
                f"no hierarchy resolved for protein_class_id={leaf_id}"
            )
        hierarchy = hierarchies[0]
        self._hierarchy_cache[leaf_id] = hierarchy
        return hierarchy

    async def _prefetch_protein_class_chain(self, leaf_id: int) -> None:
        current_id = await self._resolve_replaced_leaf_id(leaf_id)
        seen: set[int] = set()
        while current_id is not None:
            if current_id in seen:
                raise ProteinClassificationResolutionError(
                    f"parent cycle detected for protein_class_id={leaf_id}"
                )
            seen.add(current_id)
            row = await self._load_protein_class_row(current_id)
            current_id = _coerce_positive_int(row.get("parent_id"))

    async def _resolve_replaced_leaf_id(self, leaf_id: int) -> int:
        current_id = leaf_id
        seen: set[int] = set()
        while True:
            if current_id in seen:
                raise ProteinClassificationResolutionError(
                    f"replaced_by cycle detected for protein_class_id={leaf_id}"
                )
            seen.add(current_id)
            row = await self._load_protein_class_row(current_id)
            replacement_id = _coerce_positive_int(row.get("replaced_by"))
            if replacement_id is None:
                return current_id
            current_id = replacement_id

    async def _load_protein_class_row(self, protein_class_id: int) -> JsonDict:
        if protein_class_id not in self._protein_class_cache:
            self._protein_class_cache[protein_class_id] = await self._fetch_one(
                _PROTEIN_CLASS_ENTITY_TYPE,
                "protein_class_id",
                protein_class_id,
            )
        row = self._protein_class_cache[protein_class_id]
        if row is None:
            raise ProteinClassificationResolutionError(
                f"missing protein classification node {protein_class_id}"
            )
        return row

    async def _fetch_one(
        self,
        entity_type: str,
        filter_field: str,
        value: int,
    ) -> JsonDict | None:
        async for record in self.data_source.fetch(
            entity_type=entity_type,
            limit=1,
            filter_ids=[str(value)],
            filter_field=filter_field,
        ):
            if isinstance(record, Mapping):
                return dict(record)
        return None


@dataclass(frozen=True, slots=True)
class _ComponentClassificationResult:
    hierarchies: tuple[ProteinClassHierarchy, ...]
    error: ProteinClassificationResolutionError | None = None


class _ResolvedComponentClassificationPort:
    def __init__(
        self,
        component_results: Mapping[int, _ComponentClassificationResult],
    ) -> None:
        self._component_results = component_results

    def get_component_classifications(
        self,
        component_id: int,
    ) -> tuple[ProteinClassHierarchy, ...]:
        result = self._component_results.get(component_id)
        if result is None:
            return ()
        if result.error is not None:
            raise result.error
        return result.hierarchies


def _target_id_from_record(record: Mapping[str, object]) -> str | None:
    for key in ("target_id", "target_chembl_id"):
        value = _coerce_text(record.get(key))
        if value is not None:
            return value
    return None


def _component_ids_from_target_record(record: Mapping[str, object]) -> tuple[int, ...]:
    raw_components = record.get("target_components")
    if not isinstance(raw_components, list):
        return ()
    component_ids = [
        component_id
        for item in raw_components
        if isinstance(item, Mapping)
        if (component_id := _coerce_positive_int(item.get("component_id"))) is not None
    ]
    return tuple(dict.fromkeys(component_ids))


def _target_ids_from_component_record(record: Mapping[str, object]) -> tuple[str, ...]:
    raw_targets = record.get("targets")
    if not isinstance(raw_targets, list):
        return ()
    target_ids = [
        target_id
        for item in raw_targets
        if isinstance(item, Mapping)
        if (target_id := _target_id_from_record(item)) is not None
    ]
    return tuple(dict.fromkeys(target_ids))


def _leaf_ids_from_component_row(record: Mapping[str, object]) -> tuple[int, ...]:
    leaf_ids = _leaf_ids_from_value(record.get("protein_classification_ids"))
    if leaf_ids:
        return leaf_ids
    return _leaf_ids_from_classification_objects(record.get("protein_classifications"))


def _leaf_ids_from_classification_objects(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    leaf_ids = [
        leaf_id
        for item in value
        if isinstance(item, Mapping)
        if (
            leaf_id := _coerce_positive_int(
                item.get("protein_classification_id")
                or item.get("protein_class_id")
                or item.get("leaf_id")
            )
        )
        is not None
    ]
    return tuple(dict.fromkeys(leaf_ids))


def _leaf_ids_from_value(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    loaded = value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ProteinClassificationResolutionError(
                "protein_classification_ids must be canonical JSON"
            ) from exc
    if not isinstance(loaded, Iterable) or isinstance(loaded, (str, bytes)):
        return ()
    leaf_ids = [
        leaf_id
        for item in loaded
        if (leaf_id := _coerce_positive_int(item)) is not None
    ]
    return tuple(dict.fromkeys(leaf_ids))


def _coerce_positive_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return _coerce_positive_int(int(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return _coerce_positive_int(int(stripped))
        except ValueError:
            return None
    return None


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
