"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.graph_snapshot import GraphRelation, GraphSnapshot
from memory.graph.sync_pkg.python_paths import _is_excluded_file_structure_path
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _link_relation_backed_directory_housing,
    _relation_backed_parent_relative,
)

__all__ = [
    "_link_relation_backed_structure_for_relation",
]


def _link_relation_backed_structure_for_relation(
    snapshot: GraphSnapshot,
    root: Path,
    relation: GraphRelation,
    *,
    relation_backed_types: set[str],
    file_backed_labels: set[str],
    config: dict[str, object],
) -> None:
    if (
        relation.relation_type not in relation_backed_types
        or relation.target.label not in file_backed_labels
    ):
        return
    target_node = snapshot.nodes.get(relation.target)
    if target_node is None:
        return
    source_path_value = target_node.properties.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        return
    if _is_excluded_file_structure_path(source_path_value, config):
        return

    parent_relative = _relation_backed_parent_relative(root, source_path_value)
    if parent_relative is None:
        return
    _link_relation_backed_directory_housing(
        snapshot,
        relation.source,
        parent_relative=parent_relative,
        config=config,
    )
