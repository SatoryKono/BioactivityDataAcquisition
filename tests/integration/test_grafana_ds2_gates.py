"""DS2 Wave 0 cross-cutting gates for Grafana dashboards.

Covers:
- continuous lag panels must not use state-timeline without discrete state frame
- status stats map bare numeric vocabulary (incl. 3/null)
- operator tables must not default color-background on all cells
- Trust next-step rail SSOT title remains Primary recovery
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard

pytestmark = pytest.mark.integration

_DASHBOARDS = sorted(Path("grafana/dashboards").glob("bioetl-*.json"))
_OPERATOR_UIDS = {
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
}


def _walk(panels: list[dict]) -> list[dict]:
    out: list[dict] = []
    for panel in panels or []:
        out.append(panel)
        out.extend(_walk(panel.get("panels") or []))
    return out


def _continuous_lag_expr(expr: str) -> bool:
    text = (expr or "").lower()
    return "bioetl_stage_lag_seconds" in text and "bool" not in text


def test_runtime_stage_lag_primary_panel_is_timeseries() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panels = {
        panel.get("id"): panel for panel in get_dashboard_panels(dashboard) if panel.get("id")
    }
    panel = panels.get(9105)
    assert panel is not None
    assert panel.get("type") == "timeseries", (
        "DS2-01: continuous stage lag must use timeseries, not state-timeline"
    )
    exprs = [t.get("expr", "") for t in panel.get("targets") or [] if isinstance(t, dict)]
    assert any("bioetl_stage_lag_seconds" in e for e in exprs)


def test_no_state_timeline_on_continuous_stage_lag() -> None:
    for path in _DASHBOARDS:
        dashboard = load_dashboard(path)
        if dashboard.get("uid") not in _OPERATOR_UIDS:
            continue
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "state-timeline":
                continue
            for target in panel.get("targets") or []:
                expr = str(target.get("expr") or "")
                if _continuous_lag_expr(expr):
                    raise AssertionError(
                        f"{path.name} panel id={panel.get('id')} title={panel.get('title')!r}: "
                        "state-timeline cannot host continuous bioetl_stage_lag_seconds"
                    )


def test_incident_status_maps_value_three_and_null() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    status = next(
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") == 9401 and panel.get("type") == "stat"
    )
    defaults = (status.get("fieldConfig") or {}).get("defaults") or {}
    mappings = defaults.get("mappings") or []
    flat: dict[str, str] = {}
    null_text = None
    for mapping in mappings:
        if mapping.get("type") == "value":
            for key, opt in (mapping.get("options") or {}).items():
                if isinstance(opt, dict) and "text" in opt:
                    flat[str(key)] = str(opt["text"])
        if mapping.get("type") == "special":
            options = mapping.get("options") or {}
            if options.get("match") == "null":
                result = options.get("result") or {}
                null_text = result.get("text")
    assert flat.get("0") == "OK"
    assert flat.get("1") == "WARN"
    assert flat.get("2") == "CRIT"
    assert flat.get("3") in {"UNKNOWN", "INCOMPLETE"}
    assert null_text == "UNKNOWN"


def test_incident_operator_tables_no_default_color_background() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    for panel in get_dashboard_panels(dashboard):
        if panel.get("type") != "table":
            continue
        if panel.get("id") not in {2002, 2003, 2004, 2005, 2010}:
            continue
        defaults = ((panel.get("fieldConfig") or {}).get("defaults") or {})
        custom = defaults.get("custom") or {}
        cell = custom.get("cellOptions") or {}
        assert cell.get("type") in {None, "auto"}, (
            f"Incident table id={panel.get('id')} must not default color-background; "
            f"got {cell.get('type')!r}"
        )
        overrides = (panel.get("fieldConfig") or {}).get("overrides") or []
        # Severity paint, if any, must be override-scoped.
        for override in overrides:
            props = {
                prop.get("id"): prop.get("value")
                for prop in (override.get("properties") or [])
                if isinstance(prop, dict)
            }
            cell_opt = props.get("custom.cellOptions")
            if isinstance(cell_opt, dict) and cell_opt.get("type") == "color-background":
                matcher = override.get("matcher") or {}
                assert matcher.get("id") in {"byName", "byRegexp", "byType"}


def test_trust_primary_recovery_ssot_title_and_link() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") == "Primary recovery"
    ]
    assert len(panels) == 1
    assert not any(
        panel.get("title") == "Next Action: Replay Diagnostics"
        for panel in get_dashboard_panels(dashboard)
    )
    links = (panels[0].get("options") or {}).get("dataLinks") or []
    assert links
    url = str(links[0].get("url") or "")
    assert "bioetl-control-plane-v1" in url
    assert "viewPanel=130" in url


def test_operator_status_stats_map_null_unknown() -> None:
    """First-screen Status stats on operator UIDs must map null → UNKNOWN text."""
    required = {
        "bioetl-control-plane-v1",
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-provider-health-v2",
        "bioetl-overview-v2",
    }
    for path in _DASHBOARDS:
        dashboard = load_dashboard(path)
        uid = dashboard.get("uid")
        if uid not in required:
            continue
        status_panels = [
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "Status" and panel.get("type") == "stat"
        ]
        if not status_panels:
            continue
        for panel in status_panels:
            mappings = ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                "mappings"
            ) or []
            has_null = False
            for mapping in mappings:
                if mapping.get("type") != "special":
                    continue
                options = mapping.get("options") or {}
                if options.get("match") == "null":
                    result = options.get("result") or {}
                    assert result.get("text") in {"UNKNOWN", "INCOMPLETE", "N/A"}
                    has_null = True
            assert has_null, f"{uid} Status panel missing null mapping"
