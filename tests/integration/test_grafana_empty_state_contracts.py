"""Grafana empty-state rendering contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title", "expected_snippet"),
    [
        (
            "bioetl-control-plane-v1.json",
            "Track: Checkpoint Compatibility Outcomes",
            'label_replace(vector(0), "disposition", "no_events", "", "")',
        ),
    ],
)
def test_empty_state_distribution_panels_use_explicit_placeholder_series(
    dashboard_file: str, panel_title: str, expected_snippet: str
) -> None:
    """Require an explicit zero placeholder instead of an empty canvas."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any(expected_snippet in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must include "
        f"{expected_snippet!r} to avoid empty-state no-data rendering"
    )
