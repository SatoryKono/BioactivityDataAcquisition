"""Ratchet: AUD-002 god-module _core.py is below the 500-LOC closeout gate (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
SHARDS = (
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_reexport_a.py",
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_reexport_b.py",
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_reexport_c.py",
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core_reexport_d.py",
)


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_issue_10526_core_loc_below_closeout_gate() -> None:
    assert _loc(CORE) < 500
    for shard in SHARDS:
        assert shard.is_file()
        assert _loc(shard) < 500
    assert callable(_core.main)
    assert callable(_core.build_snapshot)
    assert "main" in _core.__all__
    assert "build_snapshot" in _core.__all__
    assert "_core_reexport_a" not in _core.__all__
