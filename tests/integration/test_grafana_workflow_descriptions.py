"""Workflow dashboard description contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    index_panels_by_base_title,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


def test_workflow_dashboard_descriptions_explain_selected_range_limits() -> None:
    runtime = load_dashboard(_require_dashboard("bioetl-runtime.json"))

    description = str(runtime.get("description", "")).lower()
    assert "selected run" in description
    assert "incident workspace" in description
    assert "pipeline flow dual layout" not in description
    assert "blockers" not in description
    assert "taxonomy" not in description

    incident = load_dashboard(_require_dashboard("bioetl-incident-v1.json"))
    panels = index_panels_by_base_title(get_dashboard_panels(incident))
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
