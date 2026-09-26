"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.link_pipeline_test_suite import _link_pipeline_test_suite
from memory.graph.sync_pkg.test_artifact_key import (
    _link_pipeline_test_artifact,
    _test_artifact_key,
)

__all__ = [
    "_pipeline_test_linker",
    "_provider_pipeline_index_key",
]


def _provider_pipeline_index_key(node: GraphNode) -> str | None:
    if node.key.label != "pipeline_surface":
        return None
    provider = node.properties.get("provider")
    return provider if isinstance(provider, str) else None


def _pipeline_test_linker(
    snapshot: GraphSnapshot,
    relation_type: str,
) -> Callable[[NodeKey, str, str], None]:
    def link_test_target(
        pipeline_key: NodeKey, test_path: str, provenance: str
    ) -> None:
        artifact_key = _test_artifact_key(test_path)
        if artifact_key not in snapshot.nodes:
            return
        _link_pipeline_test_artifact(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )
        _link_pipeline_test_suite(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )

    return link_test_target
