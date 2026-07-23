"""Integration tests for Grafana dashboard JSON metadata contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import get_dashboard_files, load_dashboard

pytestmark = pytest.mark.integration


def test_all_dashboards_have_bioetl_tag():
    """All shipped dashboards must have tag 'bioetl'."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        tags = dashboard.get("tags", [])
        assert isinstance(tags, list), f"{dashboard_path.name} tags must be a list"
        assert "bioetl" in tags, f"{dashboard_path.name} must have tag 'bioetl'"


def test_dashboard_time_refresh_by_level():
    """L0/L1 dashboards: 12h/30s, L2 forensic: 24h/1m."""
    expectations = {
        "bioetl-overview-v2.json": ("now-12h", "30s"),
        "bioetl-runtime.json": ("now-12h", "30s"),
        "bioetl-control-plane-v1.json": ("now-12h", "30s"),
        "bioetl-provider-health-v2.json": ("now-12h", "30s"),
        "bioetl-dq-v2.json": ("now-12h", "30s"),
        "bioetl-workflow-overview.json": ("now-12h", "30s"),
    }
    for dashboard_name, (expected_time, expected_refresh) in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        time_obj = dashboard.get("time")
        assert isinstance(time_obj, dict), f"{dashboard_name} must have time object"
        assert time_obj.get("from") == expected_time, (
            f"{dashboard_name} time.from must be {expected_time}, got {time_obj.get('from')}"
        )
        refresh_obj = dashboard.get("refresh")
        assert refresh_obj is not None, f"{dashboard_name} must have refresh setting"
        if isinstance(refresh_obj, str):
            assert refresh_obj == expected_refresh, (
                f"{dashboard_name} refresh must be {expected_refresh}, got {refresh_obj}"
            )
        elif isinstance(refresh_obj, dict):
            assert refresh_obj.get("interval") == expected_refresh, (
                f"{dashboard_name} refresh interval must be {expected_refresh}, "
                f"got {refresh_obj.get('interval')}"
            )


def test_dashboard_timezone_is_browser():
    """All dashboards must use browser timezone."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        timezone = dashboard.get("timezone")
        assert timezone == "browser", (
            f"{dashboard_path.name} timezone must be 'browser', got {timezone!r}"
        )


def test_dashboard_style_is_dark():
    """All dashboards must use dark style."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        style = dashboard.get("style")
        assert style == "dark", (
            f"{dashboard_path.name} style must be 'dark', got {style!r}"
        )


def test_dashboard_editable_is_true():
    """All shipped dashboards must be editable."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        editable = dashboard.get("editable")
        assert editable is True, (
            f"{dashboard_path.name} editable must be True, got {editable}"
        )


def test_dashboard_graphTooltip_is_1():
    """All dashboards must have graphTooltip set to 1."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        graphTooltip = dashboard.get("graphTooltip")
        assert graphTooltip in ("1", 1), (
            f"{dashboard_path.name} graphTooltip must be '1' or 1, got {graphTooltip!r}"
        )


def test_dashboard_has_uid():
    """All dashboards must define a uid."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must define a string uid"
        assert uid, f"{dashboard_path.name} uid must not be empty"


def test_dashboard_schema_version_and_iteration():
    """Dashboards should have valid schemaVersion and iteration if present."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        schema_version = dashboard.get("schemaVersion")
        iteration = dashboard.get("iteration")
        # schemaVersion may be 30 or 39 (permitted values)
        if schema_version is not None:
            assert schema_version in (30, 39), (
                f"{dashboard_path.name} schemaVersion must be 30 or 39, got {schema_version}"
            )
        # iteration if present must be positive integer
        if iteration is not None:
            assert isinstance(iteration, int), (
                f"{dashboard_path.name} iteration must be integer, got {type(iteration)}"
            )
            assert iteration > 0, (
                f"{dashboard_path.name} iteration must be positive, got {iteration}"
            )


def test_dashboard_hide_controls_if_present():
    """If hideControls is present, it must be false."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        hide_controls = dashboard.get("hideControls")
        if hide_controls is not None:
            assert hide_controls is False, (
                f"{dashboard_path.name} hideControls must be false, got {hide_controls}"
            )
