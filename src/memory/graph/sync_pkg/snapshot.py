"""Snapshot construction and file-structure traversal surface for graph sync."""

from __future__ import annotations

from memory.graph.sync_pkg._core import (
    GraphNode,
    GraphRelation,
    GraphSnapshot,
    NodeKey,
    _add_file_structure_surfaces,
    _walk_repo_zone_file_structure,
    _walk_repo_zone_root,
    build_snapshot,
    snapshot_invariant_issues,
    snapshot_orphans,
)

__all__ = [
    "GraphNode",
    "GraphRelation",
    "GraphSnapshot",
    "NodeKey",
    "_add_file_structure_surfaces",
    "_walk_repo_zone_file_structure",
    "_walk_repo_zone_root",
    "build_snapshot",
    "snapshot_invariant_issues",
    "snapshot_orphans",
]
