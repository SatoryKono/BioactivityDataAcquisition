"""Ratchet and unit coverage for AUD-002 python path extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import python_paths
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "python_paths.py"
_CORE_LOC_BEFORE = 14834


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_python_paths_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _python_surface_name(" not in core_text
    assert "INIT_PY =" not in core_text
    assert "def _python_surface_name(" in MOD.read_text(encoding="utf-8")
    assert _core._python_surface_name is python_paths._python_surface_name
    assert _core.INIT_PY == "__init__.py"
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_surface_name_exclusion_and_hubs() -> None:
    assert (
        python_paths._python_surface_name("src/bioetl/domain/ports/__init__.py")
        == "bioetl.domain.ports"
    )
    assert python_paths._is_excluded_file_structure_path(
        "docs/site/index.md",
        {"excluded_prefixes": ["docs/site"], "excluded_dir_names": []},
    )
    assert python_paths._promoted_directory_hubs(
        "src/bioetl/domain/ports", {"promoted_hubs": ["src", "src/bioetl"]}
    ) == ["src", "src/bioetl"]
    assert python_paths._supplemental_directory_hubs_for_node(
        NodeKey("script_surface", "qa"), "scripts/engineering/qa/foo.py"
    ) == ("scripts/ops",)
