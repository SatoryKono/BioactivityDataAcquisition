"""Integration tests for Grafana dashboard panel title conventions."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_range_panels_include_window_in_title_or_description():
    """Range panels should mention time window concepts when using $__range."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            description = panel.get("description", "")
            # Check if panel uses $__range
            uses_range = any(
                "$__range" in str(target.get("expr", ""))
                for target in panel.get("targets", [])
            )
            if uses_range:
                combined = f"{title} {description}".lower()
                # Check for time-related concepts
                time_keywords = ["range", "window", "interval", "historical", "time"]
                assert any(kw in combined for kw in time_keywords), (
                    f"{dashboard_path.name}:{title} should mention time window concepts "
                    "in title or description when using $__range"
                )
