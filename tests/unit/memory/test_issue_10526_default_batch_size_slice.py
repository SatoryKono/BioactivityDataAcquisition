"""Ratchet coverage for AUD-002 default_batch_size extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import default_batch_size as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "default_batch_size.py"
_CORE_LOC_BEFORE = 13690


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_default_batch_size_owns_symbols_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "DEFAULT_BATCH_SIZE =" not in core_text
    assert "DEFAULT_BATCH_SIZE =" in MOD.read_text(encoding="utf-8")
    assert _core.DEFAULT_BATCH_SIZE is extracted.DEFAULT_BATCH_SIZE
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
