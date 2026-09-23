"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_test_suite_surface import (
    _add_test_artifact_surface,
    _add_test_suite_surface,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _composite_config_dependency_entries,
    _link_composite_dependency,
    _link_composite_seed_dependency,
)
from memory.graph.sync_pkg.default_batch_size import TEST_SURFACES
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_test_graph",
    "_link_composite_config_dependencies",
]


def _link_composite_config_dependencies(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    composite_payload: object,
    *,
    seed_pipeline: str | None,
    entity_nodes: dict[str, NodeKey],
) -> None:
    _link_composite_seed_dependency(
        snapshot, composite_node, seed_pipeline=seed_pipeline, entity_nodes=entity_nodes
    )
    for dependency in _composite_config_dependency_entries(composite_payload):
        _link_composite_dependency(snapshot, composite_node, dependency, entity_nodes)


def _add_test_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    tests_root = root / "tests"
    for suite_dir, suite_name in TEST_SURFACES.items():
        _add_test_suite_surface(
            snapshot, project, today, suite_dir=suite_dir, suite_name=suite_name
        )

    for test_path in sorted(tests_root.rglob("test_*.py")):
        _add_test_artifact_surface(snapshot, root, today, test_path)
