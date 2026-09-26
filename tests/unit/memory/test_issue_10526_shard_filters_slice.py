"""Ratchet and unit coverage for AUD-002 shard filter extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import shard_filters
from memory.graph.sync_pkg._core_models import SnapshotSelection

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
SHARDS = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "shard_filters.py"
# Line count on origin/main after the GraphSnapshot slice (#10655).
_CORE_LOC_BEFORE_SHARD_FILTERS_SLICE = 15832


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_shard_filters_own_specs_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    shard_text = SHARDS.read_text(encoding="utf-8")
    assert "STORAGE_LAYER_FILTER: ShardFilterSpec" not in core_text
    assert "DOCS_DRIFT_FILTER: ShardFilterSpec" not in core_text
    assert "STORAGE_LAYER_FILTER: ShardFilterSpec" in shard_text
    assert _core.STORAGE_LAYER_FILTER is shard_filters.STORAGE_LAYER_FILTER
    assert _core.DOCS_DRIFT_FILTER is shard_filters.DOCS_DRIFT_FILTER
    assert _core.ShardFilterSpec is shard_filters.ShardFilterSpec
    assert _loc(CORE) < _CORE_LOC_BEFORE_SHARD_FILTERS_SLICE
    assert _loc(SHARDS) < 500


def test_storage_filter_labels_and_selected_helpers() -> None:
    labels, relation_specs = shard_filters.STORAGE_LAYER_FILTER
    assert "storage_surface" in labels
    assert "pipeline_surface" in labels
    assert any(spec[0] == "WRITES_TO" for spec in relation_specs)
    selected = _core._selected_shard_filters(SnapshotSelection(only_storage_layer=True))
    assert selected == (shard_filters.STORAGE_LAYER_FILTER,)
    docs = _core._selected_shard_filters(SnapshotSelection(only_docs_drift=True))
    assert docs == (shard_filters.DOCS_DRIFT_FILTER,)
    empty = _core._selected_shard_filters(SnapshotSelection())
    assert empty == ()
