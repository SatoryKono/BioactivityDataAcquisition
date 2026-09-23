"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_mapping
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.classify_silver_storage_fields import _composite_group_fields
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _add_composite_output_layers,
)
from memory.graph.sync_pkg.composite_group_field_entries import (
    _add_composite_seed_surface,
)
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _add_composite_dependency_surfaces,
)
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.graph_contexts import CompositeOutputConfig
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    _composite_storage_context,
    _link_composite_layer_promotions,
)
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_composite_storage_data_surfaces",
    "_index_storage_layer_fields",
]


def _index_storage_layer_fields(
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    for layer_name, surface in layer_nodes.items():
        schema_fields_by_storage[surface.name] = field_nodes_by_layer.get(
            layer_name, {}
        )


def _add_composite_storage_data_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob(YAML_FILE_GLOB)):
        payload = _read_yaml(composite_path)
        context, composite_payload, dependencies = _composite_storage_context(
            root,
            composite_path,
            payload,
            today=today,
        )
        has_dependency_pipelines = isinstance(dependencies, list) and any(
            isinstance(item, dict) for item in dependencies
        )
        source_storage_refs = _add_composite_seed_surface(
            snapshot,
            project,
            context,
            composite_payload=composite_payload,
            has_dependency_pipelines=has_dependency_pipelines,
        )
        source_storage_refs.extend(
            _add_composite_dependency_surfaces(
                snapshot,
                project,
                context,
                dependencies=dependencies,
            )
        )
        merge_payload = _as_mapping(composite_payload.get("merge"))
        output_payload = _as_mapping(merge_payload.get("output"))
        layer_nodes, field_nodes_by_layer = _add_composite_output_layers(
            snapshot,
            project,
            context,
            CompositeOutputConfig(
                merge_payload=merge_payload,
                output_payload=output_payload,
                group_fields=_composite_group_fields(merge_payload),
                source_storage_refs=source_storage_refs,
                schema_fields_by_storage=schema_fields_by_storage,
            ),
        )
        _index_storage_layer_fields(
            schema_fields_by_storage, layer_nodes, field_nodes_by_layer
        )
        _link_composite_layer_promotions(snapshot, layer_nodes, field_nodes_by_layer)
