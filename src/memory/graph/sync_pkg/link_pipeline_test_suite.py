"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_test_suite_name import _pipeline_test_suite_name

__all__ = [
    "_link_pipeline_test_suite",
]


def _link_pipeline_test_suite(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    suite_name = _pipeline_test_suite_name(snapshot, artifact_key)
    if suite_name is None:
        return
    snapshot.add_relation(
        pipeline_key,
        relation_type,
        NodeKey("test_surface", suite_name),
        provenance=provenance,
    )
