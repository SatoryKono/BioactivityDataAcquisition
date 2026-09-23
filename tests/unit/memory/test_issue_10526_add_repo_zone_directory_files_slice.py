"""Ratchet coverage for AUD-002 add_repo_zone_directory_files extract (#10526)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import add_repo_zone_directory_files as extracted

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = (
    ROOT / "src" / "memory" / "graph" / "sync_pkg" / "add_repo_zone_directory_files.py"
)
_CORE_LOC_BEFORE = 5576
_NAME = "_add_repo_zone_directory_files"
_OWNED = re.compile(
    rf"^(def {re.escape(_NAME)}\(|class {re.escape(_NAME)}\b|{re.escape(_NAME)}\s*[:=])",
    re.M,
)


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_add_repo_zone_directory_files_owns_symbols_and_shrinks_core() -> None:
    assert not _OWNED.search(CORE.read_text(encoding="utf-8"))
    assert _OWNED.search(MOD.read_text(encoding="utf-8"))
    assert getattr(_core, _NAME) is getattr(extracted, _NAME)
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500
