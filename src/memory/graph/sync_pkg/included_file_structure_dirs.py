"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import _is_excluded_file_structure_path

__all__ = [
    "_add_repo_zone_directory_surface",
    "_included_file_structure_dirs",
]


def _included_file_structure_dirs(
    root: Path,
    current_path: Path,
    dirnames: list[str],
    config: dict[str, object],
) -> list[str]:
    return sorted(
        name
        for name in dirnames
        if not _is_excluded_file_structure_path(
            _rel_path(root, current_path / name), config
        )
    )


def _add_repo_zone_directory_surface(
    snapshot: GraphSnapshot,
    root: Path,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    current_path: Path,
    relative_dir: str,
) -> NodeKey:
    directory = snapshot.add_node(
        "directory_surface",
        relative_dir,
        summary=f"Primary repository directory `{relative_dir}`.",
        source_path=relative_dir,
        source_kind="file_structure_directory",
        repo_zone=zone_name,
        depth=len(Path(relative_dir).parts),
        is_primary=True,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    if relative_dir == relative_root:
        snapshot.add_relation(zone, "CONTAINS", directory, provenance="file_structure")
    else:
        parent_key = NodeKey("directory_surface", _rel_path(root, current_path.parent))
        snapshot.add_relation(
            parent_key, "CONTAINS", directory, provenance="file_structure"
        )
    return directory
