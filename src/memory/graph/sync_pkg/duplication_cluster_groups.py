"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import CallableDescriptor
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_duplication_cluster_node",
    "_duplication_cluster_groups",
    "_link_duplication_cluster_members",
    "_link_same_shape_members",
]


def _duplication_cluster_groups(
    callable_descriptors: dict[NodeKey, CallableDescriptor],
    *,
    min_ast_nodes: int,
) -> tuple[tuple[tuple[str, str, str], list[CallableDescriptor]], ...]:
    grouped: dict[tuple[str, str, str], list[CallableDescriptor]] = {}
    for descriptor in callable_descriptors.values():
        if descriptor.ast_node_count < min_ast_nodes:
            continue
        grouped.setdefault(
            (
                descriptor.family_name,
                descriptor.surface_kind,
                descriptor.ast_shape_hash,
            ),
            [],
        ).append(descriptor)
    return tuple(sorted(grouped.items()))


def _add_duplication_cluster_node(
    snapshot: GraphSnapshot,
    *,
    today: str,
    family_name: str,
    surface_kind: str,
    shape_hash: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey:
    return snapshot.add_node(
        "duplication_cluster",
        f"{family_name}:{surface_kind}:{shape_hash[:12]}",
        summary=f"Potential duplicate logic cluster for `{family_name}` {surface_kind}.",
        source_kind="semantic_duplication_cluster",
        family_name=family_name,
        surface_kind=surface_kind,
        duplicate_count=len(unique_members),
        ast_shape_hash=shape_hash,
        semantic_tags=sorted(
            {tag for member in unique_members for tag in member.semantic_tags}
        ),
        promotion_score=round(min(0.99, 0.35 + (0.1 * len(unique_members))), 2),
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _link_duplication_cluster_members(
    snapshot: GraphSnapshot,
    cluster: NodeKey,
    unique_members: list[CallableDescriptor],
) -> None:
    for member in unique_members:
        snapshot.add_relation(
            cluster, "CONTAINS", member.node_key, provenance="code_duplication"
        )


def _link_same_shape_members(
    snapshot: GraphSnapshot,
    unique_members: list[CallableDescriptor],
) -> None:
    for index, left in enumerate(unique_members):
        for right in unique_members[index + 1 :]:
            snapshot.add_relation(
                left.node_key,
                "SAME_SHAPE_AS",
                right.node_key,
                provenance="code_duplication",
            )
            snapshot.add_relation(
                right.node_key,
                "SAME_SHAPE_AS",
                left.node_key,
                provenance="code_duplication",
            )
