"""Integration tests for Grafana dashboard first-screen responsibility."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_critical_panels_on_first_screen():
    """Critical panels (status, current cause, first action) should be on first screen."""
    # Define critical panel patterns that should be on first screen
    critical_titles = {
        "System Status",
        "Runtime Status",
        "Runtime Blockers",
        "Current Status",
        "Current Cause",
        "First Action",
    }
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            # Check if this is a critical panel
            if title in critical_titles:
                grid_pos = panel.get("gridPos", {})
                y = grid_pos.get("y", 0)
                # First screen is typically y < 12 (24 rows total, 12 is half)
                # Allow some flexibility for dashboards that keep a taller shared
                # context/identity row before the answer cards.
                assert y < 18, (
                    f"{dashboard_path.name}:{title} should be on first screen (y < 18), got y={y}"
                )
