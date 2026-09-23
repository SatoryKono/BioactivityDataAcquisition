"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.test_suite_name import (
    _link_test_artifact_scope,
    _test_suite_name,
)

__all__ = [
    "_add_test_artifact_surface",
    "_add_test_suite_surface",
]


def _add_test_suite_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    suite_dir: str,
    suite_name: str,
) -> None:
    suite = snapshot.add_node(
        "test_surface",
        suite_name,
        summary=f"`tests/{suite_dir}/` coverage surface.",
        source_path=f"tests/{suite_dir}",
        source_kind="test_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_TEST_SURFACE", suite, provenance="test_graph")


def _add_test_artifact_surface(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    test_path: Path,
) -> None:
    relative_path = _rel_path(root, test_path)
    parts = Path(relative_path).parts
    suite_name = _test_suite_name(parts)
    if suite_name is None:
        return
    suite_dir = parts[1]
    artifact = snapshot.add_node(
        "test_artifact",
        relative_path,
        summary=f"Test artifact `{relative_path}`.",
        source_path=relative_path,
        source_kind="test_artifact",
        suite=suite_dir,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        NodeKey("test_surface", suite_name),
        "CONTAINS",
        artifact,
        provenance="test_graph",
    )
    _link_test_artifact_scope(snapshot, artifact, parts)
