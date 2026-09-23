"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_repo_zone_file_surface import (
    _add_repo_zone_doc_artifact,
    _add_repo_zone_file_surface,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import _is_excluded_file_structure_path

__all__ = [
    "_add_repo_zone_directory_file",
]


def _add_repo_zone_directory_file(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    directory: NodeKey,
    current_path: Path,
    filename: str,
    today: str,
    *,
    zone_name: str,
    config: dict[str, object],
) -> None:
    file_path = current_path / filename
    relative_file = _rel_path(root, file_path)
    if _is_excluded_file_structure_path(relative_file, config):
        return
    file_surface = _add_repo_zone_file_surface(
        snapshot,
        directory,
        relative_file,
        today,
        zone_name=zone_name,
        filename=filename,
    )
    _add_repo_zone_doc_artifact(
        snapshot,
        project,
        file_surface,
        relative_file,
        today,
        zone_name=zone_name,
    )
