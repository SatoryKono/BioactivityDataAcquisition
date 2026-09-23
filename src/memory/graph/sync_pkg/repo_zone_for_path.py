"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.walk_repo_zone_root import _walk_repo_zone_root

__all__ = [
    "_add_repo_zone_file_structure",
    "_repo_zone_for_path",
]


def _repo_zone_for_path(
    source_path_value: str, zone_roots: dict[str, tuple[str, ...]]
) -> str | None:
    return next(
        (
            zone_name
            for zone_name, relative_roots in zone_roots.items()
            if any(
                source_path_value == zone_root
                or source_path_value.startswith(f"{zone_root}/")
                for zone_root in relative_roots
            )
        ),
        None,
    )


def _add_repo_zone_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
    zone = snapshot.add_node(
        "repo_zone",
        zone_name,
        summary=f"Primary repository zone `{zone_name}`.",
        source_kind="file_structure_zone",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_REPO_ZONE", zone, provenance="file_structure")

    for relative_root in relative_roots:
        _walk_repo_zone_root(
            snapshot,
            root,
            project,
            zone,
            today,
            zone_name=zone_name,
            relative_root=relative_root,
            config=config,
        )
