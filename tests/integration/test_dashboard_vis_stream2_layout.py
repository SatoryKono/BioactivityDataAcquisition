"""VIS-20260908 stream-2 layout contracts (#10247, #10248, #10252, #10257)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_CONTROL = Path("grafana/dashboards/bioetl-control-plane-v1.json")
_PROVIDER = Path("grafana/dashboards/bioetl-provider-health-v2.json")


def _panel(dashboard: dict, panel_id: int) -> dict:
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == panel_id
    )
    assert isinstance(panel, dict)
    return panel


def _organize(panel: dict) -> dict:
    transform = next(
        item
        for item in panel.get("transformations") or []
        if item.get("id") == "organize"
    )
    options = transform.get("options") or {}
    assert isinstance(options, dict)
    return options


def test_replay_anchor_tables_hide_internal_columns_and_rename_operator_fields() -> (
    None
):
    """#10247 T2: Parameter / Current / Result / Action, no copy_mode chrome."""
    dashboard = load_dashboard(_CONTROL)
    for panel_id in (9406, 9408, 9409):
        panel = _panel(dashboard, panel_id)
        excluded = _organize(panel).get("excludeByName") or {}
        assert excluded.get("copy_mode") is True
        assert excluded.get("copy_value") is True
        assert excluded.get("Time") is True
        assert "__name__" not in excluded
        names = {
            item.get("matcher", {}).get("options"): {
                prop.get("id"): prop.get("value")
                for prop in item.get("properties") or []
            }
            for item in panel.get("fieldConfig", {}).get("overrides") or []
        }
        assert names["copy_mode"]["custom.hidden"] is True
        assert (
            panel.get("fieldConfig", {})
            .get("defaults", {})
            .get("custom", {})
            .get("inspect")
            is True
        )


def test_identity_values_and_gaps_use_short_values_and_compact_height() -> None:
    """#10247 T3: short values with inspect, no full-hash canvas."""
    dashboard = load_dashboard(_CONTROL)
    for panel_id in (9405, 9407):
        panel = _panel(dashboard, panel_id)
        assert int((panel.get("gridPos") or {}).get("h") or 0) <= 8
        rename = _organize(panel).get("renameByName") or {}
        assert rename.get("label") == "Parameter"
        assert rename.get("value_short") == "Current"
        excluded = _organize(panel).get("excludeByName") or {}
        assert excluded.get("value_full") is True


def test_read_latency_defaults_to_p95_table_legend() -> None:
    """#10248 T4: p95 default, quantile selector, last/max legend table."""
    dashboard = load_dashboard(_CONTROL)
    panel = _panel(dashboard, 111)
    assert len(panel.get("targets") or []) == 1
    expr = str((panel.get("targets") or [{}])[0].get("expr") or "")
    assert "$read_latency_quantile" in expr
    legend = (panel.get("options") or {}).get("legend") or {}
    assert legend.get("displayMode") == "table"
    assert "lastNotNull" in (legend.get("calcs") or [])
    assert "max" in (legend.get("calcs") or [])
    quantile = next(
        item
        for item in dashboard.get("templating", {}).get("list", [])
        if item.get("name") == "read_latency_quantile"
    )
    assert quantile.get("current", {}).get("value") == "0.95"
    assert str(quantile.get("description") or "").strip()
    reads = _panel(dashboard, 6)
    axis = (
        (reads.get("fieldConfig") or {})
        .get("defaults", {})
        .get("custom", {})
        .get("axisLabel")
    )
    assert "reads / $__interval" in str(axis)


def test_provider_severity_column_has_min_width_and_narrower_provider() -> None:
    """#10252 H2: Severity readable; Provider no longer steals the row."""
    dashboard = load_dashboard(_PROVIDER)
    panel = _panel(dashboard, 9101)
    widths: dict[str, int] = {}
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        field = str((override.get("matcher") or {}).get("options") or "")
        props = {
            item.get("id"): item.get("value")
            for item in override.get("properties") or []
        }
        if "custom.width" in props:
            widths[field] = int(props["custom.width"])
        if field == "Value":
            assert props.get("custom.minWidth") == 160
            assert (props.get("custom.cellOptions") or {}).get("wrapText") is False
    assert widths.get("provider") == 130
    assert widths.get("Value") == 160
    assert "Severity" not in widths
    assert widths.get("provider", 0) + widths.get("Value", 0) <= 301
    assert int((panel.get("gridPos") or {}).get("y") or 0) < 18
    for panel_id in (9102, 9111, 9112):
        expander = _panel(dashboard, panel_id)
        assert int((expander.get("gridPos") or {}).get("y") or 0) >= 18


def test_nav_chips_use_eight_px_gap_and_status_stats_stay_compact() -> None:
    """#10257 C3: nav spacing and compact UNKNOWN on background stats."""
    for path in (
        _CONTROL,
        Path("grafana/dashboards/bioetl-overview-v2.json"),
        _PROVIDER,
        Path("grafana/dashboards/bioetl-dq-v2.json"),
        Path("grafana/dashboards/bioetl-incident-v1.json"),
        Path("grafana/dashboards/bioetl-runtime.json"),
        Path("grafana/dashboards/bioetl-run-explorer-v1.json"),
    ):
        dashboard = load_dashboard(path)
        nav = _panel(dashboard, 1000)
        content = str((nav.get("options") or {}).get("content") or "")
        assert "gap:8px" in content
        assert "padding:0 8px" in content
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "stat":
                continue
            options = panel.get("options") or {}
            if options.get("colorMode") != "background":
                continue
            text = options.get("text") or {}
            assert options.get("textMode") == "value_and_name"
            assert text.get("valueSize") == 20
            assert text.get("titleSize") == 14
