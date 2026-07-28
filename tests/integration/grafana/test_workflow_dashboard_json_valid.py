"""Integration checks for workflow evidence after dashboard simplification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_RETIRED_WORKFLOW_DASHBOARD = Path("grafana/dashboards/bioetl-workflow-overview.json")
_RUNTIME_DASHBOARD = Path("grafana/dashboards/bioetl-runtime.json")


def _iter_panels(panels: list[object]) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        resolved.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            resolved.extend(_iter_panels(nested))
    return resolved


def test_workflow_overview_dashboard_is_retired() -> None:
    """bioetl-workflow-overview was removed in grafana simplification #6570/#6576."""
    assert not _RETIRED_WORKFLOW_DASHBOARD.exists(), (
        "bioetl-workflow-overview.json must stay retired; workflow evidence lives "
        "on bioetl-runtime (Pipeline Diagnostics) after epic #6570"
    )


def test_runtime_workflow_band_uses_workflow_metrics() -> None:
    """Merged workflow band on runtime must keep the core workflow PromQL surface."""
    dashboard = json.loads(_RUNTIME_DASHBOARD.read_text(encoding="utf-8"))

    assert dashboard["uid"] == "bioetl-runtime"
    panels = _iter_panels(list(dashboard.get("panels") or []))
    titles = {str(panel.get("title") or "") for panel in panels}
    assert "Workflow band (merged from bioetl-workflow-overview)" in titles
    assert "Failed Workflow Runs / Range" in titles
    assert "Failed Pipeline Steps / Range" in titles

    expressions = "\n".join(
        str(target.get("expr", ""))
        for panel in panels
        for target in panel.get("targets", []) or []
        if isinstance(target, dict)
    )
    assert "bioetl_workflow_runs_total" in expressions
    assert "bioetl_workflow_step_events_total" in expressions
