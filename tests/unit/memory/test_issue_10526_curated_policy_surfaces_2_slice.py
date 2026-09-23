"""Ratchet coverage for AUD-002 curated_policy_surfaces_2 extract (#10526)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import curated_policy_surfaces_2 as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "curated_policy_surfaces_2.py"
_CORE_LOC_BEFORE = 4590
_NAME = "_curated_policy_surfaces"
_OWNED = re.compile(
    rf"^(def {re.escape(_NAME)}\(|class {re.escape(_NAME)}\b|{re.escape(_NAME)}\s*[:=])",
    re.M,
)


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_curated_policy_surfaces_2_owns_symbols_and_shrinks_core() -> None:
    assert not _OWNED.search(CORE.read_text(encoding="utf-8"))
    assert _OWNED.search(MOD.read_text(encoding="utf-8"))
    assert getattr(_core, _NAME) is getattr(extracted, _NAME)
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
