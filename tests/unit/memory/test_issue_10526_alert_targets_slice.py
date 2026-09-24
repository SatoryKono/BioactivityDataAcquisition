"""Ratchet and unit coverage for AUD-002 alert target extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import alert_targets
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "alert_targets.py"
_CORE_LOC_BEFORE = 14538


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_alert_targets_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _runtime_dimensions(" not in core_text
    assert "def _metric_dashboard_targets(" not in core_text
    assert callable(_core.build_snapshot)
    assert "def _runtime_dimensions(" in MOD.read_text(encoding="utf-8")
    assert _core._runtime_dimensions is alert_targets._runtime_dimensions
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_runtime_dimensions_and_dashboard_keys() -> None:
    dims = alert_targets._runtime_dimensions("pipeline chembl entity activity")
    assert "pipeline" in dims
    assert "entity" in dims
    keys = alert_targets._dashboard_target_keys(["bioetl-overview-v2"])
    assert keys == {NodeKey("dashboard_surface", "bioetl-overview-v2")}
    assert alert_targets._sorted_node_keys(keys)[0].name == "bioetl-overview-v2"
