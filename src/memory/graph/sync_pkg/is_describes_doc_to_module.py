"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphRelation, GraphSnapshot

__all__ = [
    "_add_reverse_module_doc_edges",
    "_collect_artifact_source_surfaces",
    "_is_describes_doc_to_module",
]


def _is_describes_doc_to_module(relation: GraphRelation) -> bool:
    return (
        relation.relation_type == "DESCRIBES"
        and relation.source.label
        in {"doc_source_surface", "doc_artifact", "policy_surface"}
        and relation.target.label == "module_surface"
    )


def _collect_artifact_source_surfaces(
    snapshot: GraphSnapshot,
) -> dict[NodeKey, list[NodeKey]]:
    artifact_sources: dict[NodeKey, list[NodeKey]] = {}
    for relation in tuple(snapshot.relations.values()):
        if relation.relation_type != "BACKED_BY":
            continue
        if relation.source.label != "doc_source_surface":
            continue
        if relation.target.label != "doc_artifact":
            continue
        artifact_sources.setdefault(relation.target, []).append(relation.source)
    return artifact_sources


def _add_reverse_module_doc_edges(snapshot: GraphSnapshot) -> None:
    for relation in tuple(snapshot.relations.values()):
        if not _is_describes_doc_to_module(relation):
            continue
        snapshot.add_relation(
            relation.target,
            "DESCRIBED_IN",
            relation.source,
            provenance="docs_code_drift_reverse",
            confidence=relation.properties.get("confidence"),
        )

    artifact_sources = _collect_artifact_source_surfaces(snapshot)
    for relation in tuple(snapshot.relations.values()):
        if relation.relation_type != "DESCRIBED_IN":
            continue
        if relation.source.label != "module_surface":
            continue
        if relation.target.label != "doc_artifact":
            continue
        for source_surface in artifact_sources.get(relation.target, ()):
            snapshot.add_relation(
                relation.source,
                "DESCRIBED_IN",
                source_surface,
                provenance="docs_code_drift_curated_source",
                confidence=relation.properties.get("confidence"),
            )
