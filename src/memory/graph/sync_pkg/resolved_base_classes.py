"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import ClassDescriptor
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_duplication_override_methods",
    "_resolved_base_classes",
]


def _resolved_base_classes(
    snapshot: GraphSnapshot,
    class_descriptor: ClassDescriptor,
    class_name_index: dict[str, list[NodeKey]],
) -> tuple[NodeKey, ...]:
    class_node = snapshot.nodes[class_descriptor.node_key]
    base_names = class_node.properties.get("base_names")
    if not isinstance(base_names, list):
        return ()
    resolved: list[NodeKey] = []
    for base_name in base_names:
        if not isinstance(base_name, str) or not base_name:
            continue
        base_candidates = class_name_index.get(base_name, [])
        if len(base_candidates) == 1:
            resolved.append(base_candidates[0])
    return tuple(resolved)


def _link_duplication_override_methods(
    snapshot: GraphSnapshot,
    *,
    class_descriptor: ClassDescriptor,
    base_class: NodeKey,
    class_method_index: dict[tuple[NodeKey, str], NodeKey],
) -> None:
    for method_name in class_descriptor.method_names:
        base_method = class_method_index.get((base_class, method_name))
        current_method = class_method_index.get(
            (class_descriptor.node_key, method_name)
        )
        if base_method is not None and current_method is not None:
            snapshot.add_relation(
                current_method, "OVERRIDES", base_method, provenance="code_duplication"
            )
