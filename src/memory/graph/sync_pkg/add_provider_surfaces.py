"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.curated_policy_surfaces_2 import (
    _add_policy_surface_entry,
    _curated_policy_surfaces,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.provider_config_paths import (
    _add_provider_surface,
    _provider_config_paths,
)

__all__ = [
    "_add_policy_surfaces",
    "_add_provider_surfaces",
]


def _add_provider_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> dict[str, NodeKey]:
    providers_root = root / "configs" / "providers"
    provider_nodes: dict[str, NodeKey] = {}
    for provider_path in _provider_config_paths(providers_root):
        _add_provider_surface(
            snapshot,
            root,
            project,
            today,
            provider_path,
            provider_nodes=provider_nodes,
        )
    return provider_nodes


def _add_policy_surfaces(
    snapshot: GraphSnapshot, _root: Path, project: NodeKey, today: str
) -> None:
    for policy_payload in _curated_policy_surfaces():
        _add_policy_surface_entry(snapshot, project, today, policy_payload)
