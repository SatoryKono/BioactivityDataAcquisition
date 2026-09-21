"""Deterministic graph-level consistency helpers for operator lineage evidence."""

from __future__ import annotations

from bioetl.domain.lineage import LineageGraphFragment, LineageNodeRef


def conflicting_node_ids(
    fragments: tuple[LineageGraphFragment, ...],
) -> list[str]:
    """Reject contradictory definitions while allowing partial node references."""
    definitions: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    for fragment in fragments:
        nodes: list[LineageNodeRef] = list(fragment.nodes)
        for edge in fragment.edges:
            nodes.extend((edge.source, edge.target))
        for node in nodes:
            definition = node.to_dict()
            previous = definitions.setdefault(node.node_id, {})
            if _merge_definition(previous, definition):
                conflicts.add(node.node_id)
    return sorted(conflicts)


def _merge_definition(previous: dict[str, object], incoming: dict[str, object]) -> bool:
    """Merge known fields; absent and null reference fields carry no assertion."""
    conflict = False
    for key, value in incoming.items():
        if value is None:
            continue
        old = previous.get(key)
        if isinstance(value, dict) and (old is None or isinstance(old, dict)):
            nested = dict(old or {})
            conflict = _merge_definition(nested, value) or conflict
            previous[key] = nested
        elif old is not None and old != value:
            conflict = True
        else:
            previous[key] = value
    return conflict


def _adjacency(fragments: tuple[LineageGraphFragment, ...]) -> dict[str, set[str]]:
    """Index directed edges, including nodes with no outgoing edges."""
    adjacency: dict[str, set[str]] = {}
    for fragment in fragments:
        for edge in fragment.edges:
            adjacency.setdefault(edge.source.node_id, set()).add(edge.target.node_id)
            _ = adjacency.setdefault(edge.target.node_id, set())
    return adjacency


def cycle_nodes(fragments: tuple[LineageGraphFragment, ...]) -> list[str]:
    """Return the stable set of node ids involved in directed cycles."""
    adjacency = _adjacency(fragments)

    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    for candidate in sorted(adjacency):
        if candidate in visited:
            continue
        visiting.add(candidate)
        stack = [(candidate, iter(sorted(adjacency[candidate])))]
        found: set[str] = set()
        while stack:
            node_id, targets = stack[-1]
            target_id = next(targets, None)
            if target_id is None:
                stack.pop()
                visiting.remove(node_id)
                visited.add(node_id)
                if node_id in found and stack:
                    parent = stack[-1][0]
                    cycle.update({parent, node_id})
                    found.add(parent)
            elif target_id in visiting:
                cycle.update({node_id, target_id})
                found.add(node_id)
            elif target_id not in visited:
                visiting.add(target_id)
                stack.append((target_id, iter(sorted(adjacency[target_id]))))
    return sorted(cycle)


__all__ = ["conflicting_node_ids", "cycle_nodes"]
