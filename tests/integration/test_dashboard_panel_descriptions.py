"""Integration tests for Grafana dashboard panel descriptions."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_panels_have_descriptions():
    """All panels should have non-empty descriptions (where applicable)."""
    # Skip navigation bus panels and other text-only panels
    skip_patterns = [
        "Navigation",
        "Scope",
        "Dashboard Navigation",
        "Known",
    ]
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            # Skip navigation/bus panels and known exception panels
            if any(skip in title for skip in skip_patterns):
                continue
            # Skip text panels (navigation bus, etc.)
            if panel.get("type") == "text":
                continue
            # Skip row panels (containers)
            if panel.get("type") == "row":
                continue
            description = panel.get("description", "")
            assert description, (
                f"{dashboard_path.name}:{title} must have non-empty description"
            )
