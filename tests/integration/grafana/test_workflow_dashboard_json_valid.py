"""Integration checks for the workflow overview dashboard JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _iter_panels(panels: list[dict[str, object]]) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for panel in panels:
        resolved.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            resolved.extend(_iter_panels(nested))
    return resolved


def test_workflow_dashboard_json_is_valid_and_uses_workflow_metrics() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-workflow-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert dashboard["uid"] == "bioetl-workflow-overview"
    expressions = "\n".join(
        target.get("expr", "")
        for panel in _iter_panels(dashboard["panels"])
        for target in panel.get("targets", [])
    )
    assert "bioetl_workflow_runs_total" in expressions
    assert "bioetl_workflow_step_events_total" in expressions
    assert "bioetl_workflow_step_duration_seconds_bucket" in expressions
