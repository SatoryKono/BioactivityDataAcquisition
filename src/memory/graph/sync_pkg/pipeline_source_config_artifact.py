"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_pipeline_doc_artifacts",
    "_pipeline_doc_artifact_targets",
    "_pipeline_source_config_artifact",
]


def _pipeline_source_config_artifact(
    snapshot: GraphSnapshot, pipeline: NodeKey
) -> NodeKey:
    source_path = snapshot.nodes[pipeline].properties.get("source_path", "")
    return NodeKey("config_artifact", str(source_path))


def _pipeline_doc_artifact_targets(
    snapshot: GraphSnapshot,
    *,
    provider_name: str,
    entity_name: str,
) -> tuple[NodeKey, ...]:
    entity_dash = entity_name.replace("_", "-")
    candidates = (
        f"docs/04-reference/providers/{provider_name}/{entity_dash}.md",
        f"docs/04-reference/pipelines/{provider_name}-{entity_dash}.md",
    )
    glob_prefix = f"docs/04-reference/pipelines/{provider_name}/"
    glob_suffix = f"-{entity_dash}-spec.md"
    doc_keys = [
        NodeKey("doc_artifact", path)
        for path in candidates
        if NodeKey("doc_artifact", path) in snapshot.nodes
    ]
    doc_keys.extend(
        node.key
        for node in snapshot.nodes.values()
        if node.key.label == "doc_artifact"
        and node.key.name.startswith(glob_prefix)
        and node.key.name.endswith(glob_suffix)
    )
    return tuple(sorted(set(doc_keys), key=lambda key: key.name))


def _link_pipeline_doc_artifacts(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    doc_artifacts: tuple[NodeKey, ...],
    *,
    provenance: str,
) -> None:
    for doc_artifact in doc_artifacts:
        snapshot.add_relation(
            pipeline, "DESCRIBED_IN", doc_artifact, provenance=provenance
        )
