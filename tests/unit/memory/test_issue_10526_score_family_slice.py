"""Ratchet and unit coverage for AUD-002 score/family extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import score_family
from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "score_family.py"
_CORE_LOC_BEFORE = 14931


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_score_family_owns_helpers_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _threshold_score(" not in core_text
    assert "def _family_for_path(" not in core_text
    assert "def _threshold_score(" in MOD.read_text(encoding="utf-8")
    assert _core._threshold_score is score_family._threshold_score
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_threshold_tags_and_family_match() -> None:
    assert score_family._threshold_score(6, medium=3, high=6) == 2
    assert score_family._presence_score(0) == 0
    assert "retry" in score_family._semantic_tags("src/a.py", "retry_request")
    family = DuplicateFamilyConfig(
        name="ports",
        roots=("src/bioetl/domain/ports",),
        package_family="domain",
        promotion_targets=(NodeKey("port_surface", "x"),),
        excluded_paths=("src/bioetl/domain/ports/skip.py",),
    )
    config = {"families": (family,)}
    assert (
        score_family._family_for_path("src/bioetl/domain/ports/http.py", config)
        is family
    )
    assert (
        score_family._family_for_path("src/bioetl/domain/ports/skip.py", config) is None
    )
