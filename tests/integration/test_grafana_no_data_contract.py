"""Grafana diagnostic no-data contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)
from tests.integration.grafana_contract_specs import (
    DIAGNOSTIC_NO_ZERO_FALLBACK_EXPECTATIONS,
)

pytestmark = pytest.mark.integration


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


def test_diagnostic_queries_preserve_no_data_without_zero_fallbacks() -> None:
    """Diagnostic absence must remain no-data after the #7558/#7560 closeout."""
    for (
        dashboard_name,
        panel_titles,
    ) in DIAGNOSTIC_NO_ZERO_FALLBACK_EXPECTATIONS.items():
        dashboard = load_dashboard(_require_dashboard(dashboard_name))
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"Dashboard {dashboard_name} diagnostic panel {panel_title!r} "
                "must preserve no-data instead of synthesizing a healthy zero"
            )
