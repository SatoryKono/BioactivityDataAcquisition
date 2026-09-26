"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _add_duplication_cluster_node,
    _duplication_cluster_groups,
    _link_duplication_cluster_members,
    _link_same_shape_members,
)
from memory.graph.sync_pkg.graph_contexts import (
    CallableDescriptor,
    ClassDescriptor,
    DuplicateFamilyConfig,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.method_surface_promotion_target import (
    _method_surface_promotion_target,
)
from memory.graph.sync_pkg.override_target_classes import _duplication_family_by_name
from memory.graph.sync_pkg.resolved_base_classes import (
    _link_duplication_override_methods,
    _resolved_base_classes,
)

__all__ = [
    "_duplication_promotion_target",
    "_emit_duplication_clusters",
    "_link_duplication_override_relations",
]


def _link_duplication_override_relations(
    snapshot: GraphSnapshot,
    class_descriptors: dict[NodeKey, ClassDescriptor],
    class_name_index: dict[str, list[NodeKey]],
    class_method_index: dict[tuple[NodeKey, str], NodeKey],
) -> None:
    for class_descriptor in class_descriptors.values():
        for base_class in _resolved_base_classes(
            snapshot, class_descriptor, class_name_index
        ):
            snapshot.add_relation(
                class_descriptor.node_key,
                "DEPENDS_ON",
                base_class,
                provenance="code_duplication",
            )
            _link_duplication_override_methods(
                snapshot,
                class_descriptor=class_descriptor,
                base_class=base_class,
                class_method_index=class_method_index,
            )


def _duplication_promotion_target(
    snapshot: GraphSnapshot,
    config: dict[str, object],
    family_name: str,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    promotion_target = _method_surface_promotion_target(
        snapshot, surface_kind, unique_members
    )
    if promotion_target is not None:
        return promotion_target
    family = _duplication_family_by_name(config, family_name)
    if not isinstance(family, DuplicateFamilyConfig):
        return None
    for candidate in family.promotion_targets:
        if candidate in snapshot.nodes:
            return candidate
    return None


def _emit_duplication_clusters(
    snapshot: GraphSnapshot,
    project: NodeKey,
    *,
    today: str,
    config: dict[str, object],
    callable_descriptors: dict[NodeKey, CallableDescriptor],
    min_cluster_size: int,
    min_ast_nodes: int,
) -> None:
    for (family_name, surface_kind, shape_hash), members in _duplication_cluster_groups(
        callable_descriptors,
        min_ast_nodes=min_ast_nodes,
    ):
        if len(members) < min_cluster_size:
            continue
        unique_members = sorted(members, key=lambda item: item.node_key.name)
        cluster = _add_duplication_cluster_node(
            snapshot,
            today=today,
            family_name=family_name,
            surface_kind=surface_kind,
            shape_hash=shape_hash,
            unique_members=unique_members,
        )
        snapshot.add_relation(
            project, "CONTAINS", cluster, provenance="code_duplication"
        )
        _link_duplication_cluster_members(snapshot, cluster, unique_members)
        _link_same_shape_members(snapshot, unique_members)
        promotion_target = _duplication_promotion_target(
            snapshot, config, family_name, surface_kind, unique_members
        )
        if promotion_target is not None:
            snapshot.add_relation(
                cluster,
                "CAN_PROMOTE_TO",
                promotion_target,
                provenance="code_duplication",
            )
        package_family = NodeKey("package_family", unique_members[0].package_family)
        for relation in tuple(snapshot.relations.values()):
            if (
                relation.relation_type == "TESTS_PACKAGE_FAMILY"
                and relation.target == package_family
            ):
                snapshot.add_relation(
                    cluster,
                    "COVERED_BY_TEST",
                    relation.source,
                    provenance="code_duplication",
                )
