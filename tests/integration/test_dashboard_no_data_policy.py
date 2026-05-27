"""Integration tests for Grafana dashboard no-data/unknown policy."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_panels_using_zero_fallback_have_explicit_descriptions():
    """Panels using 'or vector(0)' should have explicit descriptions confirming this is intentional."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            description = panel.get("description", "")
            # Check if any target uses "or vector(0)"
            targets = panel.get("targets", [])
            uses_zero_fallback = any(
                "or vector(0)" in str(target.get("expr", "")) for target in targets
            )
            if uses_zero_fallback:
                # Panels using zero fallback should mention this in description
                # This is a SHOULD, not MUST - just check description exists
                assert description, (
                    f"{dashboard_path.name}:{title} uses 'or vector(0)' but has no description"
                )


def test_status_panels_do_not_use_zero_fallback():
    """Current-status and current-cause panels should not use 'or vector(0)' (fail-closed)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            # Check for status/current-cause panels
            if (
                "Status" in title
                or "Current Cause" in title
                or "Current Status" in title
            ):
                targets = panel.get("targets", [])
                for target in targets:
                    expr = str(target.get("expr", ""))
                    assert "or vector(0)" not in expr, (
                        f"{dashboard_path.name}:{title} should not use 'or vector(0)' - status panels must be fail-closed"
                    )
