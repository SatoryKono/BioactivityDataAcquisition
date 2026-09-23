"""Ratchet coverage for AUD-002 complexity_marker_buckets extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import complexity_marker_buckets as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "complexity_marker_buckets.py"
_CORE_LOC_BEFORE = 13831


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_complexity_marker_buckets_owns_symbols_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _complexity_marker_buckets(" not in core_text
    assert "def _complexity_marker_buckets(" in MOD.read_text(encoding="utf-8")
    assert _core._complexity_marker_buckets is extracted._complexity_marker_buckets
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
