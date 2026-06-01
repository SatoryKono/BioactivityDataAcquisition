"""ChEMBL protein classification graph adapter."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from bioetl.domain.ports import ProteinClassificationPort
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
    ProteinClassLevel,
)

__all__ = [
    "ChEMBLProteinClassificationGraph",
    "ProteinClassificationNode",
]


@dataclass(frozen=True, slots=True)
class ProteinClassificationNode:
    """One ChEMBL protein_classification node."""

    protein_class_id: int
    parent_id: int | None
    class_level: int | None
    pref_name: str | None = None
    protein_class_desc: str | None = None
    replaced_by: int | None = None


class ChEMBLProteinClassificationGraph(ProteinClassificationPort):
    """Resolve component protein classification IDs against a preloaded graph."""

    def __init__(
        self,
        *,
        nodes: Mapping[int, ProteinClassificationNode],
        component_leaf_ids: Mapping[int, Iterable[int]],
    ) -> None:
        self._nodes = dict(nodes)
        self._component_leaf_ids = {
            component_id: tuple(dict.fromkeys(leaf_ids))
            for component_id, leaf_ids in component_leaf_ids.items()
        }
        self._hierarchy_cache: dict[int, ProteinClassHierarchy] = {}

    @classmethod
    def from_rows(
        cls,
        *,
        protein_class_rows: Iterable[Mapping[str, object]],
        target_component_rows: Iterable[Mapping[str, object]],
    ) -> ChEMBLProteinClassificationGraph:
        """Build a deterministic graph adapter from existing Silver rows."""
        nodes = {
            node.protein_class_id: node
            for node in (
                _node_from_row(row)
                for row in protein_class_rows
            )
            if node is not None
        }
        component_leaf_ids = {
            component_id: leaf_ids
            for component_id, leaf_ids in (
                _component_leaf_ids_from_row(row)
                for row in target_component_rows
            )
            if component_id is not None
        }
        return cls(nodes=nodes, component_leaf_ids=component_leaf_ids)

    def get_component_classifications(
        self,
        component_id: int,
    ) -> tuple[ProteinClassHierarchy, ...]:
        """Return deterministic L1-L5 hierarchies for a component."""
        if component_id < 1:
            raise ProteinClassificationResolutionError(
                f"component_id must be positive, got {component_id}"
            )
        leaf_ids = self._component_leaf_ids.get(component_id, ())
        hierarchies = [self._hierarchy_for_leaf_id(leaf_id) for leaf_id in leaf_ids]
        return tuple(sorted(hierarchies, key=lambda hierarchy: hierarchy.leaf_id))

    def _hierarchy_for_leaf_id(self, leaf_id: int) -> ProteinClassHierarchy:
        cached = self._hierarchy_cache.get(leaf_id)
        if cached is not None:
            return cached
        resolved_leaf_id = self._resolve_replacement(leaf_id)
        levels = self._walk_levels(resolved_leaf_id)
        hierarchy = ProteinClassHierarchy(
            l1=levels.get(1, ProteinClassLevel.empty()),
            l2=levels.get(2, ProteinClassLevel.empty()),
            l3=levels.get(3, ProteinClassLevel.empty()),
            l4=levels.get(4, ProteinClassLevel.empty()),
            l5=levels.get(5, ProteinClassLevel.empty()),
            leaf_id=resolved_leaf_id,
        )
        self._hierarchy_cache[leaf_id] = hierarchy
        return hierarchy

    def _resolve_replacement(self, leaf_id: int) -> int:
        current_id = leaf_id
        seen: set[int] = set()
        while True:
            if current_id in seen:
                raise ProteinClassificationResolutionError(
                    f"replaced_by cycle detected for protein_class_id={leaf_id}"
                )
            seen.add(current_id)
            node = self._node(current_id)
            if node.replaced_by is None:
                return current_id
            current_id = node.replaced_by

    def _walk_levels(self, leaf_id: int) -> dict[int, ProteinClassLevel]:
        current_id: int | None = leaf_id
        seen: set[int] = set()
        levels: dict[int, ProteinClassLevel] = {}
        while current_id is not None:
            if current_id in seen:
                raise ProteinClassificationResolutionError(
                    f"parent cycle detected for protein_class_id={leaf_id}"
                )
            seen.add(current_id)
            node = self._node(current_id)
            level = _validated_class_level(node, leaf_id=leaf_id)
            if level <= 5:
                levels[level] = ProteinClassLevel(
                    id=node.protein_class_id,
                    name=node.pref_name,
                    desc=node.protein_class_desc,
                )
            current_id = node.parent_id

        _validate_contiguous_levels(levels, leaf_id=leaf_id)
        return levels

    def _node(self, protein_class_id: int) -> ProteinClassificationNode:
        node = self._nodes.get(protein_class_id)
        if node is None:
            raise ProteinClassificationResolutionError(
                f"missing protein classification node {protein_class_id}"
            )
        return node


def _node_from_row(
    row: Mapping[str, object],
) -> ProteinClassificationNode | None:
    protein_class_id = _coerce_int(row.get("protein_class_id"))
    if protein_class_id is None or protein_class_id < 1:
        return None
    return ProteinClassificationNode(
        protein_class_id=protein_class_id,
        parent_id=_coerce_int(row.get("parent_id")),
        class_level=_coerce_int(row.get("class_level")),
        pref_name=_coerce_str(row.get("pref_name")),
        protein_class_desc=_coerce_str(row.get("protein_class_desc")),
        replaced_by=_coerce_int(row.get("replaced_by")),
    )


def _component_leaf_ids_from_row(
    row: Mapping[str, object],
) -> tuple[int | None, tuple[int, ...]]:
    component_id = _coerce_int(row.get("component_id"))
    if component_id is None or component_id < 1:
        return None, ()
    leaf_ids = _leaf_ids_from_value(row.get("protein_classification_ids"))
    if not leaf_ids:
        leaf_ids = _leaf_ids_from_forensic_value(row.get("protein_classifications"))
    return component_id, leaf_ids


def _leaf_ids_from_value(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
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
        return _coerce_int_tuple(loaded)
    return _coerce_int_tuple(value)


def _leaf_ids_from_forensic_value(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    loaded = _load_json_if_needed(value)
    if not isinstance(loaded, list):
        return ()
    leaf_ids: list[int] = []
    for item in loaded:
        if isinstance(item, Mapping):
            leaf_id = _coerce_int(item.get("protein_classification_id"))
            if leaf_id is not None and leaf_id > 0:
                leaf_ids.append(leaf_id)
    return tuple(dict.fromkeys(leaf_ids))


def _load_json_if_needed(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProteinClassificationResolutionError(
            "protein_classifications must be canonical JSON"
        ) from exc


def _coerce_int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return ()
    coerced = [
        int_value
        for item in value
        if (int_value := _coerce_int(item)) is not None and int_value > 0
    ]
    return tuple(dict.fromkeys(coerced))


def _coerce_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _validated_class_level(
    node: ProteinClassificationNode,
    *,
    leaf_id: int,
) -> int:
    level = node.class_level
    if level is None:
        raise ProteinClassificationResolutionError(
            f"missing class_level in chain for protein_class_id={leaf_id}"
        )
    if level < 1:
        raise ProteinClassificationResolutionError(
            f"class_level must be >= 1 for protein_class_id={node.protein_class_id}"
        )
    if level > 6:
        raise ProteinClassificationResolutionError(
            f"class_level {level} exceeds supported provider range for protein_class_id={node.protein_class_id}"
        )
    return level


def _validate_contiguous_levels(
    levels: Mapping[int, ProteinClassLevel],
    *,
    leaf_id: int,
) -> None:
    if not levels:
        raise ProteinClassificationResolutionError(
            f"no L1-L5 levels resolved for protein_class_id={leaf_id}"
        )
    ordered_levels = sorted(levels)
    expected = list(range(1, max(ordered_levels) + 1))
    if ordered_levels != expected:
        raise ProteinClassificationResolutionError(
            f"broken protein classification chain for protein_class_id={leaf_id}"
        )
