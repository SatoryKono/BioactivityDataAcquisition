"""Ratchet coverage for AUD-002 snapshot_relation_requirements extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import snapshot_relation_requirements as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = (
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "snapshot_relation_requirements.py"
)
_CORE_LOC_BEFORE = 14232


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_snapshot_relation_requirements_owns_symbols_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "SNAPSHOT_RELATION_REQUIREMENTS =" not in core_text
    assert "SNAPSHOT_RELATION_REQUIREMENTS =" in MOD.read_text(encoding="utf-8")
    assert (
        _core.SNAPSHOT_RELATION_REQUIREMENTS is extracted.SNAPSHOT_RELATION_REQUIREMENTS
    )
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
