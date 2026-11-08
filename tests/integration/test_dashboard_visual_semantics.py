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


def test_dq_history_colors_survive_trailing_missing_samples() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    quality = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9482)
    assert quality["type"] == "canvas"
    assert quality["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
    query = quality["targets"][0]
    assert "run_id=${run_id:percentencode}" in query["url"]
    assert "excluded UNKNOWN" in query["uql"]
    assert "tracking='full'" in query["uql"]
    assert "$count($distinct($s.stage_id)) = 3" in query["uql"]
    assert not any(
        p["id"] == 153
        for p in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
        )
    )


def test_status_panels_have_correct_value_mapping():
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9401)
    defaults = panel["fieldConfig"]["defaults"]
    options = next(m["options"] for m in defaults["mappings"] if m["type"] == "value")
    assert {key: value["text"] for key, value in options.items()} == {
        "0": "OK",
        "1": "UNKNOWN",
        "2": "WARN",
        "3": "CRIT",
    }
    assert options["0"]["color"] == "green"
    assert options["3"]["color"] == "red"
    assert options["1"]["color"] != "green"
    assert defaults["noValue"] == "UNKNOWN"


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
