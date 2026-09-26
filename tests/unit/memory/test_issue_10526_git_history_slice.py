"""Ratchet and unit coverage for AUD-002 git history extract (#10526)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import git_history

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "git_history.py"
_CORE_LOC_BEFORE = 15111


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_git_history_owns_helpers_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    mod_text = MOD.read_text(encoding="utf-8")
    assert "def _git_last_commit_age_days(" not in core_text
    assert "def _parse_git_chunk_age_output(" not in core_text
    assert "def _git_last_commit_age_days(" in mod_text
    assert _core._parse_git_chunk_age_output is git_history._parse_git_chunk_age_output
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_parse_chunk_age_output() -> None:
    today = date(2026, 9, 23)
    output = "\n".join(
        (
            "__TS__1758500000",
            "src/a.py",
            "__TS__1758400000",
            "src/b.py",
        )
    )
    ages = git_history._parse_git_chunk_age_output(
        output, ["src/a.py", "src/b.py", "src/missing.py"], today
    )
    assert ages["src/missing.py"] is None
    assert ages["src/a.py"] is not None
    assert ages["src/b.py"] is not None
    assert ages["src/b.py"] >= ages["src/a.py"]
