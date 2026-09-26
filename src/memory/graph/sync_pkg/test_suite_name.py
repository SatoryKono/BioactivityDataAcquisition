"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import KNOWN_LAYERS, TEST_SURFACES
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_test_artifact_scope",
    "_test_suite_name",
]


def _test_suite_name(parts: tuple[str, ...]) -> str | None:
    if len(parts) < 2:
        return None
    suite_dir = parts[1]
    return TEST_SURFACES.get(suite_dir)


def _link_test_artifact_scope(
    snapshot: GraphSnapshot, artifact: NodeKey, parts: tuple[str, ...]
) -> None:
    layer_name = parts[2] if len(parts) > 2 and parts[2] in KNOWN_LAYERS else None
    if layer_name is None:
        return
    snapshot.add_relation(
        artifact,
        "TESTS_LAYER",
        NodeKey("layer_family", layer_name),
        provenance="test_graph",
    )
    if len(parts) <= 4:
        return
    family_key = NodeKey("package_family", f"{layer_name}/{parts[3]}")
    if family_key in snapshot.nodes:
        snapshot.add_relation(
            artifact,
            "TESTS_PACKAGE_FAMILY",
            family_key,
            provenance="test_graph",
        )
