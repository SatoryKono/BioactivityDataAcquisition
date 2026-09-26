"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _duplication_class_method_index,
)
from memory.graph.sync_pkg.collect_duplication_descriptors_for_modu import (
    _collect_duplication_descriptors_for_module,
)
from memory.graph.sync_pkg.duplication_analysis_config import (
    _duplication_analysis_config,
)
from memory.graph.sync_pkg.duplication_cluster_thresholds import (
    _duplication_cluster_thresholds,
)
from memory.graph.sync_pkg.graph_contexts import DuplicationExtractionContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_duplication_override_relations import (
    _emit_duplication_clusters,
    _link_duplication_override_relations,
)

__all__ = [
    "_extract_code_duplication_surfaces",
]


def _extract_code_duplication_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    config = _duplication_analysis_config(memory_mapping)
    if not bool(config.get("enabled", True)):
        return

    min_cluster_size, min_ast_nodes = _duplication_cluster_thresholds(config)
    extraction = DuplicationExtractionContext(
        snapshot=snapshot,
        root=root,
        today=today,
        config=config,
    )
    for module in tuple(snapshot.nodes.values()):
        if module.key.label != "module_surface":
            continue
        _collect_duplication_descriptors_for_module(extraction, module)

    class_method_index = _duplication_class_method_index(
        extraction.callable_descriptors
    )
    _link_duplication_override_relations(
        snapshot,
        extraction.class_descriptors,
        extraction.class_name_index,
        class_method_index,
    )
    _emit_duplication_clusters(
        snapshot,
        project,
        today=today,
        config=config,
        callable_descriptors=extraction.callable_descriptors,
        min_cluster_size=min_cluster_size,
        min_ast_nodes=min_ast_nodes,
    )
