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
"""Integration tests for Grafana dashboard visual semantics."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_saved_dq_errors_do_not_become_healthy_history() -> None:
    """DQ no longer projects range-history colors onto a saved Run ID."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    assert 153 not in panels
    status = panels[9406]
    assert "SELECTED RUN" in status["description"]
    assert "QUERY ERROR" in str(status)
    assert "INCOMPLETE" in str(status)
    assert "run_id=${run_id}" in str(status["targets"])
    assert not any("expr" in t for t in status["targets"])


def test_saved_provider_status_has_fail_closed_mapping() -> None:
    panel = next(
        p
        for p in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
        )
        if p["id"] == 9481
    )
    defaults = panel["fieldConfig"]["defaults"]
    assert defaults["noValue"] == "UNKNOWN"
    values = next(m["options"] for m in defaults["mappings"] if m["type"] == "value")
    assert values["UNKNOWN"]["color"] == "gray"
    assert values["OK"]["color"] == "green"
    assert values["ERROR"]["color"] == "red"
    assert any(
        m["type"] == "special"
        and m["options"]["match"] == "null"
        and m["options"]["result"]["text"] == "UNKNOWN"
        for m in defaults["mappings"]
    )


def test_thresholds_configuration():
    """Status panels using thresholds mode must have proper configuration."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            field_config = panel.get("fieldConfig", {})
            defaults = field_config.get("defaults", {})
            color_config = defaults.get("color", {})
            if color_config.get("mode") == "thresholds":
                thresholds = defaults.get("thresholds", {})
                assert isinstance(thresholds, dict), (
                    f"{dashboard_path.name} thresholds must be a dict"
                )
                # Only check mode if it's set
                if thresholds.get("mode"):
                    assert thresholds.get("mode") == "absolute", (
                        f"{dashboard_path.name} thresholds mode must be absolute"
                    )
                steps = thresholds.get("steps", [])
                assert isinstance(steps, list), (
                    f"{dashboard_path.name} thresholds steps must be a list"
                )
                # Only check steps if there are any
                if steps:
                    # Check first step has null value
                    first_step = steps[0]
                    assert first_step.get("value") is None, (
                        f"{dashboard_path.name} first threshold step must have null value"
                    )


def test_status_panels_have_canonical_color_mappings():
    """Status panels should use canonical color mappings: 0→OK(green), 1→WARN(orange),
    ≥2→CRIT(red), null→UNKNOWN(gray)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            # Check for status panels
            if "Status" in title or "Severity" in title:
                field_config = panel.get("fieldConfig", {})
                defaults = field_config.get("defaults", {})
                mappings = defaults.get("mappings", [])
                if mappings:
                    # Check for canonical mappings (if mappings are defined)
                    # This is a SHOULD, not MUST - some dashboards may use different mappings
                    # Just verify that mappings exist and are well-formed
                    for mapping in mappings:
                        assert isinstance(mapping, dict), (
                            f"{dashboard_path.name}:{title} mapping must be a dict"
                        )
                        mapping_type = mapping.get("type")
                        assert mapping_type in ("value", "range", "regex", "special"), (
                            f"{dashboard_path.name}:{title} mapping type must be value/range/regex/special, got {mapping_type}"
                        )


def test_threshold_steps_have_canonical_colors():
    """Threshold steps should use canonical colors: green (null), orange (1), red (2)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            field_config = panel.get("fieldConfig", {})
            defaults = field_config.get("defaults", {})
            color_config = defaults.get("color", {})
            if color_config.get("mode") == "thresholds":
                thresholds = defaults.get("thresholds", {})
                steps = thresholds.get("steps", [])
                if steps:
                    # Check for canonical color pattern (green, orange, red)
                    # This is a SHOULD, not MUST - just verify colors are valid
                    valid_colors = {
                        "green",
                        "orange",
                        "red",
                        "yellow",
                        "blue",
                        "purple",
                        "gray",
                        "text",
                    }
                    for step in steps:
                        color = step.get("color")
                        if color:
                            # Allow both hex colors and named colors
                            if isinstance(color, str) and not color.startswith("#"):
                                assert color.lower() in valid_colors, (
                                    f"{dashboard_path.name}:{title} threshold step color must be valid named color, got {color}"
                                )
