"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _optional_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.entity_config_paths import (
    _add_entity_config_surface,
    _entity_config_paths,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_entity_config_surfaces",
    "_provider_config_properties",
]


def _provider_config_properties(
    source_payload: object,
) -> tuple[str | None, str | None]:
    auth_type = None
    pagination = None
    provider_config = source_payload
    if isinstance(provider_config, dict):
        provider_config = provider_config.get("provider_config", provider_config)
        if isinstance(provider_config, dict):
            auth_type = _optional_text(provider_config.get("auth_type"))
            pagination_data = provider_config.get("pagination")
            if isinstance(pagination_data, dict):
                pagination = _optional_text(pagination_data.get("strategy"))
    return auth_type, pagination


def _add_entity_config_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    provider_nodes: dict[str, NodeKey],
) -> dict[str, NodeKey]:
    entities_root = root / "configs" / "entities"
    entity_nodes: dict[str, NodeKey] = {}
    for entity_path in _entity_config_paths(entities_root):
        _add_entity_config_surface(
            snapshot,
            root,
            today,
            entity_path,
            provider_nodes=provider_nodes,
            entity_nodes=entity_nodes,
        )
    return entity_nodes
