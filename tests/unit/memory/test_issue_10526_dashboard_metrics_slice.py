"""Ratchet and unit coverage for AUD-002 dashboard metrics extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import dashboard_metrics

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "dashboard_metrics.py"
_CORE_LOC_BEFORE = 14873


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_dashboard_metrics_own_helpers_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    assert "def _extract_bioetl_metrics(" not in core_text
    assert "BIOETL_METRIC_PATTERN =" not in core_text
    assert "def _extract_bioetl_metrics(" in MOD.read_text(encoding="utf-8")
    assert _core._extract_bioetl_metrics is dashboard_metrics._extract_bioetl_metrics
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_extract_metrics_and_panel_walk(tmp_path: Path) -> None:
    text = "sum(bioetl_http_requests_total) + bioetl_queue_depth"
    metrics = dashboard_metrics._extract_bioetl_metrics(text)
    assert "bioetl_http_requests_total" in metrics
    assert "bioetl_queue_depth" in metrics
    payload = {
        "panels": [
            {
                "targets": [{"expr": "bioetl_http_requests_total"}],
                "panels": [{"targets": [{"expr": "bioetl_nested_metric"}]}],
            }
        ]
    }
    found = dashboard_metrics._dashboard_metrics_from_payload(payload)
    assert "bioetl_http_requests_total" in found
    assert "bioetl_nested_metric" in found
    probe = tmp_path / "x.py"
    probe.write_text("token-alpha", encoding="utf-8")
    assert dashboard_metrics._path_contains_any_token(probe, ["alpha"])
    assert not dashboard_metrics._path_contains_any_token(probe, ["zzz"])
