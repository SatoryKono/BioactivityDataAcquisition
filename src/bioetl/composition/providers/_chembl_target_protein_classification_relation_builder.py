"""Internal relation-builder for ChEMBL target protein-classification wrappers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass, field
from typing import cast

from bioetl.application.services.protein_classification_resolution import (
    ProteinClassificationResolutionService,
    TargetProteinClassificationRecord,
)
from bioetl.domain.ports import DataSourcePort
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)

from ._chembl_target_protein_classification_helpers import (
    _PROTEIN_CLASS_ENTITY_TYPE,
    _TARGET_COMPONENT_ENTITY_TYPE,
    canonical_json,
    coerce_positive_int,
    component_ids_from_target_record,
    leaf_ids_from_component_row,
    target_id_from_record,
    target_ids_from_component_record,
)


@dataclass(slots=True)
class TargetProteinClassificationRelationBuilder:
    """Resolve relation rows from target and target-component source records."""

    data_source: DataSourcePort
    _component_cache: dict[int, JsonDict | None] = field(default_factory=dict)
    _protein_class_cache: dict[int, JsonDict | None] = field(default_factory=dict)
    _hierarchy_cache: dict[int, ProteinClassHierarchy] = field(default_factory=dict)

    def reset(self) -> None:
        self._component_cache.clear()
        self._protein_class_cache.clear()
        self._hierarchy_cache.clear()

    async def enrich_target_record(self, record: JsonDict) -> JsonDict:
        target_id = target_id_from_record(record)
        if target_id is None:
            return dict(record)
        component_ids = component_ids_from_target_record(record)
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
            target_id = target_id_from_record(record)
            if target_id is None:
                continue
            rows = await self.relation_rows_for_target(
                target_id=target_id,
                component_ids=component_ids_from_target_record(record),
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
            component_id = coerce_positive_int(component.get("component_id"))
            if component_id is None:
                continue
            target_ids = target_ids_from_component_record(component)
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
            leaf_ids = leaf_ids_from_component_row(row)
            hierarchies = tuple(
                [await self._resolve_leaf_hierarchy(leaf_id) for leaf_id in leaf_ids]
            )
            return _ComponentClassificationResult(hierarchies=hierarchies)
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

    async def _resolve_leaf_hierarchy(self, leaf_id: int) -> ProteinClassHierarchy:
        cached = self._hierarchy_cache.get(leaf_id)
        if cached is not None:
            return cached
        await self._prefetch_protein_class_chain(leaf_id)
        graph = ChEMBLProteinClassificationGraph.from_rows(
            protein_class_rows=[
                row for row in self._protein_class_cache.values() if row is not None
            ],
            target_component_rows=[
                {"component_id": 1, "protein_classification_ids": canonical_json([leaf_id])}
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
            current_id = coerce_positive_int(row.get("parent_id"))

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
            replacement_id = coerce_positive_int(row.get("replaced_by"))
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
