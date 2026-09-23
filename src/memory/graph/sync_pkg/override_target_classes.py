"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import (
    CallableDescriptor,
    DuplicateFamilyConfig,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_duplication_family_by_name",
    "_override_target_classes",
]


def _override_target_classes(
    snapshot: GraphSnapshot,
    member: CallableDescriptor,
) -> set[NodeKey]:
    candidate_set = {
        relation.target
        for relation in snapshot.relations.values()
        if relation.source == member.node_key
        and relation.relation_type == "OVERRIDES"
        and relation.target.label == "method_surface"
    }
    return {
        NodeKey("class_surface", target.name.rsplit(".", 1)[0])
        for target in candidate_set
    }


def _duplication_family_by_name(
    config: dict[str, object],
    family_name: str,
) -> DuplicateFamilyConfig | None:
    return next(
        (
            item
            for item in _as_iterable(config.get("families"))
            if isinstance(item, DuplicateFamilyConfig) and item.name == family_name
        ),
        None,
    )
