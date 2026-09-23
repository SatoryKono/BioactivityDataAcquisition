"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_pipeline_name import (
    _add_composite_pipeline_surface,
)
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.entity_pipeline_identity import _add_entity_pipeline_surface
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_composite_pipeline_surfaces",
    "_add_entity_pipeline_surfaces",
]


def _add_entity_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob(YAML_FILE_GLOB)):
        _add_entity_pipeline_surface(
            snapshot,
            root,
            project,
            today,
            entity_path,
            contract_nodes=contract_nodes,
            adapter_nodes=adapter_nodes,
            pipeline_nodes=pipeline_nodes,
        )


def _add_composite_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob(YAML_FILE_GLOB)):
        _add_composite_pipeline_surface(
            snapshot,
            root,
            project,
            today,
            composite_path,
            pipeline_nodes=pipeline_nodes,
        )
