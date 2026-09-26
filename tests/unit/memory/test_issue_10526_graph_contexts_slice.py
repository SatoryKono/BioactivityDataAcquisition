"""Ratchet and unit coverage for AUD-002 graph context extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import graph_contexts
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
CTX = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "graph_contexts.py"
_CORE_LOC_BEFORE = 15317


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_graph_contexts_own_models_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    ctx_text = CTX.read_text(encoding="utf-8")
    assert "class WorkflowContext" not in core_text
    assert "class ComplexityAnalysisContext" not in core_text
    assert "class WorkflowContext" in ctx_text
    assert _core.WorkflowContext is graph_contexts.WorkflowContext
    assert _core.DuplicateFamilyConfig is graph_contexts.DuplicateFamilyConfig
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(CTX) < 500


def test_surface_relation_indexes_type_roundtrip() -> None:
    snapshot = GraphSnapshot()
    src = snapshot.add_node("module_surface", "src/a.py")
    dst = snapshot.add_node("class_surface", "A")
    snapshot.add_relation(src, "DECLARES", dst)
    indexes = graph_contexts.SurfaceRelationIndexes(
        incoming={dst: list(snapshot.relations.values())},
        outgoing={src: list(snapshot.relations.values())},
        declared_children={src: [dst]},
    )
    assert indexes.declared_children[NodeKey("module_surface", "src/a.py")] == [dst]
