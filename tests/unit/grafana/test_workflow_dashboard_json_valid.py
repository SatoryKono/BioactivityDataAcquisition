"""Unit checks for the workflow overview dashboard JSON."""

from __future__ import annotations

import json
from pathlib import Path


def test_workflow_dashboard_json_is_valid_and_uses_workflow_metrics() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-workflow-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert dashboard["uid"] == "bioetl-workflow-overview"
    expressions = "\n".join(
        target.get("expr", "")
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )
    assert "bioetl_workflow_runs_total" in expressions
    assert "bioetl_workflow_step_events_total" in expressions
    assert "bioetl_workflow_step_duration_seconds_bucket" in expressions
