"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_pipeline_test_artifact",
    "_test_artifact_key",
]


def _test_artifact_key(test_path: str) -> NodeKey:
    return NodeKey("test_artifact", test_path)


def _link_pipeline_test_artifact(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    snapshot.add_relation(
        pipeline_key, relation_type, artifact_key, provenance=provenance
    )
