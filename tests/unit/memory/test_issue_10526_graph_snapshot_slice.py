"""Ratchet and unit coverage for AUD-002 GraphSnapshot extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import graph_snapshot
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
SNAP = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "graph_snapshot.py"
# Line count on origin/main after the anchors slice (#10653).
_CORE_LOC_BEFORE_SNAPSHOT_SLICE = 15953


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_graph_snapshot_owns_models_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    snap_text = SNAP.read_text(encoding="utf-8")
    assert "class GraphSnapshot" not in core_text
    assert "def snapshot_orphans(" not in core_text
    assert "class GraphSnapshot" in snap_text
    assert _core.GraphSnapshot is graph_snapshot.GraphSnapshot
    assert _core.snapshot_orphans is graph_snapshot.snapshot_orphans
    assert _loc(CORE) < _CORE_LOC_BEFORE_SNAPSHOT_SLICE
    assert _loc(SNAP) < 500


def test_add_node_relation_stats_and_to_dict() -> None:
    snapshot = graph_snapshot.GraphSnapshot()
    src = snapshot.add_node("pipeline_surface", "chembl", role="entity", skip=None)
    dst = snapshot.add_node("module_surface", "src/x.py")
    snapshot.add_relation(src, "RUNS_VIA", dst, provenance="unit")
    assert src == NodeKey("pipeline_surface", "chembl")
    assert snapshot.nodes[src].properties == {"role": "entity"}
    stats = snapshot.stats()
    assert stats["node_count"] == 2
    assert stats["relation_count"] == 1
    assert stats["labels"]["pipeline_surface"] == 1
    payload = snapshot.to_dict()
    names = [item["name"] for item in payload["nodes"]]
    assert names == ["src/x.py", "chembl"]
    assert payload["relations"][0]["type"] == "RUNS_VIA"


def test_snapshot_orphans_lists_degree_zero_nodes() -> None:
    snapshot = graph_snapshot.GraphSnapshot()
    connected = snapshot.add_node("pipeline_surface", "chembl")
    orphan = snapshot.add_node("module_surface", "src/orphan.py")
    snapshot.add_relation(
        connected, "RUNS_VIA", NodeKey("module_surface", "src/other.py")
    )
    assert graph_snapshot.snapshot_orphans(snapshot) == [orphan]
