# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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


DASHBOARD_DATETIME_UNIT = "time:YYYY-MM-DD HH:mm"


def _iter_field_units(panel: dict) -> list[str]:
    """Collect default and override unit strings from one panel."""
    units: list[str] = []
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    default_unit = defaults.get("unit")
    if isinstance(default_unit, str) and default_unit:
        units.append(default_unit)
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(override, dict):
            continue
        for prop in override.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "unit":
                value = prop.get("value")
                if isinstance(value, str) and value:
                    units.append(value)
    return units


def test_timestamp_kpi_uses_compact_datetime_unit():
    """Timestamp KPI must render as YYYY-MM-DD HH:mm."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if "Timestamp" in title or title == "Inspect Latest Successful Data":
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                unit = defaults.get("unit")
                assert unit == DASHBOARD_DATETIME_UNIT, (
                    f"{dashboard_path.name}:{title} must have unit="
                    f"{DASHBOARD_DATETIME_UNIT}, got {unit!r}"
                )


def test_shipped_dashboards_do_not_use_iso_datetime_unit():
    """Operator clocks must not use dateTimeAsIso (ISO-8601 with T/offset)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for unit in _iter_field_units(panel):
                assert unit != "dateTimeAsIso", (
                    f"{dashboard_path.name}:panel={panel.get('id')} "
                    f"{panel.get('title')!r} still uses dateTimeAsIso"
                )
                if unit.startswith("time:") or unit.startswith("dateTime"):
                    assert unit == DASHBOARD_DATETIME_UNIT, (
                        f"{dashboard_path.name}:panel={panel.get('id')} "
                        f"datetime unit must be {DASHBOARD_DATETIME_UNIT}, got {unit!r}"
                    )


def test_trust_evidence_observed_at_is_converted_to_time():
    """Trust first-screen ISO evidence_observed_at must become YYYY-MM-DD HH:mm."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == 9418
    )
    conversions = [
        conversion
        for transform in panel.get("transformations") or []
        if isinstance(transform, dict) and transform.get("id") == "convertFieldType"
        for conversion in (transform.get("options") or {}).get("conversions") or []
        if isinstance(conversion, dict)
    ]
    assert any(
        conversion.get("targetField") == "evidence_observed_at"
        and conversion.get("destinationType") == "time"
        for conversion in conversions
    )
    units = _iter_field_units(panel)
    assert DASHBOARD_DATETIME_UNIT in units


def test_run_explorer_completed_at_is_converted_to_time():
    """ISO completed_at strings must become time fields before unit formatting."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-run-explorer-v1.json"))
    required = {3010, 3020}
    seen: set[int] = set()
    for panel in get_dashboard_panels(dashboard):
        panel_id = panel.get("id")
        if panel_id not in required:
            continue
        seen.add(int(panel_id))
        conversions = [
            conversion
            for transform in panel.get("transformations") or []
            if isinstance(transform, dict) and transform.get("id") == "convertFieldType"
            for conversion in (transform.get("options") or {}).get("conversions") or []
            if isinstance(conversion, dict)
        ]
        assert any(
            conversion.get("targetField") == "completed_at"
            and conversion.get("destinationType") == "time"
            for conversion in conversions
        ), f"panel {panel_id} must convert completed_at to time"
    assert seen == required


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
