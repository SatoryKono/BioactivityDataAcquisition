"""Ratchet and unit coverage for AUD-002 targeted-apply anchors extract (#10526)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import apply_anchors
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
ANCHORS = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "apply_anchors.py"
# Line count on origin/main after the verification slice (#10650).
_CORE_LOC_BEFORE_ANCHORS_SLICE = 16081


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_apply_anchors_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    anchors_text = ANCHORS.read_text(encoding="utf-8")
    assert "def _targeted_apply_required_anchor_labels(" not in core_text
    assert "def _ensure_targeted_apply_prerequisites(" not in core_text
    assert "def sync_snapshot(" in core_text
    assert "def _targeted_apply_required_anchor_labels(" in anchors_text
    assert (
        _core._ensure_targeted_apply_prerequisites
        is apply_anchors._ensure_targeted_apply_prerequisites
    )
    assert _loc(CORE) < _CORE_LOC_BEFORE_ANCHORS_SLICE
    assert _loc(ANCHORS) < 500


def test_required_labels_and_external_keys() -> None:
    snapshot = _core.GraphSnapshot()
    src = snapshot.add_node("pipeline_surface", "chembl")
    dst = NodeKey("module_surface", "src/missing.py")
    snapshot.add_relation(src, "RUNS_VIA", dst)
    assert apply_anchors._targeted_apply_required_anchor_labels(snapshot) == (
        "module_surface",
    )
    assert apply_anchors._targeted_apply_external_anchor_keys(snapshot) == (dst,)
    assert apply_anchors._missing_anchor_labels(("a", "b"), {"a": 1, "b": 0}) == ["b"]
    assert "missing or empty: `a`" in apply_anchors._missing_anchor_labels_message(
        "targeted sync", ["a"]
    )
    msg = apply_anchors._missing_anchor_keys_message("targeted sync", (dst,))
    assert "`module_surface:src/missing.py`" in msg


def test_ensure_prerequisites_raises_when_labels_missing() -> None:
    snapshot = _core.GraphSnapshot()
    src = snapshot.add_node("pipeline_surface", "chembl")
    snapshot.add_relation(src, "RUNS_VIA", NodeKey("module_surface", "src/missing.py"))
    client = MagicMock()
    client.query.return_value = [{"label": "module_surface", "count": 0}]
    with pytest.raises(RuntimeError, match="pre-existing managed anchor labels"):
        apply_anchors._ensure_targeted_apply_prerequisites(
            client, snapshot, mode_description="targeted sync"
        )


def test_anchor_count_rows_and_empty_missing_keys() -> None:
    rows = [
        {"label": "module_surface", "name": "a.py", "count": 2},
        {"label": "skip", "name": "b.py", "count": "x"},
    ]
    counts = apply_anchors._anchor_count_rows(rows)
    assert counts[NodeKey("module_surface", "a.py")] == 2
    assert (
        apply_anchors._missing_managed_anchor_keys(MagicMock(), (), context="x") == ()
    )
