"""Stable lineage fragment identity helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.lineage import LineageEdge, LineageNodeRef, LineageNodeType


def fragment_timestamp(*values: datetime | None) -> datetime:
    """Resolve one stable fragment timestamp."""
    for value in values:
        if value is not None:
            return value
    return current_utc_time()


def build_fragment_id(prefix: str, *parts: object) -> str:
    """Build a stable compact fragment identifier from semantic parts."""
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts if part is not None).encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}:{digest}"


def build_semantic_fragment_id(
    prefix: str,
    *,
    nodes: list[LineageNodeRef] | tuple[LineageNodeRef, ...],
    edges: list[LineageEdge] | tuple[LineageEdge, ...],
) -> str:
    """Build a fragment id from semantic topology only."""
    semantic_node_ids = sorted(
        node.node_id
        for node in nodes
        if node.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
    )
    semantic_edge_ids = sorted(
        ":".join(
            [
                edge.edge_type.value,
                edge.source.node_id,
                edge.target.node_id,
                json.dumps(edge.attributes, sort_keys=True, separators=(",", ":")),
            ]
        )
        for edge in edges
        if edge.source.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
        and edge.target.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
    )
    return build_fragment_id(prefix, *semantic_node_ids, *semantic_edge_ids)


def dedupe_nodes(nodes: list[LineageNodeRef]) -> tuple[LineageNodeRef, ...]:
    """Deduplicate nodes by canonical node identifier in stable content order."""
    unique: dict[str, LineageNodeRef] = {}
    for node in nodes:
        unique.setdefault(node.node_id, node)
    return tuple(unique[node_id] for node_id in sorted(unique))


__all__ = [
    "build_fragment_id",
    "build_semantic_fragment_id",
    "dedupe_nodes",
    "fragment_timestamp",
]
