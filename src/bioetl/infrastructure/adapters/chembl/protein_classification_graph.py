"""ChEMBL protein classification graph adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from bioetl.domain.ports import ProteinClassificationPort
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
    ProteinClassLevel,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_coerce import (
    validate_contiguous_levels,
    validated_class_level,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_node import (
    ProteinClassificationNode,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_rows import (
    component_leaf_ids_from_row,
    node_from_row,
)

__all__ = [
    "ChEMBLProteinClassificationGraph",
    "ProteinClassificationNode",
]


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
            for node in (node_from_row(row) for row in protein_class_rows)
            if node is not None
        }
        component_leaf_ids = {
            component_id: leaf_ids
            for component_id, leaf_ids in (
                component_leaf_ids_from_row(row) for row in target_component_rows
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
        path = self._walk_path(resolved_leaf_id)
        levels = {
            level_number: level for level_number, level in path if level_number <= 5
        }
        hierarchy = ProteinClassHierarchy(
            l1=levels.get(1, ProteinClassLevel.empty()),
            l2=levels.get(2, ProteinClassLevel.empty()),
            l3=levels.get(3, ProteinClassLevel.empty()),
            l4=levels.get(4, ProteinClassLevel.empty()),
            l5=levels.get(5, ProteinClassLevel.empty()),
            leaf_id=resolved_leaf_id,
            path=tuple(level for _level_number, level in path),
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

    def _walk_path(self, leaf_id: int) -> tuple[tuple[int, ProteinClassLevel], ...]:
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
            level = validated_class_level(node, leaf_id=leaf_id)
            if level in levels:
                raise ProteinClassificationResolutionError(
                    f"duplicate class_level {level} for protein_class_id={leaf_id}"
                )
            levels[level] = ProteinClassLevel(
                id=node.protein_class_id,
                name=node.pref_name,
                desc=node.protein_class_desc,
            )
            current_id = node.parent_id

        validate_contiguous_levels(levels, leaf_id=leaf_id)
        return tuple(sorted(levels.items()))

    def _node(self, protein_class_id: int) -> ProteinClassificationNode:
        node = self._nodes.get(protein_class_id)
        if node is None:
            raise ProteinClassificationResolutionError(
                f"missing protein classification node {protein_class_id}"
            )
        return node
