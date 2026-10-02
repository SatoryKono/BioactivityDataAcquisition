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
    dashboard = load_dashboard(_CONTROL)
    compare = _panel(dashboard, 9406)
    excluded = _organize(compare)["excludeByName"]
    assert excluded["copy_mode"] is True
    assert excluded["copy_value"] is True
    assert excluded["Time"] is True
    assert _organize(compare)["renameByName"]["current_value_full"] == "Current"
    assert _organize(compare)["renameByName"]["checkpoint_value_full"] == "Checkpoint"
    for pid in (9406, 9408):
        panel = _panel(dashboard, pid)
        assert panel["fieldConfig"]["defaults"]["custom"]["inspect"] is True
        assert panel["options"]["footer"]["enablePagination"] is True


def test_identity_values_and_gaps_use_short_values_and_compact_height() -> None:
    dashboard = load_dashboard(_CONTROL)
    panel = _panel(dashboard, 9408)
    assert _organize(panel)["renameByName"]["value_full"] == "Value"
    value = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"].get("options") == "Value"
    )
    props = {p["id"]: p["value"] for p in value["properties"]}
    assert (
        props.get(
            "custom.inspect", panel["fieldConfig"]["defaults"]["custom"]["inspect"]
        )
        is True
    )
    assert panel["gridPos"]["w"] == 24
    assert panel["options"]["footer"]["enablePagination"] is True
    assert "Presence is not verification" in panel["description"]


def test_read_latency_defaults_to_p95_table_legend() -> None:
    """#10248 T4: p95 default, quantile selector, last/max legend table."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
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
    reads = _panel(dashboard, 8806)
    axis = (
        (reads.get("fieldConfig") or {})
        .get("defaults", {})
        .get("custom", {})
        .get("axisLabel")
    )
    assert "reads / $__interval" in str(axis)


def test_provider_severity_column_has_min_width_and_narrower_provider() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = _panel(dashboard, 9480)
    assert panel["options"]["cellHeight"] == "sm"
    assert panel["options"]["footer"]["enablePagination"] is True
    assert panel["fieldConfig"]["defaults"]["custom"]["minWidth"] >= 50
    names = _organize(panel)["renameByName"]
    assert names["provider"] == "Provider"
    assert names["check_result"] == "Result"
    assert names["check_performed"] == "Performed"
    assert panel["gridPos"]["y"] >= 18
    assert not _PROVIDER.exists()


def test_nav_chips_use_eight_px_gap_and_status_stats_stay_compact() -> None:
    for path in sorted(Path("grafana/dashboards").glob("*.json")):
        if path.name == "bioetl-run-explorer-v1.json":
            continue
        dashboard = load_dashboard(path)
        nav = _panel(dashboard, 1000)
        content = nav["options"]["content"]
        assert "gap:8px" in content
        assert "padding:0 2px" in content
        assert "font-size:16px" in content
        assert nav["gridPos"]["h"] == 2
    readiness = _panel(load_dashboard(_CONTROL), 9422)
    assert readiness["options"]["textMode"] == "value"
    assert readiness["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
    assert readiness["options"]["text"]["valueSize"] >= 20
