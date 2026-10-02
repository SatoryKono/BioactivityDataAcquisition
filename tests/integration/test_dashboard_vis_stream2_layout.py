# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportAny=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
_OVERVIEW = Path("grafana/dashboards/bioetl-overview-v2.json")
_INCIDENT = Path("grafana/dashboards/bioetl-incident-v1.json")


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
    panel = _panel(load_dashboard(_CONTROL), 9408)
    include = panel["transformations"][0]["options"]["include"]["names"]
    assert include == ["label", "priority", "present", "status", "value_full", "why"]
    assert not {"copy_mode", "copy_value", "Time"} & set(include)
    assert _organize(panel)["renameByName"]["label"] == "Parameter"
    assert panel["fieldConfig"]["defaults"]["custom"]["inspect"] is True


def test_identity_values_and_gaps_use_short_values_and_compact_height() -> None:
    """The collapsed evidence table retains full values and copy access."""
    dashboard = load_dashboard(_CONTROL)
    panel = _panel(dashboard, 9408)
    row = _panel(dashboard, 9430)
    assert row["collapsed"] is True and panel in row["panels"]
    assert panel["gridPos"]["h"] == 9
    assert _organize(panel)["renameByName"]["value_full"] == "Value"
    assert any("view=copy_values" in link["url"] for link in panel["links"])
    assert "present ? 1 : 0" in panel["targets"][0]["uql"]


def test_read_latency_defaults_to_p95_table_legend() -> None:
    """#10248 T4: p95 default, quantile selector, last/max legend table."""
    dashboard = load_dashboard(_INCIDENT)
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


def test_provider_severity_column_has_min_width_and_narrower_provider() -> None:
    """Saved provider observations replace the retired CURRENT severity matrix."""
    dashboard = load_dashboard(_OVERVIEW)
    row = _panel(dashboard, 9483)
    assert row["collapsed"] is True
    assert {9480, 9481} <= {p["id"] for p in row["panels"]}
    panel = _panel(dashboard, 9481)
    assert "provider_checks" in str(panel["targets"])
    assert "run_id=${run_id}" in str(panel["targets"])
    values = next(
        m["options"]
        for m in panel["fieldConfig"]["defaults"]["mappings"]
        if m["type"] == "value"
    )
    assert values["UNKNOWN"]["color"] == "gray"
    assert values["ERROR"]["color"] == "red"
    assert not any("bioetl_provider_current_status" in str(p) for p in row["panels"])


def test_nav_chips_use_eight_px_gap_and_status_stats_stay_compact() -> None:
    """#10257 C3: nav spacing and compact UNKNOWN on background stats."""
    for path in (
        _CONTROL,
        Path("grafana/dashboards/bioetl-overview-v2.json"),
        Path("grafana/dashboards/bioetl-dq-v2.json"),
        Path("grafana/dashboards/bioetl-incident-v1.json"),
    ):
        dashboard = load_dashboard(path)
        nav = _panel(dashboard, 1000)
        content = str((nav.get("options") or {}).get("content") or "")
        assert "gap:8px" in content
        assert "padding:0 2px" in content
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "stat":
                continue
            options = panel.get("options") or {}
            if options.get("colorMode") != "background":
                continue
            text = options.get("text") or {}
            assert options.get("textMode") in {"value", "value_and_name"}
            assert panel["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
            assert 20 <= text.get("valueSize", 0) <= 48
            assert text.get("titleSize", 0) >= 12
