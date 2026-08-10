"""Deterministic graph-level consistency helpers for operator lineage evidence."""

from __future__ import annotations

from bioetl.domain.lineage import LineageGraphFragment, LineageNodeRef


def conflicting_node_ids(
    fragments: tuple[LineageGraphFragment, ...],
) -> list[str]:
    """Return node ids that have more than one persisted definition."""
    definitions: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    for fragment in fragments:
        nodes: list[LineageNodeRef] = list(fragment.nodes)
        for edge in fragment.edges:
            nodes.extend((edge.source, edge.target))
        for node in nodes:
            definition = node.to_dict()
            previous = definitions.setdefault(node.node_id, definition)
            if previous != definition:
                conflicts.add(node.node_id)
    return sorted(conflicts)


def cycle_nodes(fragments: tuple[LineageGraphFragment, ...]) -> list[str]:
    """Return the stable set of node ids involved in directed cycles."""
    adjacency: dict[str, set[str]] = {}
    for fragment in fragments:
        for edge in fragment.edges:
            adjacency.setdefault(edge.source.node_id, set()).add(edge.target.node_id)
            _ = adjacency.setdefault(edge.target.node_id, set())

    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            cycle.add(node_id)
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        found = False
        for target_id in sorted(adjacency.get(node_id, ())):
            if visit(target_id):
                cycle.update({node_id, target_id})
                found = True
        visiting.remove(node_id)
        visited.add(node_id)
        return found

    for candidate in sorted(adjacency):
        _ = visit(candidate)
    return sorted(cycle)


__all__ = ["conflicting_node_ids", "cycle_nodes"]
