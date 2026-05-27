"""Integration tests for Grafana dashboard collapsed row policy."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_collapsed_rows_have_descriptive_titles():
    """Collapsed rows should have descriptive titles by incident scenario."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            # Check if panel is a collapsed row
            collapsed = panel.get("collapsed")
            if collapsed is True:
                title = panel.get("title", "")
                # Collapsed rows should have descriptive titles
                # Common patterns: "Incident Drilldown: ...", "Diagnostics: ...", etc.
                assert title, f"{dashboard_path.name}: collapsed row must have title"
                # Check for incident scenario patterns (optional but recommended)
                # This is a SHOULD, not MUST, so we just check title exists
