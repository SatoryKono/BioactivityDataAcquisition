"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _normalize_repo_relative_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import _promoted_directory_hubs

__all__ = [
    "_link_relation_backed_directory_housing",
    "_relation_backed_file_structure_labels",
    "_relation_backed_file_structure_types",
    "_relation_backed_parent_relative",
]


def _relation_backed_file_structure_types() -> set[str]:
    return {"BACKED_BY", "DESCRIBED_IN", "DEFINED_BY"}


def _relation_backed_file_structure_labels() -> set[str]:
    return {
        "doc_artifact",
        "config_artifact",
        "module_surface",
        "script_surface",
        "test_artifact",
    }


def _relation_backed_parent_relative(root: Path, source_path_value: str) -> str | None:
    normalized_path = _normalize_repo_relative_path(source_path_value)
    if not normalized_path:
        return None
    target_path = root / normalized_path
    if target_path.is_dir():
        return normalized_path
    # Relation-backed labels here are file-oriented. Prefer the lexical parent
    # after the directory check to avoid expensive repeated file stats during
    # snapshot assembly on large or partially materialized trees.
    return str(Path(normalized_path).parent)


def _link_relation_backed_directory_housing(
    snapshot: GraphSnapshot,
    source: NodeKey,
    *,
    parent_relative: str,
    config: dict[str, object],
) -> None:
    directory_key = NodeKey("directory_surface", parent_relative)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "HOUSES", source, provenance="file_structure_inferred"
        )
    for promoted_hub in _promoted_directory_hubs(parent_relative, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", source, provenance="file_structure_inferred"
            )
