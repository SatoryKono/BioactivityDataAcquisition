"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_dependency_target import _link_config_artifact
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.entity_config_identity import _entity_config_identity
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_entity_config_surface",
    "_entity_config_paths",
]


def _entity_config_paths(entities_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(entities_root.rglob(YAML_FILE_GLOB)))


def _add_entity_config_surface(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    entity_path: Path,
    *,
    provider_nodes: dict[str, NodeKey],
    entity_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(entity_path)
    provider_name, entity_name, node_name, summary = _entity_config_identity(
        entity_path, payload
    )
    entity = snapshot.add_node(
        "entity_config",
        node_name,
        summary=summary,
        source_path=_rel_path(root, entity_path),
        source_kind="entity_config",
        provider=provider_name,
        entity=entity_name,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    entity_nodes[node_name] = entity
    provider = provider_nodes.get(provider_name)
    if provider is not None:
        snapshot.add_relation(provider, "DEFINES", entity, provenance="entity_config")
    _link_config_artifact(
        snapshot,
        entity,
        path=_rel_path(root, entity_path),
        summary=f"Entity config for `{provider_name}/{entity_name}`.",
        source_kind="entity_config",
        today=today,
        provenance="entity_config",
    )
