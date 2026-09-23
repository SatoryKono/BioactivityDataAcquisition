"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_relation_backed_structure_for_relat import (
    _link_relation_backed_structure_for_relation,
)
from memory.graph.sync_pkg.python_paths import (
    _promoted_directory_hubs,
    _supplemental_directory_hubs_for_node,
)
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _relation_backed_file_structure_labels,
    _relation_backed_file_structure_types,
)
from memory.graph.sync_pkg.repo_zone_for_path import _repo_zone_for_path

__all__ = [
    "_link_relation_backed_file_structure",
    "_link_source_backed_file_node",
]


def _link_source_backed_file_node(
    snapshot: GraphSnapshot,
    root: Path,
    node_key: NodeKey,
    source_path: Path,
    *,
    source_path_value: str,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    parent_relative = _rel_path(root, source_path.parent)
    file_surface = snapshot.add_node(
        "file_surface",
        source_path_value,
        summary=f"Primary repository file `{source_path_value}`.",
        source_path=source_path_value,
        source_kind="file_structure_file",
        repo_zone=_repo_zone_for_path(source_path_value, zone_roots),
        suffix=source_path.suffix,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    directory_key = NodeKey("directory_surface", parent_relative)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "CONTAINS", file_surface, provenance="file_structure"
        )
        snapshot.add_relation(
            directory_key, "HOUSES", node_key, provenance="file_structure"
        )
    for promoted_hub in _promoted_directory_hubs(parent_relative, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", node_key, provenance="file_structure"
            )
    for supplemental_hub in _supplemental_directory_hubs_for_node(
        node_key, source_path_value
    ):
        hub_key = NodeKey("directory_surface", supplemental_hub)
        snapshot.add_relation(
            hub_key, "CONTAINS", file_surface, provenance="file_structure_promoted"
        )
        snapshot.add_relation(
            hub_key, "HOUSES", node_key, provenance="file_structure_promoted"
        )
    snapshot.add_relation(file_surface, "BACKS", node_key, provenance="file_structure")


def _link_relation_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    config: dict[str, object],
) -> None:
    relation_backed_types = _relation_backed_file_structure_types()
    file_backed_labels = _relation_backed_file_structure_labels()
    for relation in tuple(snapshot.relations.values()):
        _link_relation_backed_structure_for_relation(
            snapshot,
            root,
            relation,
            relation_backed_types=relation_backed_types,
            file_backed_labels=file_backed_labels,
            config=config,
        )
