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
    dashboard = load_dashboard(_require_dashboard("bioetl-runtime.json"))

    description = str(dashboard.get("description", "")).lower()
    assert "pipeline flow dual layout" in description
    assert "blockers + taxonomy first" in description
    assert "empty blockers are valid empty" in description
    assert "telemetry confidence" in description

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    expected_tokens = {
        "Track Failed Workflow Runs": ("selected range", "not current workflow"),
        "Track Failed Workflow Steps": ("selected range", "not stage success"),
        "Start Pipeline Triage": (
            "current verdict",
            "runtime blockers",
            "dq",
            "run explorer",
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
