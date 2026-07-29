"""Workflow dashboard description contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


def test_workflow_dashboard_descriptions_explain_selected_range_limits() -> None:
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))

    description = str(dashboard.get("description", "")).lower()
    assert "selected-range" in description
    assert "does not provide current run state" in description
    assert "run_id" in description
    assert "stage" in description

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    expected_tokens = {
        "Failed Workflow Runs / Range": ("selected time range", "0. control plane"),
        "Failed Pipeline Steps / Range": ("step_kind=pipeline", "2. runtime"),
        "Failed Transform Steps / Range": ("transform", "4. data quality"),
        "Skipped Step Events / Range": ("skipped", "selected time range"),
        "Workflow Run Outcomes / Range": (
            "valid empty",
            "no matching scope",
            "telemetry absent",
            "query/datasource failures",
            "next action",
        ),
        "Step Outcomes by Kind / Step Status / Range": (
            "step kind",
            "step status",
            "2. runtime",
        ),
        "Step Duration p95 by Kind / Step Status / Range": (
            "p95",
            "selected time range",
            "2. runtime",
        ),
        "First Action": (
            "selected-range",
            "runtime",
            "data quality",
            "run_id",
            "dependency",
            "gold-write",
        ),
    }
    for title, tokens in expected_tokens.items():
        panel = panels.get(title)
        assert panel is not None, f"Workflow dashboard missing panel {title!r}"
        panel_description = str(panel.get("description", "")).lower()
        for token in tokens:
            assert token in panel_description, (
                f"{title!r} description must mention {token!r}"
            )
