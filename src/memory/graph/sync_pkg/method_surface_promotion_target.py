"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import CallableDescriptor
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.override_target_classes import _override_target_classes

__all__ = [
    "_method_surface_promotion_target",
]


def _method_surface_promotion_target(
    snapshot: GraphSnapshot,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    if surface_kind != "method_surface" or not unique_members:
        return None
    method_name = unique_members[0].callable_name
    if not all(
        member.callable_name == method_name and member.parent_class
        for member in unique_members
    ):
        return None
    common_base_candidates: set[NodeKey] | None = None
    for member in unique_members:
        class_targets = _override_target_classes(snapshot, member)
        common_base_candidates = (
            class_targets
            if common_base_candidates is None
            else common_base_candidates & class_targets
        )
    if not common_base_candidates:
        return None
    return sorted(common_base_candidates, key=lambda item: item.name)[0]
