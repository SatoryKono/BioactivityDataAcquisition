"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import _promoted_directory_hubs

__all__ = [
    "_link_source_backed_directory_structure",
    "_source_backed_file_structure_labels",
    "_source_backed_path_kind",
]


def _source_backed_path_kind(
    snapshot: GraphSnapshot,
    source_path_value: str,
    path_kind_cache: dict[str, str | None],
) -> str | None:
    if source_path_value in path_kind_cache:
        return path_kind_cache[source_path_value]

    if NodeKey("directory_surface", source_path_value) in snapshot.nodes:
        path_kind_cache[source_path_value] = "directory"
    elif NodeKey("file_surface", source_path_value) in snapshot.nodes:
        path_kind_cache[source_path_value] = "file"
    else:
        path_kind_cache[source_path_value] = None
    return path_kind_cache[source_path_value]


def _source_backed_file_structure_labels() -> set[str]:
    return {
        "layer_family",
        "package_family",
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
        "doc_source_surface",
        "doc_artifact",
        "policy_surface",
        "provider_surface",
        "entity_config",
        "composite_config",
        "config_artifact",
        "dashboard_surface",
        "script_surface",
        "test_surface",
        "test_artifact",
        "pipeline_surface",
        "contract_surface",
        "alert_surface",
        "runtime_evidence_surface",
        "workflow_surface",
        "workflow_job_surface",
    }


def _link_source_backed_directory_structure(
    snapshot: GraphSnapshot,
    node_key: NodeKey,
    *,
    source_path_value: str,
    config: dict[str, object],
) -> None:
    directory_key = NodeKey("directory_surface", source_path_value)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "HOUSES", node_key, provenance="file_structure"
        )
    for promoted_hub in _promoted_directory_hubs(source_path_value, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", node_key, provenance="file_structure"
            )
