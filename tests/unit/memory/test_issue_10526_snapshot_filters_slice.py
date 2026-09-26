"""Ratchet and unit coverage for AUD-002 snapshot filter extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import snapshot_filters
from memory.graph.sync_pkg._core_models import SnapshotSelection
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.shard_filters import DOCS_DRIFT_FILTER

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
FILTERS = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "snapshot_filters.py"
# Line count on origin/main after the shard-filters slice (#10657).
_CORE_LOC_BEFORE_SNAPSHOT_FILTERS_SLICE = 15507


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_snapshot_filters_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    filter_text = FILTERS.read_text(encoding="utf-8")
    assert "def _filtered_snapshot(" not in core_text
    assert "def _selected_shard_filters(" not in core_text
    assert "RETIREMENT_NODE_LABELS: tuple" not in core_text
    assert "def _filtered_snapshot(" in filter_text
    assert _core._filtered_snapshot is snapshot_filters._filtered_snapshot
    assert _core.RETIREMENT_NODE_LABELS is snapshot_filters.RETIREMENT_NODE_LABELS
    assert _loc(CORE) < _CORE_LOC_BEFORE_SNAPSHOT_FILTERS_SLICE
    assert _loc(FILTERS) < 500


def test_filtered_snapshot_keeps_storage_shard_nodes() -> None:
    snapshot = GraphSnapshot()
    project = snapshot.add_node("project", "bioetl")
    storage = snapshot.add_node("storage_surface", "chembl.activity")
    module = snapshot.add_node("module_surface", "src/x.py")
    snapshot.add_relation(project, "HAS_STORAGE_SURFACE", storage)
    snapshot.add_relation(module, "DESCRIBES", storage)
    filtered = snapshot_filters._filtered_snapshot(
        snapshot, SnapshotSelection(only_storage_layer=True)
    )
    assert project in filtered.nodes
    assert storage in filtered.nodes
    assert module not in filtered.nodes
    assert (project, "HAS_STORAGE_SURFACE", storage) in filtered.relations


def test_label_scope_and_legacy_kwargs() -> None:
    snapshot = GraphSnapshot()
    kept = snapshot.add_node("module_surface", "src/kept.py")
    snapshot.add_node("pipeline_surface", "chembl")
    filtered = snapshot_filters._filtered_snapshot(
        snapshot, only_labels=["module_surface"]
    )
    assert list(filtered.nodes) == [kept]
    resolved = snapshot_filters._resolved_snapshot_selection(
        None, {"only_docs_drift": True}
    )
    assert resolved.only_docs_drift is True
    assert snapshot_filters._selected_shard_filters(resolved) == (DOCS_DRIFT_FILTER,)
