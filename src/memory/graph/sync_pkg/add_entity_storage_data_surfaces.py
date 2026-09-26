"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_entity_storage_layers import _add_entity_storage_layers
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.entity_storage_context import _entity_storage_context
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.index_storage_layer_fields import _index_storage_layer_fields
from memory.graph.sync_pkg.link_entity_storage_promotions import (
    _link_entity_storage_promotions,
)
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_entity_storage_data_surfaces",
]


def _add_entity_storage_data_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    base_payload: dict[str, object],
    base_sink: dict[str, object],
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
) -> None:
    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob(YAML_FILE_GLOB)):
        payload = _read_yaml(entity_path)
        context, pipeline_sink, quality_index = _entity_storage_context(
            root,
            entity_path,
            payload,
            today=today,
            base_payload=base_payload,
        )
        layer_nodes, field_nodes_by_layer = _add_entity_storage_layers(
            snapshot,
            project,
            context,
            payload=payload,
            base_sink=base_sink,
            pipeline_sink=pipeline_sink,
            quality_index=quality_index,
        )
        _index_storage_layer_fields(
            schema_fields_by_storage, layer_nodes, field_nodes_by_layer
        )
        _link_entity_storage_promotions(snapshot, layer_nodes, field_nodes_by_layer)
