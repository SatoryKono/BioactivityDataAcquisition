"""Ratchet and unit coverage for AUD-002 file-structure extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import file_structure

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "file_structure.py"
_CORE_LOC_BEFORE = 14760


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_file_structure_owns_defaults_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "DEFAULT_FILE_STRUCTURE_REPO_ZONES:" not in core_text
    assert "def _file_structure_config(" not in core_text
    assert "def _file_structure_config(" in MOD.read_text(encoding="utf-8")
    assert _core._file_structure_config is file_structure._file_structure_config
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_default_zones_and_empty_mapping_fallback() -> None:
    assert "src" in file_structure.DEFAULT_FILE_STRUCTURE_REPO_ZONES
    assert "__pycache__" in file_structure.DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES
    config = file_structure._file_structure_config({})
    assert config["repo_zones"] is file_structure.DEFAULT_FILE_STRUCTURE_REPO_ZONES
    assert "docs/site" in config["excluded_prefixes"]
