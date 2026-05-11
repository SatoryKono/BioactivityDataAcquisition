"""Integration tests for Grafana dashboard units and decimals consistency."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_event_counters_have_correct_units_decimals():
    """Event counters should have unit=short, none, or None, decimals=0 or None."""
    event_counter_keywords = {"Missing", "Failures", "Incompatibilities", "Events"}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if any(kw in title for kw in event_counter_keywords):
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                unit = defaults.get("unit")
                decimals = defaults.get("decimals")
                assert unit in ("short", "none", None), (
                    f"{dashboard_path.name}:{title} must have unit=short/none or None, got {unit!r}"
                )
                assert decimals in (0, None), (
                    f"{dashboard_path.name}:{title} must have decimals=0 or None, got {decimals}"
                )


def test_timestamp_kpi_has_datetimeasiso_unit():
    """Timestamp KPI must have unit=dateTimeAsIso."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if "Timestamp" in title:
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                unit = defaults.get("unit")
                assert unit == "dateTimeAsIso", (
                    f"{dashboard_path.name}:{title} must have unit=dateTimeAsIso, got {unit!r}"
                )


def test_fraction_panels_have_consistent_units():
    """Fraction/rate/percentage panels should use consistent units."""
    fraction_keywords = {"Rate", "Ratio", "Percentage", "Percent"}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if any(kw in title for kw in fraction_keywords):
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                unit = defaults.get("unit")
                # Allow percentunit, percent, short, time units, or None (for rate panels)
                assert unit in (
                    "percentunit",
                    "percent",
                    "percent(0)",
                    "percent(0-100)",
                    "short",
                    "s",
                    "ms",
                    "d",
                    "h",
                    None,
                ), (
                    f"{dashboard_path.name}:{title} should use percentunit, percent, short, time unit, or None, got {unit!r}"
                )
