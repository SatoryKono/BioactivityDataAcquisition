"""Ratchet coverage for AUD-002 walk_repo_zone_file_structure extract (#10526)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import walk_repo_zone_file_structure as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = (
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "walk_repo_zone_file_structure.py"
)
_CORE_LOC_BEFORE = 5553
_NAME = "_walk_repo_zone_file_structure"
_OWNED = re.compile(
    rf"^(def {re.escape(_NAME)}\(|class {re.escape(_NAME)}\b|{re.escape(_NAME)}\s*[:=])",
    re.M,
)


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_walk_repo_zone_file_structure_owns_symbols_and_shrinks_core() -> None:
    assert not _OWNED.search(CORE.read_text(encoding="utf-8"))
    assert _OWNED.search(MOD.read_text(encoding="utf-8"))
    assert getattr(_core, _NAME) is getattr(extracted, _NAME)
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
