"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_config_paths import (
    _add_composite_config_surface,
    _composite_config_paths,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_composite_config_surfaces",
    "_entity_config_identity",
]


def _entity_config_identity(
    entity_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, str, str]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline = payload.get("pipeline", {})
    pipeline_name = None
    pipeline_description = None
    if isinstance(pipeline, dict):
        pipeline_name = pipeline.get("pipeline_name")
        pipeline_description = pipeline.get("description")
    node_name = str(pipeline_name or f"{provider_name}_{entity_name}")
    summary = str(
        pipeline_description
        or f"Entity pipeline config for `{provider_name}/{entity_name}`."
    )
    return provider_name, entity_name, node_name, summary


def _add_composite_config_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entity_nodes: dict[str, NodeKey],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in _composite_config_paths(composites_root):
        _add_composite_config_surface(
            snapshot,
            root,
            project,
            today,
            composite_path,
            entity_nodes=entity_nodes,
        )
