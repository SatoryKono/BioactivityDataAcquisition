"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_dependency_target import _link_config_artifact
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_composite_config_dependencies import (
    _link_composite_config_dependencies,
)
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_composite_config_surface",
    "_composite_config_identity",
    "_composite_config_paths",
]


def _composite_config_paths(composites_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(composites_root.glob(YAML_FILE_GLOB)))


def _composite_config_identity(
    composite_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, object, str | None]:
    composite_payload = payload.get("composite", {})
    composite_name = composite_path.stem
    summary = f"Composite pipeline config `{composite_name}`."
    seed_pipeline = None
    if isinstance(composite_payload, dict):
        composite_name = str(composite_payload.get("name", composite_name))
        summary = f"Composite pipeline config `{composite_name}`."
        seed = composite_payload.get("seed")
        if isinstance(seed, dict):
            seed_pipeline = seed.get("pipeline")
    return composite_name, summary, composite_payload, seed_pipeline


def _add_composite_config_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    composite_path: Path,
    *,
    entity_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(composite_path)
    composite_name, summary, composite_payload, seed_pipeline = (
        _composite_config_identity(
            composite_path,
            payload,
        )
    )
    composite_node = snapshot.add_node(
        "composite_config",
        composite_name,
        summary=summary,
        source_path=_rel_path(root, composite_path),
        source_kind="composite_config",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_COMPOSITE", composite_node, provenance="composite_config"
    )
    _link_config_artifact(
        snapshot,
        composite_node,
        path=_rel_path(root, composite_path),
        summary=summary,
        source_kind="composite_config",
        today=today,
        provenance="composite_config",
    )
    _link_composite_config_dependencies(
        snapshot,
        composite_node,
        composite_payload,
        seed_pipeline=seed_pipeline,
        entity_nodes=entity_nodes,
    )
