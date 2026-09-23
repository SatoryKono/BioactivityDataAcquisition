"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _link_pipeline_doc_artifacts,
    _pipeline_doc_artifact_targets,
)

__all__ = [
    "_add_pipeline_doc_edges",
]


def _add_pipeline_doc_edges(snapshot: GraphSnapshot) -> None:
    for node in tuple(snapshot.nodes.values()):
        if node.key.label != "pipeline_surface":
            continue
        pipeline_kind = node.properties.get("pipeline_kind")
        if pipeline_kind == "entity":
            provider_name = str(node.properties.get("provider") or "")
            entity_name = str(node.properties.get("entity") or "")
        elif pipeline_kind == "composite":
            provider_name = "composite"
            entity_name = node.key.name.removeprefix("composite_")
        else:
            continue
        if not provider_name or not entity_name:
            continue
        _link_pipeline_doc_artifacts(
            snapshot,
            node.key,
            _pipeline_doc_artifact_targets(
                snapshot,
                provider_name=provider_name,
                entity_name=entity_name,
            ),
            provenance="impact_pipeline_docs",
        )
