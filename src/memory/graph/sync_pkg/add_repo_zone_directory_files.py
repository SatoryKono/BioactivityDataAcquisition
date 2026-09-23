"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_repo_zone_directory_file import (
    _add_repo_zone_directory_file,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_repo_zone_directory_files",
]


def _add_repo_zone_directory_files(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    directory: NodeKey,
    current_path: Path,
    filenames: list[str],
    today: str,
    *,
    zone_name: str,
    config: dict[str, object],
) -> None:
    for filename in sorted(filenames):
        _add_repo_zone_directory_file(
            snapshot,
            root,
            project,
            directory,
            current_path,
            filename,
            today,
            zone_name=zone_name,
            config=config,
        )
