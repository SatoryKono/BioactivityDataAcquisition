"""Small helpers for protein classification resolution."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.chembl.protein_classification import ProteinClassHierarchy


def json_array(values: Iterable[object]) -> str:
    """Return a stable JSON array for publication in scalar contract fields."""
    return json.dumps(tuple(values), ensure_ascii=False, separators=(",", ":"))


def record_component_hierarchies(
    *,
    by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]],
    component_id: int,
    hierarchies: tuple[ProteinClassHierarchy, ...],
) -> None:
    """Keep the lowest component ID for each resolved classification leaf."""
    for hierarchy in hierarchies:
        current = by_leaf_id.get(hierarchy.leaf_id)
        if current is None or component_id < current[0]:
            by_leaf_id[hierarchy.leaf_id] = (component_id, hierarchy)
