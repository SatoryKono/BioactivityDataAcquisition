"""Ratchet and unit coverage for AUD-002 port surface extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import port_surfaces

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "port_surfaces.py"
_CORE_LOC_BEFORE = 14697


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_port_surfaces_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _build_port_surface_catalog(" not in core_text
    assert "PORTS_MODULE_PREFIX =" not in core_text
    assert "def _build_port_surface_catalog(" in MOD.read_text(encoding="utf-8")
    assert (
        _core._build_port_surface_catalog is port_surfaces._build_port_surface_catalog
    )
    assert port_surfaces.PORTS_MODULE_PREFIX == "bioetl.domain.ports"
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_empty_catalog_and_resolve_missing_module(tmp_path: Path) -> None:
    descriptors, surfaces, symbols = port_surfaces._build_port_surface_catalog(tmp_path)
    assert descriptors == []
    assert surfaces == {}
    assert symbols == {}
    assert port_surfaces._resolve_python_module_surface(tmp_path, "missing.mod") is None
