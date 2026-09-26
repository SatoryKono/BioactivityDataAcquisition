"""Ratchet and unit coverage for AUD-002 analysis source extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import analysis_source
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "analysis_source.py"
_CORE_LOC_BEFORE = 15195


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_analysis_source_owns_helpers_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    mod_text = MOD.read_text(encoding="utf-8")
    assert "def _build_surface_relation_indexes(" not in core_text
    assert "def _read_analysis_source_text(" not in core_text
    assert "def _build_surface_relation_indexes(" in mod_text
    assert (
        _core._build_surface_relation_indexes
        is analysis_source._build_surface_relation_indexes
    )
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_indexes_and_posix_source_read(tmp_path: Path) -> None:
    snapshot = GraphSnapshot()
    src = snapshot.add_node("module_surface", "src/a.py")
    dst = snapshot.add_node("class_surface", "A")
    snapshot.add_relation(src, "DECLARES", dst)
    indexes = analysis_source._build_surface_relation_indexes(snapshot)
    assert indexes.declared_children[src] == [dst]
    path = tmp_path / "sample.py"
    path.write_text("HELLO\n", encoding="utf-8")
    assert (
        analysis_source._read_analysis_source_text(path, os_name="posix") == "HELLO\n"
    )
    assert (
        analysis_source._analysis_read_source_text(tmp_path, "sample.py", {})
        == "hello\n"
    )
