"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_string_list
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_pipeline_normalization_modules",
    "_normalization_edge_config",
    "_pipeline_normalization_modules",
    "_pipeline_normalization_targets",
]


def _pipeline_normalization_targets(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[tuple[str, NodeKey, str, NodeKey], ...]:
    targets: list[tuple[str, NodeKey, str, NodeKey]] = []
    for pipeline_name, pipeline_key in pipeline_nodes.items():
        pipeline_node = snapshot.nodes.get(pipeline_key)
        if pipeline_node is None:
            continue
        pipeline_kind = str(pipeline_node.properties.get("pipeline_kind", "entity"))
        targets.append(
            (
                pipeline_name,
                pipeline_key,
                pipeline_kind,
                NodeKey("entity_config", pipeline_name),
            )
        )
    return tuple(targets)


def _normalization_edge_config(
    normalization_mapping: dict[str, object],
) -> tuple[str, str, list[str], list[str], dict[str, object]]:
    relation_type = str(normalization_mapping.get("relation_type", "DEPENDS_ON"))
    entity_relation_type = str(
        normalization_mapping.get("entity_relation_type", relation_type)
    )
    defaults = normalization_mapping.get("defaults")
    default_entity_modules: list[str] = []
    default_composite_modules: list[str] = []
    if isinstance(defaults, dict):
        entity_defaults = defaults.get("entity")
        composite_defaults = defaults.get("composite")
        if isinstance(entity_defaults, dict):
            default_entity_modules = _as_string_list(entity_defaults.get("modules"))
        if isinstance(composite_defaults, dict):
            default_composite_modules = _as_string_list(
                composite_defaults.get("modules")
            )
    pipeline_entries = normalization_mapping.get("pipelines")
    pipeline_overrides = pipeline_entries if isinstance(pipeline_entries, dict) else {}
    return (
        relation_type,
        entity_relation_type,
        default_entity_modules,
        default_composite_modules,
        pipeline_overrides,
    )


def _pipeline_normalization_modules(
    pipeline_name: str,
    pipeline_kind: str,
    pipeline_overrides: dict[str, object],
    default_entity_modules: list[str],
    default_composite_modules: list[str],
) -> list[str]:
    modules = list(
        default_entity_modules
        if pipeline_kind == "entity"
        else default_composite_modules
    )
    pipeline_payload = pipeline_overrides.get(pipeline_name)
    if isinstance(pipeline_payload, dict):
        modules.extend(_as_string_list(pipeline_payload.get("modules")))
    return modules


def _link_pipeline_normalization_modules(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    *,
    entity_key: NodeKey,
    pipeline_kind: str,
    modules: list[str],
    relation_type: str,
    entity_relation_type: str,
) -> None:
    seen_modules: set[str] = set()
    for module_path in modules:
        if module_path in seen_modules:
            continue
        seen_modules.add(module_path)
        module_key = NodeKey("module_surface", module_path)
        if module_key not in snapshot.nodes:
            continue
        snapshot.add_relation(
            pipeline_key, relation_type, module_key, provenance="impact_normalization"
        )
        if pipeline_kind == "entity" and entity_key in snapshot.nodes:
            snapshot.add_relation(
                entity_key,
                entity_relation_type,
                module_key,
                provenance="impact_normalization",
            )
