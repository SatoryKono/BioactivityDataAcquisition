"""First-screen Grafana dashboard contracts for operator triage dashboards."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def test_runtime_provider_dq_first_screens_use_canonical_current_status() -> None:
    """L2 first screens must answer current state before range evidence."""
    expectations = {
        "bioetl-runtime.json": {
            "Monitor Runtime Current Status": "bioetl_runtime_current_status",
            "Inspect Top Runtime Blockers": "bioetl_runtime_current_blocker_reason",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor GLOBAL Provider Severity Matrix": "bioetl_provider_current_status",
            "Inspect Provider Top Causes": "bioetl_provider_current_cause",
        },
        "bioetl-dq-v2.json": {
            "Monitor DQ Current Status": "bioetl_dq_current_status",
            "Inspect DQ Current Reasons": "bioetl_dq_current_reason",
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_metric in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} must expose first-screen panel {panel_title!r}"
            )
            assert panel.get("gridPos", {}).get("y", 999) <= 10, (
                f"{dashboard_name}:{panel_title} must be visible before range evidence"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(expected_metric in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must consume {expected_metric}"
            )
            assert all("$__range" not in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must not use selected range for current status"
            )


def test_provider_and_dq_range_evidence_panels_are_below_first_screen() -> None:
    provider = load_dashboard(Path("grafana/dashboards/bioetl-provider-health-v2.json"))
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    range_panels = {
        "bioetl-provider-health-v2.json": (
            provider,
            [
                "Healthy Checks",
                "Degraded Checks",
                "Provider Failure Rate",
                "Track Failure and Degraded Trend by Provider",
            ],
        ),
        "bioetl-dq-v2.json": (
            dq,
            [
                "Track Range Evidence: Bronze -> Silver -> Gold",
                "Silver Filter Rejects",
            ],
        ),
    }

    for dashboard_name, (dashboard, panel_titles) in range_panels.items():
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, f"{dashboard_name} missing {panel_title!r}"
            assert panel.get("gridPos", {}).get("y", 0) >= 18, (
                f"{dashboard_name}:{panel_title} must sit below first-screen current state"
            )
